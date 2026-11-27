# Landing-to-next-takeoff linkage status

The collected BER A-CDM observations cannot currently yield complete landing-to-next-takeoff rows. All 53 raw API pages under `data/acdm/raw/*/page_*.json` were inspected: their record schemas contain departure fields, with no landing, in-block or inbound-flight timestamp fields. Raw page occurrences overlap and include other dates; they were inspected for schema coverage, not pooled into independent observations.

`turnaround_linkage_pending.csv` contains one pending row per finalized departure record, retaining its registration, departure identifiers, target times, ATOT and source location. All arrival fields and turnaround durations are blank. `is_complete_turnaround=False` in every row. Canceled flights and departures without observed ATOT are retained with explicit status flags. The registration match key removes punctuation and uppercases the original registration; the original is preserved separately. A match key is a linking aid, not proof of aircraft identity or an arrival match.

There are **zero complete observed turnarounds** in this output. Do not import this pending table into simulation as though it supplies arrival demand or observed turnaround durations. TOBT is a target; it is not substituted for actual off-block time. `taxitime` is not used to infer either landing or off-block time. Two successive BER departures of the same aircraft include an intervening flight rotation and cannot stand in for an arrival/departure pair.

The older files were checked as possible secondary sources:

- `acdm.csv`: another departure-only table, with no arrival timestamps.
- `BER_Turnarounds_MIXED_REAL_SYNTHETIC.csv`: arrival/departure flight labels and times, but no aircraft registration and unresolved row-level real/synthetic provenance.
- Lab2 final reconstructed BER dataset: no aircraft registration and collection dates preceding these November snapshots.
- Lab2 OpenSky-derived case table: includes ICAO24-based candidate links, but its BER observations are from December 2025, not November 2026; first/last observation semantics also require verification.

No secondary data were merged into the new observed A-CDM table. Existing historical reconstructions can be analyzed separately with their limitations, not presented as completed November A-CDM turnarounds.

## Required additional arrival source

For each inbound arrival, obtain actual landing time (or actual in-block time), aircraft registration or a verified mapping from ICAO24, BER airport identity, inbound flight identifier, timestamp timezone and source provenance. For stand turnaround duration, both actual in-block and actual off-block are needed. For landing-to-takeoff ground interval, actual landing and the following actual takeoff are needed.

Matching must require the same aircraft at BER, compatible verified timezones, chronological arrival before departure, and a uniquely supported next-leg pairing. Ambiguous pairs, aircraft swaps, coverage gaps, cancellations, overnight parking and diversions need review flags. Do not apply an arbitrary maximum duration that silently removes overnight ground stays; classify such stays separately under documented rules.

The next step is to obtain a compatible arrival source for the November collection dates, then perform and audit those joins. This task only prepared the matching worklist; it did not request new API data or change the collection schedule.
