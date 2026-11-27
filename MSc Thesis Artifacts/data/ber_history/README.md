# BER historical flight dataset: October 1–November 13, 2026

## What this dataset represents

Authenticated OpenSky airport flight lists for EDDB, paired by aircraft ICAO24 and cross-checked against the saved BER A-CDM departures. The requested period uses **Europe/Berlin calendar dates**, with explicit timezone offsets in exported timestamps. September 29–30 are fetched only as support for aircraft already at BER before October 1.

OpenSky firstSeen/lastSeen are inferred flight boundaries from surveillance observations. Their difference across two legs is a **ground-interval proxy**, not independently measured exact landing-to-takeoff time and not AIBT-to-AOBT stand turnaround. The exact actual-event columns remain empty. No schedules, passenger counts, service durations, registration values or missing days are invented.

OpenSky builds historical flight lists after a UTC day finishes. November 13 is marked `awaiting_nightly_processing` rather than represented as a complete observed day. November 10–12 have absent or unusually sparse returns, even after one refresh. Check `prepared/daily_coverage.csv` and `prepared/audit.json` for actual availability. Successful query coverage does not establish complete surveillance of all airport traffic. A return below 100 movements per direction is a transparent review flag, not a statistically validated completeness threshold.

## Files

| File under `prepared/` | Meaning |
|---|---|
| `ber_ground_intervals_proxy.csv` | All candidate arrival/next-departure pairs with review flags |
| `ber_ground_intervals_core_proxy.csv` | Pairing-screened subset; not verified ground-truth timing |
| `ber_movements_opensky.csv` | Unique arrival/departure observations whose relevant boundary falls in the requested period |
| `unpaired_departures.csv` | Observed departures without an adjacent observed BER arrival for the same ICAO24 |
| `acdm_crosscheck_candidates.csv` | All 810 finalized A-CDM references plus supplemental observed takeoffs, labeled separately |
| `ber_acdm_observed_takeoffs.csv` | Unique observed A-CDM takeoffs found in saved raw responses and preserved manual snapshots; partial daily coverage |
| `daily_coverage.csv` | Arrival/departure query status for every requested local calendar date |
| `movement_records_for_review.csv` | Raw records lacking a usable aircraft identity or relevant time boundary, if any |
| `audit.json` | Counts, review flags, reference correspondence and build-script hash |

`opensky/YYYY-MM-DD/` holds raw responses and manifests with query windows, retrieval times and SHA-256 hashes. The requested UTC interval is 25 hours for the October 25 daylight-saving transition. `access_checks/` records initial access probes; these are not counted as independent flight observations. Credentials are excluded from this data directory and from reports. Windows-encrypted credentials are read locally; OAuth tokens are kept in memory only.

## Pairing method

1. Retain unique source flight records per direction; preserve inferred airport, distance and alternative-airport candidate metadata.
2. Order relevant arrival `lastSeen` and departure `firstSeen` boundaries for each ICAO24.
3. Create a candidate only when an arrival is immediately followed by a departure in that observed BER sequence. Both records must therefore share the aircraft identifier. This supports candidate physical-aircraft linkage, subject to surveillance gaps or erroneous identifiers; it is not a complete network-wide rotation audit.
4. Flag nonpositive intervals, source inconsistencies, consecutive arrivals, intervals under 15 minutes, intervals over 24 hours, or missing daily query coverage. These remain in the full candidate table but are excluded from the core subset. Thresholds are transparent review rules, not universal turnaround-duration laws.
5. Preserve intervals of 6–24 hours and label descriptive duration bands. Do not treat overnight parking as a short service turnaround simply because the pair is structurally plausible. A two-day boundary buffer cannot resolve every long stay before October 1.

