# Combined Berlin dataset — packaged 19 November 2026

## Open this file first

`BER_Combined_Turnaround_Pairs.csv`: **10,940 rows and 41 columns**. This is an unchanged copy of the pairing-screened core table used for the thesis. Each row is a candidate interval between an inbound and following outbound observation of the same aircraft ICAO24 identifier at BER (EDDB). It joins two flight legs; it is not one flight leg or a certified ground-truth rotation.

**826 rows have a candidate A-CDM reference match.** The other rows retain their OpenSky pairing, with missing A-CDM fields left empty. A-CDM matches are based on unique callsign/time correspondence, not independent registration-to-ICAO24 verification.

## Timestamp meanings

- `inbound_last_seen_utc` / `inbound_last_seen_berlin`: last observed inbound flight boundary.
- `outbound_first_seen_utc` / `outbound_first_seen_berlin`: first observed outbound flight boundary.
- `ground_interval_proxy_min`: outbound first-seen minus inbound last-seen, in minutes.
- `actual_landing_time`, `actual_inblock_time`, `actual_offblock_time`, `actual_takeoff_time`: empty; these exact operational events were not independently observed for the paired rows.
- `acdm_actual_takeoff_naive`: an actual-takeoff field from the matched A-CDM record where available; preserved in its source timezone form. `acdm_timezone_hypothesis` records the reconciliation hypothesis separately.

Therefore, this table approximates the aircraft's arrival-to-next-departure interval. **It is not exact measured landing-to-takeoff or stand turnaround (AIBT–AOBT).** TOBT and TSAT are targets, not executed service events. Cleaning, fueling, boarding and passenger counts are not measured in this dataset. No simulated service times have been inserted.

## Coverage and other files

The core arrivals range from 2026-09-30T13:22:17+02:00 to 2026-11-09T21:38:43+01:00. There are 54 supporting September 30 arrivals paired to departures entering the October period. The core table does not provide complete coverage through November 19.

`BER_All_Candidate_Pairs_With_Review_Flags.csv` contains **11,203 candidates**, including the 263 omitted from the screened table. It has 858 candidate A-CDM links. Some observations reach November 12, but sparse/missing coverage and other flags make these rows unsuitable for automatic inclusion. This table and the core table overlap; do not concatenate them.

`supporting_prepared_data/` contains the original movements, unmatched departures, daily coverage, reference cross-checks and preparation audit. The 1,204 observed A-CDM takeoff records and 1,230 cross-check reference records are earlier historical-build views with supplemental partial-day observations. They overlap other A-CDM views; their counts must not be added together as distinct flights.

`ACDM_daily_snapshots/` contains all five finalized snapshots currently saved: 2026-11-01 (289 rows), 2026-11-05 (257 rows), 2026-11-08 (264 rows), 2026-11-15 (254 rows), 2026-11-16 (258 rows). Their total is 1,322 departure records across five separated snapshots, not a continuously observed period or a set of fully completed turnarounds. These source records can include unfinished/canceled departures. The November 15/16 snapshots were collected after the combined table was built. They are included separately and are **not silently appended as paired turnarounds**, because corresponding OpenSky arrivals are unavailable in this build.

`ACDM_supplemental_reference/` preserves the existing supplemental reference response pages and manifest used in the earlier build. It is not an additional complete day.

## Main column groups

| Columns | Meaning |
|---|---|
| `interval_id` | Unique candidate interval key |
| `aircraft_icao24` | Physical-aircraft identifier used for pairing, subject to surveillance/identity limitations |
| `inbound_callsign`, `outbound_callsign` | ATC identifiers for the two legs; not necessarily commercial flight numbers |
| `inbound_origin`, `outbound_destination` | Source airport context |
| UTC and Berlin boundary columns | Offset-aware observation-boundary timestamps |
| `ground_interval_proxy_min`, `descriptive_duration_band` | Arithmetic interval and descriptive stay band |
| `timing_basis`, `pairing_basis`, `review_flags`, `eligible_core_proxy_cohort` | Definitions and screening status; core does not mean verified timing |
| Distance/alternative-airport columns | Airport-estimation quality context |
| Source-file and outbound-flight keys | Provenance links to archived source records |
| `acdm_reference_key`, candidate reference fields | Matched A-CDM registration, type, airline, stand, runway and targets where available |
| `acdm_actual_takeoff_naive`, `acdm_timezone_hypothesis`, `opensky_departure_minus_acdm_min`, `acdm_match_basis` | Departure cross-check, original timestamp and explicitly recorded matching assumptions |

## Checks

The packaging script checks unique core IDs, positive interval ordering, minute arithmetic and absence of fabricated exact-event timestamps. Exported CSVs are byte-identical copies; preparation screening is not rerun or changed. The original verification report documents source aircraft/airport/time linkage checks. `dataset_manifest.json` records file hashes and counts. No API credentials, authentication responses or simulated service logs are included.
