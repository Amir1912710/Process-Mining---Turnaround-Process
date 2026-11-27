# BER data preparation — first MSc milestone

This dataset is Amir Abdelsayed's empirical preparation layer for the MSc study. The Airport Ground Handling (Extended) simulator is the professor's existing baseline; no authorship of that model is claimed. No model changes or empirical calibration have been performed in this milestone.

## Scope and provenance

Only finalized `data/acdm/days/YYYY-MM-DD/flights.csv` snapshots are read. Raw pages, previews, unsuccessful requests and superseded versions are excluded. The script checks source CSV against its corresponding JSON, manifest row counts and recorded raw-response hashes. It never accesses credentials or the network and does not modify source files.

Run `python tools/prepare_acdm.py` from the project, or invoke that script by its absolute path. Outputs are regenerated in this directory. `audit.json` records source hashes, script hash, source coverage, missingness, flags and descriptive interval statistics. Future finalized daily snapshots are included automatically when the script is rerun; files in this folder are derived outputs.

## Current coverage

| Source STD date | Records |
|---|---:|
| 2026-11-01 | 289 |
| 2026-11-05 | 257 |
| 2026-11-08 | 264 |
| Total | 810 |

These are three separated daily snapshots, not eleven continuously observed days. Full-day coverage remains unverified. The `verified=True` source field is an API attribute, not independent verification of completeness, timestamp semantics or research suitability.

## Outputs and inclusion rules

| File | Rows now | Use |
|---|---:|---|
| `ber_departures_prepared.csv` | 810 | Master table, including canceled, incomplete and flagged records |
| `actual_takeoffs.csv` | 784 | Valid source identity/date/airport and parsable ATOT, excluding canceled flights |
| `target_takeoff_pairs.csv` | 782 | Actual takeoff cohort with parsable TOBT and TSAT; negative intervals retained |
| `nonnegative_target_sequence.csv` | 774 | Sensitivity cohort requiring TSAT−TOBT, ATOT−TSAT and ATOT−TOBT all nonnegative |
| `quality_flags.csv` | One row per flag | Review ledger; a flight may have several flags |
| `audit.json` | — | Reproducibility and quality summary |

The last cohort is a conservative sensitivity subset, not a declaration that every negative interval is erroneous. Eight distinct flights are omitted from it; overlapping interval flags must not be summed as distinct flights. No generic outlier clipping or maximum-delay threshold is applied. Long delays are retained. Missing aircraft registration, stand or runway affects analyses requiring those fields but does not invalidate every departure analysis.

Source statuses are 784 OFF, 13 SKD, 11 XLD and 2 COM. Fifteen non-canceled rows lack ATOT. Canceled and unfinished flights remain available for coverage/missingness analysis and must not be silently described as completed flights.

## Dictionary and timestamp rules

All original CSV columns are retained with their original values. Added columns follow these rules:

| Added field | Definition |
|---|---|
| `source_day`, `source_file`, `source_row` | Provenance; row numbers include the CSV header |
| `record_key` | Source date plus API record ID; duplicates are flagged rather than silently selected |
| `<timestamp>_parsed` | ISO-formatted parsable source timestamp; empty for missing/invalid values |
| `timestamp_timezone` | `unverified_naive`; no UTC/local conversion is performed |
| `time_of_day_std_hour` | Raw STD wall-clock hour, not a verified local operational hour |
| `usable_actual_takeoff` | Inclusion flag for actual takeoff cohort |
| `usable_target_takeoff_pairs` | Inclusion flag for complete target/takeoff triples |
| `usable_nonnegative_target_sequence` | Inclusion flag for the sensitivity subset |
| `quality_flags` | Semicolon-separated review/missingness flags |
| `suggested_pilot_partition` | Latest available source date held out; earlier dates for calibration |

The partition is a proposal, currently November 1/5 for calibration and November 8 for evaluation. It has not been used to fit anything. A future rerun with new dates recomputes this suggestion; freeze an explicit experiment split before fitting models. Do not tune decisions on held-out performance. Descriptive inspection of a candidate test day is disclosed by this audit; it is not an untouched prospective test set.

Timestamp meanings:

- `std`: source scheduled departure field; precise off-block versus take-off definition remains to be confirmed.
- `eobt`: estimated off-block timestamp by conventional A-CDM naming; raw API mapping still needs confirmation.
- `tobt`: target off-block timestamp, not observed off-block and not the time its update was issued.
- `tsat`: target start-up approval timestamp, not actual approval or the time TSAT was issued.
- `ctot`: calculated take-off timestamp when present; absence is not automatically a data defect or zero delay.
- `atot`: source actual take-off timestamp; retained as the observed departure endpoint.
- `updated_at`: source record update timestamp; not an individual target revision history.
- `taxitime`: reported source value; no claim that it is actual measured taxi duration.

Derived minutes are computed directly without imputing values:

| Field | Arithmetic | Valid interpretation |
|---|---|---|
| `tsat_minus_tobt_min` | TSAT − TOBT | Difference between target values; not actual queue waiting |
| `atot_minus_tsat_min` | ATOT − TSAT | Actual takeoff relative to target start-up; not measured taxi time |
| `atot_minus_tobt_min` | ATOT − TOBT | Composite target-to-takeoff interval |
| `tobt_minus_std_min` | TOBT − STD | Target/schedule difference with STD semantics unresolved |
| `atot_minus_ctot_min` | ATOT − CTOT | Difference from calculated takeoff time for CTOT-bearing flights |

Across-midnight differences use the complete recorded dates. The pipeline does not shift timestamps by a day just to force positive durations. Missing AIBT/AOBT or service timestamps are not invented. Original dates and naive timezones are preserved. Do not label target fields as executed process events in a Promenade log; issue/update events require observation/issue timestamps.

## Remaining data-readiness gates

1. Confirm raw API timestamp timezone, STD definition and `taxitime` meaning from reliable source documentation or the provider.
2. Review the eight flights with negative target-sequence differences. Decide on metric-specific inclusion with both unfiltered and sensitivity results documented.
3. Select an explicit forecast/retrospective experiment definition. Final end-of-day targets cannot automatically be used as early prediction inputs.
4. Freeze the source dates, split and inclusion criteria for calibration/evaluation. More observed days are needed for stronger validation.

The preparation milestone has produced an auditable analysis table. It has not established full model-ready ground-truth turnaround data. The next independent work is the semantic/flag review, followed by descriptive analysis; empirical simulator calibration comes afterward.
