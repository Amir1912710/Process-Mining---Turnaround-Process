# Berlin historical dataset — collection and preparation results

Requested period: **October 1–November 13, 2026**, using Berlin calendar dates. Source observations were obtained through the user's authenticated OpenSky API client. All raw API responses and query manifests are retained locally. The original A-CDM source files were not changed.

## Deliverables

| Dataset | Rows | Meaning |
|---|---:|---|
| `data/ber_history/prepared/ber_movements_opensky.csv` | 22,635 | 11,316 arrivals and 11,319 departures within the requested period |
| `data/ber_history/prepared/ber_ground_intervals_proxy.csv` | 11,203 | Candidate consecutive observed BER arrival/departure pairs of the same ICAO24 |
| `data/ber_history/prepared/ber_ground_intervals_core_proxy.csv` | 10,940 | Subset with no implemented pairing-review flags |
| `data/ber_history/prepared/unpaired_departures.csv` | 116 | Departures for which no candidate interval was created |
| `data/ber_history/prepared/ber_acdm_observed_takeoffs.csv` | 1,204 | Unique actual takeoff observations recovered from saved A-CDM pages and preserved manual snapshots |
| `data/ber_history/prepared/acdm_crosscheck_candidates.csv` | 1,230 | 810 finalized daily reference records, including unfinished/canceled flights, plus 420 supplemental actual-takeoff observations |

The core intervals include 8,951 intervals of 15 minutes–6 hours and 1,989 of 6–24 hours. These are descriptive bins, not independently established service-turnaround classifications. Overnight/extended ground stays must be considered separately when calibrating a short-turnaround model.

## Coverage limitations

Forty dates, October 1–November 9, have successful arrival/departure queries without the low-count flag. This does not prove complete surveillance coverage. Two preceding dates, September 29–30, provide 1,104 supporting movement records to improve left-boundary pairing; they are not included as in-period movements.

| Date | Arrivals returned | Departures returned | Treatment |
|---|---:|---:|---|
| November 10 | No arrival result (HTTP 404) | 22 | Missing/sparse source coverage |
| November 11 | 3 | 24 | Sparse source coverage |
| November 12 | 16 | 32 | Sparse source coverage |
| November 13 | Not published in historical endpoint | Not published in historical endpoint | Awaiting nightly processing |

One refresh of November 10–12 returned the same sparse counts. Do not claim a complete October 1–November 13 dataset. The latest November 13 A-CDM board snapshot had zero actual takeoffs at retrieval; the earlier snapshot with 247 actual takeoffs was preserved and remains included in the reference observations.

## Reference cross-check

Of the original 784 finalized A-CDM records with ATOT, 767 (97.8%) have a unique callsign/time correspondence candidate. Across finalized and supplemental references, 897 unique candidates were found. All select the hypothesis that the naive A-CDM timestamps are UTC rather than Berlin local time. This is strong empirical support, not independent provider documentation of the API timezone contract.

For the 897 selected candidates, OpenSky departure boundary minus A-CDM ATOT has median **−9 seconds**. Of those candidates, 882 are within one minute and 896 within five minutes. The search already restricted candidates to 30 minutes, so these statistics describe matched cases and do not establish accuracy over all traffic. Registration/aircraft-type/stand/runway/target values are attached only to corresponding candidate flights, without extrapolating them to other dates.

## What one interval row means

One row links the last observed boundary of an inbound flight to the first observed boundary of the next observed outbound flight at BER, using the same ICAO24 identifier. It carries both callsigns, route airports, UTC and Berlin timestamps, duration, flags, source paths and any A-CDM correspondence.

**These are surveillance-based ground-interval proxies, not exact measured landing-to-takeoff times or in-block-to-off-block turnaround durations.** No actual landing/block timestamps have been fabricated. ICAO24 linkage supports an aircraft-level candidate but remains subject to missing flights, aircraft/transponder identification issues and inferred-airport errors. Airport distance and alternative-candidate metadata are retained for stricter screening.

## Validation performed

Independent exported-data checks passed for all 11,203 pairs: shared source aircraft identity, BER airport endpoints, source timestamp linkage, interval arithmetic, unique departure usage, no invented actual timestamps, exact core-subset membership, unique reference correspondence and reconciliation of paired plus unpaired departures. Date coverage contains every requested calendar date. The collector's local-day boundaries were checked across the 25-hour October 25 DST transition. Raw-response hashes are checked before building.

The build is reproducible with `tools/collect_ber_opensky.py`, `tools/build_ber_history.py` and `tools/verify_ber_history.py`. Credentials are stored with Windows-user encryption; tokens and secrets are not included in datasets. Neither the simulator nor the collection automation was changed.

## Recommended use in the thesis

Use the pairing-screened dataset as an initial aircraft-linked observational layer. Analyze interval duration, overnight parking, airline/aircraft contexts where supported by references, daily coverage and uncertainty. Keep sparse dates outside the principal calibration/evaluation study. Do not feed final observed departure endpoints into a simulator and then claim agreement as independent validation. Stand-level and service-duration calibration still require appropriate actual observations or explicitly documented assumptions.

See `data/ber_history/README.md` for the schema, matching rules and source documentation. OpenSky's [field documentation](https://openskynetwork.github.io/opensky-api/python.html) and [FAQ](https://opensky-network.org/about/faq) explain its inferred flight boundaries and nightly processing.
