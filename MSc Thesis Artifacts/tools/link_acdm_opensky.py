

import argparse
import csv
import hashlib
import importlib.util
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "output/acdm_primary_20261119"

OPENSKY_PREPARED = ROOT / "data/ber_history/prepared/ber_movements_opensky.csv"
OPENSKY_RAW_DIR = ROOT / "data/ber_history/opensky"
OPENSKY_EXTRA_DAYS = ["2026-11-15", "2026-11-16"]   # retrieved fresh for this study
BER_ICAO = "EDDB"

MATCH_WINDOW_MIN = 30
TIMEZONE_HYPOTHESES = [
    ("ACDM_is_UTC", timezone.utc),
    ("ACDM_is_Europe_Berlin", ZoneInfo("Europe/Berlin")),
]

STATUS_UNIQUE = "unique_callsign_time_candidate_not_identity_verification"
STATUS_REUSED = "multiple_acdm_rows_for_opensky_flight_review"


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def describe(values):
    """n, mean, median, min, max (None when empty)."""
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def normalize_callsign(callsign):
    return (callsign or "").strip().upper()


# --------------------------------------------------------------------------
# Step 1 - A-CDM departures
# --------------------------------------------------------------------------
def load_acdm(out_dir):
    """Run prepare_acdm.py and return (prepared rows, prepare module, audit)."""
    spec = importlib.util.spec_from_file_location(
        "prepare_acdm_snapshot", ROOT / "tools/prepare_acdm.py")
    prep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prep)
    prep.OUT = out_dir / "prepared"
    audit = prep.prepare()
    rows = read_csv(prep.OUT / "ber_departures_prepared.csv")
    return rows, prep, audit


