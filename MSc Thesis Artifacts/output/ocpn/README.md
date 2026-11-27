# BER MSc OCPN study package

Prepared 13 November 2026. This is an executable study derivative, not a validated BER digital twin. István Koren's original `airport-extended.ocpn` was not edited. Its SHA-256 is recorded in each build manifest.

## Open these files

| File | Purpose | Checked |
|---|---|---|
| `BER_MSc_2026-11-01.ocpn` | Recommended starting model: 271 empirical arrival cases, 235 aircraft | All 271 completed; resources returned |
| `BER_MSc_2026-11-08.ocpn` | Separate later-date model: 238 cases, 212 aircraft | All 238 completed; resources returned |
| `BER_MSc_all_core.ocpn` | All 10,940 prepared core interval rows | Engine loaded all 10,940 demand tokens; full run not performed |
| `BER_MSc_timing_baseline.ocpn` | Same November 1 demand, retaining original service-time functions | All 271 completed; comparison setup, not the unchanged professor baseline |

Use OCPN Studio's **Open** command and select the `.ocpn`. The prepared demand is embedded: no CSV import is needed. Reset before a new replication. Use the full model cautiously; per-day models are easier to inspect and run.

The current browser could not be automated (`Debugger unattached`). Validation used Studio's actual `@rwth-pads/cpnsim` 0.6.2 WASM engine, with equivalent port/socket flattening. Browser UI verification remains outstanding. See `validation_report.json` for the performed integrity checks; these are technical completion checks, not empirical accuracy results.

## What changed

1. Replaced infinite synthetic flight generation with a finite, timestamped timetable from `ber_ground_intervals_core_proxy.csv`. Cases are ordered by inbound last-seen UTC. The epoch is UTC midnight on the first input date; offset-aware source timestamps preserve daylight-saving differences.
2. Preserved the same ICAO24 aircraft across each inbound/outbound pair. Arrival and departure callsigns come from the prepared rows. An aircraft is consumed from its identity-specific availability pool and released after simulated takeoff. A subsequent observed arrival waits if its aircraft is still in this airport simulation. Off-airport travel is not simulated or inferred.
3. Removed synthetic outstation flight time, the fictitious airport's inbound curfew and extra pre-landing flight delay before the observed arrival input. Runway contention, landing roll and taxi-in remain simulated. Input availability is the OpenSky boundary proxy, not a measured landing timestamp.
4. Changed narrowbody cleaning, fueling and boarding to the literature models below. Other aircraft sizes retain the original illustrative functions. Vehicle access time remains separate where the baseline includes it.
5. Kept carrier profile `unknown`: no unsupported low-cost/full-service timing coefficient is invented. Disabled Schengen stand segregation because route context is incomplete; retained physical size compatibility. The boolean field remains for schema compatibility and is not an observed classification.
6. Replaced misleading TOBT/TSAT event labels with assumed departure-planning steps. No observed departure, TOBT or TSAT is used to force completion. Observed outcomes remain in the external case CSV for later evaluation.
7. Added cleaning, fueling and boarding interval monitors; corrected the stand monitor to say **available**, rather than occupied. Cleaning includes vehicle travel; the remote boarding interval includes bus access. Synthetic weather is explicitly labeled.
8. Added reusable scenario controls for load factor, number of cleaning teams and service-time scale. These enable assumption sensitivity and conditional resource experiments.

The six parallel threads, resource contention, vehicle positions, fuel supply mechanisms, PRM branches, ULD handling and process dependencies are inherited from the professor's model. They are not claimed as the student's new contribution. The new contribution at this stage is the traceable empirical demand adapter, paired identities, evidence-informed timing changes, assumption separation and evaluation-ready exports.

## Service-time evidence

All formulas below produce minutes before conversion to engine milliseconds.

| Service | Narrowbody model | Interpretation |
|---|---|---|
| Cleaning | `5 + Weibull(shape=2.16, scale=6.76)` | Transferred literature assumption; vehicle travel added separately |
| Fueling | `2 + Gamma(shape=1.64, scale=9.12)` | Transferred total service duration; mean 16.956 min; not a BER pump-rate calibration |
| Boarding | `2.3 + 0.075 × passengers` | Deterministic mean reference; not a complete stochastic distribution |

The engine uses **scale first**: `weibull(6.76, 2.16)` and `gamma(9.12, 1.64)`. The distribution order was checked in official simulator source. Fueling resource dispatch, supply guards and tanker consumption remain in place, but the narrowbody duration itself is sampled from the literature distribution rather than derived from assumed uplift/flow. Neither literature fit establishes universal LCC/FSC differences.

References:

