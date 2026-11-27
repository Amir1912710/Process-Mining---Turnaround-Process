"""Exploratory empirical analyses proposed for the MSc thesis (2026-11-20).

Uses only existing prepared data (no new collection):
  - A-CDM primary table (1,322 BER departures, 5 snapshot dates)
  - OpenSky-derived aircraft pairs (10,940; 826 candidate A-CDM links)

Analyses
  A1  Inbound buffer -> TOBT lateness (reactionary delay through the turnaround)
  A2  Landing-to-TOBT floors by airline segment (empirical calibration target)
  A3  Departure-bank load -> ATOT-TSAT (shared runway/start-up contention)
  A4  Same-aircraft rotation delay carry-over (delay propagation between flights)
  A5  Stand area descriptives (terminal vs remote, layout mapping to be confirmed)

Assumptions, stated explicitly:
  * Naive A-CDM timestamps are interpreted as UTC (the hypothesis supported by the
    OpenSky departure cross-check; not a provider-confirmed contract).
  * OpenSky inbound lastSeen is a landing PROXY, not AIBT/ALDT.
  * The LCC list below is a working classification and must be cited/justified.
"""
import numpy as np
import pandas as pd

ROOT = r"C:/Users/amira/Documents/ChatGPT/Thesis Project/output"
ACDM = ROOT + "/acdm_primary_20261119/ACDM_Berlin_Primary_With_OpenSky_Check.csv"
PAIRS = ROOT + "/BER_Combined_Dataset/BER_Combined_Turnaround_Pairs.csv"
LCC = {"EJU", "EZY", "EWG", "RYR", "WZZ", "VLG", "PGT", "NOZ", "NSZ", "SXS",
       "TRA", "TVF", "EXS", "LDM", "BTI"}
RNG = np.random.default_rng(20261120)


def boot_spearman(x, y, n=5000):
    x, y = np.asarray(x), np.asarray(y)
    stat = pd.Series(x).corr(pd.Series(y), method="spearman")
    idx = RNG.integers(0, len(x), (n, len(x)))
    bs = [pd.Series(x[i]).corr(pd.Series(y[i]), method="spearman") for i in idx]
    return stat, np.percentile(bs, [2.5, 97.5])


def load():
    d = pd.read_csv(ACDM, low_memory=False)
    for c in ["std_parsed", "tobt_parsed", "tsat_parsed", "atot_parsed"]:
        d[c] = pd.to_datetime(d[c], errors="coerce")
    d = d[d.usable_target_takeoff_pairs == True].copy()  # 1,283 complete triples
    d["area"] = d.parking_pos.astype(str).str.extract(r"^([A-Za-z]+)")[0]
    d["dep_delay"] = (d.atot_parsed - d.std_parsed).dt.total_seconds() / 60
    d["seg"] = np.where(d.airline_icao.isin(LCC), "LCC", "FSC/other")
    return d


def a1_a2(d):
    p = pd.read_csv(PAIRS, low_memory=False)
    m = p.dropna(subset=["acdm_reference_key"]).merge(
        d, left_on="acdm_reference_key", right_on="record_key", how="inner")
    m = m[m.ground_interval_proxy_min < 360].copy()  # exclude long stays
    inb = pd.to_datetime(m.inbound_last_seen_utc).dt.tz_localize(None)
    m["buffer"] = (m.std_parsed - inb).dt.total_seconds() / 60
    m["land_to_tobt"] = (m.tobt_parsed - inb).dt.total_seconds() / 60
    print(f"\nA1 linked turnarounds: n={len(m)}")
    m["bin"] = pd.cut(m.buffer, [-300, 30, 45, 60, 90, 360])
    print(m.groupby("bin", observed=True).agg(
        n=("tobt_minus_std_min", "size"),
        share_tobt_late_gt5=("tobt_minus_std_min", lambda x: (x > 5).mean()),
        median_tobt_shift=("tobt_minus_std_min", "median")).round(2))
    r, ci = boot_spearman(m.buffer, m.tobt_minus_std_min)
    print(f"Spearman(buffer, TOBT-STD) = {r:.2f}  95% bootstrap CI [{ci[0]:.2f}, {ci[1]:.2f}]")

    m["tight"] = np.where(m.buffer < 45, "buffer<45", "buffer>=45")
    print("\nA2 landing-proxy -> TOBT (minutes)")
    print(m.groupby(["seg", "tight"]).land_to_tobt.describe(
        percentiles=[.05, .25, .5])[["count", "5%", "25%", "50%"]].round(1))


def a3(d):
    t = d.tsat_parsed.values.astype("datetime64[s]").astype(np.int64)
    d["load30"] = [int((np.abs(t - x) <= 900).sum() - 1) for x in t]
    print("\nA3 departures with TSAT within +-15 min vs ATOT-TSAT")
    d["lb"] = pd.cut(d.load30, [-1, 2, 4, 6, 8, 40])
    print(d.groupby("lb", observed=True).atot_minus_tsat_min.agg(
        ["count", "median", "mean"]).round(2))
    r, ci = boot_spearman(d.load30, d.atot_minus_tsat_min, 2000)
    print(f"Spearman = {r:.2f}  95% CI [{ci[0]:.2f}, {ci[1]:.2f}]")


def a4(d):
    r = d.dropna(subset=["aircraft_reg"]).sort_values(
        ["source_day", "aircraft_reg", "std_parsed"])
    g = r.groupby(["source_day", "aircraft_reg"])
    r["prev_delay"] = g.dep_delay.shift()
    p = r.dropna(subset=["prev_delay"])
    s, ci = boot_spearman(p.prev_delay, p.dep_delay)
    print(f"\nA4 same-aircraft consecutive BER departures: n={len(p)}")
    print(f"Spearman(prev departure delay, next departure delay) = {s:.2f} "
          f"95% CI [{ci[0]:.2f}, {ci[1]:.2f}]")


def a5(d):
    print("\nA5 stand area (letter prefix of parking_pos)")
    print(d.groupby("area")[["tobt_minus_std_min", "atot_minus_tsat_min",
                             "dep_delay"]].median().round(1)
          .join(d.area.value_counts().rename("n")))


if __name__ == "__main__":
    data = load()
    a1_a2(data)
    a3(data)
    a4(data)
    a5(data)