# --------------------------------------------------------------------------
# Step 2 - OpenSky departures
# --------------------------------------------------------------------------
def load_opensky_departures():
    """Return {flight_key: departure} from the prepared file plus raw extra days."""
    departures = {}

    # (a) Departures already prepared from the historical OpenSky collection
    for r in read_csv(OPENSKY_PREPARED):
        if r["direction"] == "departure":
            departures[r["flight_key"]] = {
                "key": r["flight_key"],
                "callsign": r["callsign"],
                "icao24": r["icao24"],
                "epoch": float(r["boundary_epoch"]),
                "source_file": r["source_file"],
            }

    # (b) Raw API responses for the extra days, verified against their manifest
    for day in OPENSKY_EXTRA_DAYS:
        folder = OPENSKY_RAW_DIR / day
        manifest = json.loads((folder / "departure_manifest.json").read_text())
        assert manifest["status"] == "collected"
        raw = (folder / "departure.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == manifest["sha256"], f"hash mismatch {day}"

        for f in json.loads(raw):
            if (f.get("estDepartureAirport") != BER_ICAO
                    or not f.get("icao24") or f.get("firstSeen") is None):
                continue
            key = "|".join(map(str, [f["icao24"].lower(), f["firstSeen"],
                                     f["lastSeen"], "departure"]))
            departures[key] = {
                "key": key,
                "callsign": normalize_callsign(f.get("callsign")),
                "icao24": f["icao24"].lower(),
                "epoch": f["firstSeen"],
                "source_file": str((folder / "departure.json").relative_to(ROOT)),
            }

    return departures


# --------------------------------------------------------------------------
# Step 3 - Matching
# --------------------------------------------------------------------------
def empty_result(r):
    return {
        "record_key": r["record_key"],
        "source_day": r["source_day"],
        "callsign": r["callsign"],
        "acdm_atot_naive": r["atot"],
        "status": "no_eligible_actual_takeoff",
        "candidate_count": 0,
        "opensky_flight_key": "",
        "opensky_icao24": "",
        "opensky_first_seen_utc": "",
        "opensky_source_file": "",
        "timezone_hypothesis": "",
        "delta_proxy_minus_atot_min": "",
    }


def find_candidates(atot_naive, opensky_flights):
    """All (flight, hypothesis, delta_min) within the window, under both timezones."""
    atot = datetime.fromisoformat(atot_naive)
    candidates = []
    for hypothesis, zone in TIMEZONE_HYPOTHESES:
        target = atot.replace(tzinfo=zone).timestamp()
        for flight in opensky_flights:
            delta_min = (flight["epoch"] - target) / 60
            if abs(delta_min) <= MATCH_WINDOW_MIN:
                candidates.append((flight, hypothesis, delta_min))
    return candidates


def match(acdm_rows, opensky):
    by_callsign = defaultdict(list)
    for flight in opensky.values():
        if flight["callsign"]:
            by_callsign[flight["callsign"]].append(flight)

    results = []
    for r in acdm_rows:
        res = empty_result(r)
        if r["usable_actual_takeoff"] == "True":
            res["status"] = "no_correspondence_within_30min"
            cands = find_candidates(r["atot"], by_callsign[normalize_callsign(r["callsign"])])
            res["candidate_count"] = len(cands)

            if len(cands) == 1:
                flight, hypothesis, delta = cands[0]
                res.update(
                    status="unique_candidate_pending_reuse_check",
                    opensky_flight_key=flight["key"],
                    opensky_icao24=flight["icao24"],
                    opensky_first_seen_utc=datetime.fromtimestamp(
                        flight["epoch"], timezone.utc).isoformat(),
                    opensky_source_file=flight["source_file"],
                    timezone_hypothesis=hypothesis,
                    delta_proxy_minus_atot_min=round(delta, 6),
                )
            elif cands:
                res["status"] = "ambiguous_callsign_time_candidates"
        results.append(res)

    # Reuse check: one OpenSky flight may support at most one A-CDM row
    rows_per_flight = defaultdict(list)
    for res in results:
        if res["opensky_flight_key"]:
            rows_per_flight[res["opensky_flight_key"]].append(res)
    for group in rows_per_flight.values():
        for res in group:
            res["status"] = STATUS_UNIQUE if len(group) == 1 else STATUS_REUSED

    return results


# --------------------------------------------------------------------------
# Step 4 - Outputs
# --------------------------------------------------------------------------
def combine(acdm_rows, results):
    """Original A-CDM row + prefixed crosscheck_* columns."""
    by_key = {res["record_key"]: res for res in results}
    skip = {"record_key", "source_day", "callsign", "acdm_atot_naive"}
    combined = []
    for r in acdm_rows:
        row = dict(r)
        for k, v in by_key[r["record_key"]].items():
            if k not in skip:
                row["crosscheck_" + k] = v
        combined.append(row)
    return combined


def daily_summary(audit, acdm_rows, matched):
    daily = []
    for source in audit["sources"]:
        day = source["date"]
        rows_day = [r for r in acdm_rows if r["source_day"] == day]
        matched_day = [r for r in matched if r["source_day"] == day]
        daily.append({
            "date": day,
            "records": len(rows_day),
            "eligible_atot": sum(r["usable_actual_takeoff"] == "True" for r in rows_day),
            "complete_target_triples": sum(r["usable_target_takeoff_pairs"] == "True" for r in rows_day),
            "unique_opensky_candidates": len(matched_day),
            "median_signed_proxy_delta_min": statistics.median(
                float(r["delta_proxy_minus_atot_min"]) for r in matched_day) if matched_day else None,
        })
    return daily


def build_summary(audit, prep, acdm_rows, results, matched, daily):
    deltas = [float(r["delta_proxy_minus_atot_min"]) for r in matched]
    metrics = {}
    for k in prep.METRICS:
        values = [float(r[k]) for r in acdm_rows
                  if r["usable_target_takeoff_pairs"] == "True" and r[k] != ""]
        metrics[k] = describe(values)

    return {
        "as_of": "2026-11-19",
        "primary_source": "BER A-CDM application finalized daily snapshots",
        "primary_unit": "one BER departure record, not an arrival-departure turnaround pair",
        "primary_records": len(acdm_rows),
        "primary_cohorts": audit["cohorts"],
        "status_counts": audit["status_counts"],
        "days": daily,
        "crosscheck_status": dict(Counter(r["status"] for r in results)),
        "timezone_hypotheses": dict(Counter(r["timezone_hypothesis"] for r in matched)),
        "unique_candidate_delta_min": describe(deltas),
        "unique_candidate_absolute_delta_min": describe([abs(x) for x in deltas]),
        "unique_matches_within_minutes": {str(t): sum(abs(x) <= t for x in deltas)
                                          for t in [1, 5, 15, 30]},
        "target_metrics_complete_triples": metrics,
        "missing": audit["missing"],
        "auxiliary_opensky_core_pairs": 10940,
        "auxiliary_pairs_with_acdm_candidate": 826,
        "acdm_measured_full_turnaround_pairs": 0,
        "cautions": [
            "Unique callsign/time correspondence does not independently verify aircraft identity.",
            "OpenSky firstSeen is an observation proxy, not independently measured exact ATOT.",
            "Delta statistics are conditional on matches within30 minutes.",
            "Timezone hypothesis is empirical correspondence, not provider documentation.",
            "No source AIBT/AOBT or service start/end timestamps are available.",
            "No claim of continuous full-day coverage or improved predictive accuracy.",
        ],
    }


README_TEXT = '''# A-CDM primary study update, 19 November 2026

Every row of ACDM_Berlin_Primary_With_OpenSky_Check.csv originates in a finalized BER A-CDM snapshot. OpenSky supplies only prefixed departure cross-check columns in this table. Missing/ambiguous matches remain explicit and never create A-CDM records. Summary counts and matching limitations are in summary.json.

The primary unit is a departure record. These observations cannot be represented as complete landing-to-next-takeoff or AIBT–AOBT pairs because the source lacks arrival/block milestones. TOBT/TSAT are target values and their differences from ATOT are not measured queue or service durations. Raw timestamps retain their unverified naive timezone.

The previous10,940 aircraft-pair dataset originates in OpenSky. Only826 core pairs have candidate A-CDM reference links. It is a separate auxiliary reconstruction and cannot become A-CDM data by renaming columns. Previous OCPN/Promenade outputs and60 replications are an exploratory pilot using that reconstruction. They are not new A-CDM-only calibrated results.

This version does not overwrite earlier source/prepared files or experimental outputs. Technical checks verify source JSON/CSV consistency, manifest counts and raw hashes. OpenSky cross-check tests UTC/Berlin hypotheses within30minutes, retains ambiguity, prohibits reused unique matches and reports agreement conditional on the retained candidates.
'''


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output folder")
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=True)

    acdm_rows, prep, audit = load_acdm(out)          # Step 1
    opensky = load_opensky_departures()               # Step 2
    results = match(acdm_rows, opensky)               # Step 3
    matched = [r for r in results if r["status"] == STATUS_UNIQUE]

    daily = daily_summary(audit, acdm_rows, matched)  # Step 4
    summary = build_summary(audit, prep, acdm_rows, results, matched, daily)

    write_csv(out / "opensky_departure_crosscheck.csv", results)
    write_csv(out / "ACDM_Berlin_Primary_With_OpenSky_Check.csv", combine(acdm_rows, results))
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(out / "daily_summary.csv", daily)
    (out / "README.md").write_text(README_TEXT, encoding="utf-8")

    keys = ["primary_records", "primary_cohorts", "status_counts", "days", "crosscheck_status",
            "unique_candidate_delta_min", "unique_candidate_absolute_delta_min",
            "unique_matches_within_minutes"]
    print(json.dumps({k: summary[k] for k in keys}, indent=2))


if __name__ == "__main__":
    main()