- Schultz, M., Kunze, T., Oreschko, B., and Fricke, H. (2012). *Dynamic turnaround management in a highly automated airport environment*. ICAS 2012. [Paper](https://www.icas.org/icas_archive/ICAS2012/PAPERS/808.PDF).
- Schultz, M. (2018). *Fast Aircraft Turnaround Enabled by Reliable Passenger Boarding*. Aerospace, 5(1), 8. [DOI: 10.3390/aerospace5010008](https://doi.org/10.3390/aerospace5010008).
- [OCPN Studio source](https://github.com/ELTE-DSED/ocpn-studio), especially `src/hooks/useSimulationController.ts` and `src/components/SimulationPanel.tsx`; [cpnsim source](https://github.com/rwth-pads/cpnsim), `src/simulator.rs`. Original copyright/license retained in `LICENSE-Studio.txt`.
- [OCEL JSON specification](https://www.ocel-standard.org/specification/formats/json/).

## Data and assumptions that must stay visible in the paper

- These are same-ICAO24 adjacent observed BER arrival/departure proxies, not certified rotations. Missing observations can create incorrect pairings. Core screening is not proof of complete surveillance coverage.
- All-core includes 54 arrivals on September 30 whose paired departure falls in the requested period. The prepared core has arrivals through November 9; it does not establish complete coverage through November 13. Do not claim 10,940 exact AIBT–AOBT observations.
- OpenSky inbound last-seen and outbound first-seen are airborne boundary proxies. The model does not reconstruct measured block times or internal ground-service events. Use simulated input-release-to-takeoff for a proxy comparison, and keep simulated AIBT–AOBT separate.
- A-CDM aircraft type/operator candidates are used when supported by the included type map. Unsupported/missing types use an explicitly assumed A320 configuration. The first case establishes a stable aircraft configuration within a build; later candidate disagreements are not reconciled. `*_cases.csv` exposes original candidates alongside actual model types. Seats are scenario values, not observed passenger capacities.
- Passenger counts are assumed at 85% of scenario seat count for both legs. PRM demand is set to zero in this initial data scenario because it is unobserved; the inherited PRM topology remains. Sector duration is assumed at 120 minutes. Carrier class is unknown. None is estimated from ground interval length.
- The inherited 25-stand geometry, two runways, service-resource counts, taxi times, weather, optional-service probabilities and remaining durations are fictitious study assumptions, not verified BER infrastructure or measurements. Inherited runway names may still identify the original fictional example.
- Long ground intervals include parking and schedule buffers. This version starts handling on arrival and departs when ready; it has no measured departure schedule or overnight parking policy. It therefore predicts a service-completion scenario, not an airline's complete timetable behavior. Stratify short/long intervals before empirical assessment; do not force observed departure times to conceal this limitation.
- Individual narrowbody timings are literature-informed; the aggregate model is **not fitted or validated against BER outcomes yet**. Completed runs demonstrate executable behavior only. Repeated replications and uncertainty intervals are required before reporting comparisons. The WASM API does not expose random-seed control.

## Promenade handoff

`BER_MSc_2026-11-01.ocel.json` contains **10,288 simulated events and 1,247 objects**. The later-date log contains **9,046 simulated events and 1,123 objects**. These are simulated logs, not measured Berlin service event logs.

For later Promenade analysis, import the OCEL JSON log and discover/analyze its object-centric process. Keep the `.ocpn` as the executable OCPN Studio source. Direct import of this colored, hierarchical `.ocpn` into Promenade has not been verified. No Promenade upload or analysis was performed in this step.

Exports reuse Studio's object decomposition and relationship logic, then normalize CPN type names (`int`, `real`, `bool`) to OCEL names (`integer`, `float`, `boolean`) and convert primitive values to their native JSON types. Checks cover unique identifiers, typed attributes, timestamps and non-dangling e2o/o2o links. These are custom integrity checks; an official JSON-schema validation was not performed.

Important objects include `Turnaround`, inbound/outbound `Flight`, persistent `Aircraft`, `Stand`, `Fueller` and `CleaningTeam`. Join the external `*_cases.csv` using `study_case_id` or the model flight IDs; in OCEL, type prefixes produce IDs such as `flight_DEP-BER-00001`. Do not merge case IDs from separate model variants without also retaining the variant/date identifier.

## Next paper experiments

- **RQ1:** document which observable inputs are supported; fit only identifiable boundary/aggregate quantities on training dates. Internal service distributions stay assumptions unless additional timestamps become available.
- **RQ2:** compare the original baseline and this derivative, plus the same-demand timing comparator for isolating timing changes. Freeze choices before outcome evaluation on later dates. Evaluate proxy duration error and distribution differences separately from simulated block turnaround. A single replication is insufficient.
- **RQ3:** vary cleaning teams, resource pools, passenger load and service-time assumptions. Report results as conditional scenario effects; do not claim optimized actual BER staffing.

From the project root:

```powershell
python tools/build_msc_ocpn.py --date 2026-11-01
python tools/build_msc_ocpn.py --date 2026-11-08
python tools/build_msc_ocpn.py --date 2026-11-01 --timing baseline --suffix timing_baseline
python tools/build_msc_ocpn.py --date 2026-11-01 --cleaning-teams 6 --load-factor 0.75 --service-scale 1.2 --suffix sensitivity
node tools/run_msc_ocpn.mjs output/ocpn/BER_MSc_2026-11-01.ocpn 18000
node tools/export_msc_ocel.mjs output/ocpn/BER_MSc_2026-11-01.ocpn
python tools/validate_msc_outputs.py
```

The runner uses the downloaded official runtime under `tmp/ocpn_runtime/package`; the builder reads the preserved baseline at its documented local path. Model files themselves are self-contained and can be opened in Studio without those scripts.