`inbound_last_seen_utc` and `outbound_first_seen_utc` identify the two observed boundaries. `ground_interval_proxy_min` is their difference in minutes. Corresponding Berlin timestamps include UTC offsets. `inbound_callsign`/`outbound_callsign`, route airports, aircraft ICAO24 and source file paths preserve each pair's traceability. Callsigns are ATC identifiers, not necessarily commercial flight numbers. `eligible_core_proxy_cohort` means no implemented pairing-review flags; airport-distance/candidate metadata still need consideration for stricter timing-quality analyses.

## A-CDM reference method

The three finalized snapshots contribute 810 reference departures, with ATOT available for 784. Supplemental actual takeoffs are recovered from previously saved raw pages and manual current-board snapshots, including observations from dates not represented by finalized daily files. They are explicitly labeled partial-day observations and never treated as additional complete days. Per API record ID, the latest source update is selected; differing observed ATOT values are flagged in the observation table and such supplemental records are not used for matching. The reference data are not used to fabricate October flights or targets. For each reference with ATOT, compare the normalized ATC callsign to OpenSky departures under both possible timestamp interpretations: naive A-CDM values treated as UTC, and treated as Europe/Berlin. Retain candidates within an explicitly chosen 30-minute tolerance.

Only a unique callsign/time candidate, with no reuse by another A-CDM reference, supplies reference attributes to a paired interval. This is a correspondence candidate, not an independently verified registration-to-ICAO24 mapping. Wider tolerances can increase false positives; time proximity is not a substitute for independent identity confirmation.

Source A-CDM registration, aircraft type, airline, stand, runway, TOBT, TSAT and ATOT are attached only to the corresponding candidate flight. They are not extrapolated to other dates or aircraft. The field `opensky_departure_minus_acdm_min` reports the OpenSky proxy minus ATOT under the recorded timezone hypothesis. The original naive ATOT is preserved separately. Empirical agreement supports a timezone interpretation but does not independently document the API's timezone contract. No timezone is silently assigned to the original A-CDM file.

Missing A-CDM correspondence can mean absent OpenSky coverage, missing callsign, time discrepancy, cancellation or ambiguity. Missingness must not automatically be counted as an airport operational failure. A strong departure cross-check does not validate inferred arrival times or internal handling durations.

## Reproduction

Use the bundled Python runtime, which supplies timezone data:

```powershell
& 'C:\Users\amira\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools/collect_ber_opensky.py --start 2026-10-01 --end 2026-11-13
& 'C:\Users\amira\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools/build_ber_history.py
```

The collector skips hash-verified successful files, respects saved rate-limit backoff and stops on access denial. A 404/error is recorded as unavailable, not silently converted into a zero-flight day. `--refresh` preserves older successful responses before updating selected dates. Re-running after nightly publication can add current-day records. No recurring automation or A-CDM collection schedule was changed. Run `tools/verify_ber_history.py` after building for independent exported-data checks.

## Source documentation and external check

- [OpenSky REST API](https://openskynetwork.github.io/opensky-api/rest.html): endpoint parameters and OAuth authentication.
- [OpenSky FlightData fields](https://openskynetwork.github.io/opensky-api/python.html): inferred flight boundary and airport fields.
- [OpenSky FAQ](https://opensky-network.org/about/faq): nightly flight inference and lack of schedules/cancellation data.
- [BER October traffic report](https://corporate.berlin-airport.de/en/company-media/media-portal/pressemitteilungen/2026-11-06-verkehrsbericht-oktober.html): airport reports 18,282 October movements. Compare totals as a coverage plausibility check; matching aggregate counts cannot establish flight-level completeness, and classifications/boundary semantics may differ.
- [BER TraVis](https://travisber.topsonic.aero/travis.php?lang=en): alternative two-month replay found during research. Its displayed terms restrict copying/reuse without permission. No TraVis data were bulk extracted or included.

Do not describe this as an official complete BER operational event log, true block-time dataset or measured ground-service log. It is a reproducible surveillance-based reconstruction with a limited independent A-CDM departure reference.
