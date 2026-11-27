# Controlled simulation pilot — v2.1

Completed 60 independent replications across 12 date/scenario cells: five runs per cell, on November 1 and November 8, 2026. All 15,270 simulated turnaround executions completed and passed case/aircraft/resource-return checks. These executions reuse **509 empirical interval cases**, not 15,270 new observed turnarounds. This is not a full-period simulation.

## Design

The design was fixed before these new runs, informed by the earlier exploratory results. It is a pilot, not an independently preregistered confirmatory study. Four cells per date cross original/literature service-time functions with inherited/disabled curfew. Two additional cells vary cleaning teams from 9 to 6 or fueling units from 4 hydrants + 4 tankers to 6 + 6, under literature timings and disabled curfew. Arrival demand, aircraft identities, passenger-load assumption and remaining model logic are held constant within each date.

Model files are in `models/`; exact settings and hashes are in companion manifests. `experiment_plan.json` specifies all runs. The original professor model and the previously analyzed package remain unchanged. The no-curfew models are sensitivity scenarios, not realistic BER replacements.

## Mean simulated in-block to off-block duration

| date | scenario | Mean block minutes | 95% lower | 95% upper |
| --- | --- | --- | --- | --- |
| 2026-11-01 | cleaning_6_no_curfew | 59.26 | 58.39 | 60.13 |
| 2026-11-01 | fuel_6plus6_no_curfew | 58.58 | 58.34 | 58.81 |
| 2026-11-01 | literature_inherited | 61.91 | 59.82 | 64.01 |
| 2026-11-01 | literature_no_curfew | 59.20 | 58.59 | 59.81 |
| 2026-11-01 | original_inherited | 86.91 | 84.83 | 89.00 |
| 2026-11-01 | original_no_curfew | 66.73 | 66.14 | 67.32 |
| 2026-11-08 | cleaning_6_no_curfew | 59.20 | 58.33 | 60.06 |
| 2026-11-08 | fuel_6plus6_no_curfew | 58.81 | 58.56 | 59.06 |
| 2026-11-08 | literature_inherited | 59.22 | 58.91 | 59.52 |
| 2026-11-08 | literature_no_curfew | 59.03 | 58.45 | 59.61 |
| 2026-11-08 | original_inherited | 72.73 | 69.30 | 76.17 |
| 2026-11-08 | original_no_curfew | 66.07 | 65.78 | 66.37 |

Intervals are Student-t 95% confidence intervals for the mean of **five replication-level means**. They describe Monte Carlo variability conditional on the fixed input/model assumptions. They do not quantify uncertainty in passenger loads, measured input proxies, service distributions, airport capacities or model structure. Negative lower endpoints, if any, are mathematical interval estimates and not feasible negative durations.

## Exploratory differences between scenarios

| date | contrast | Difference minutes | 95% lower | 95% upper |
| --- | --- | --- | --- | --- |
| 2026-11-01 | timing_inherited | -25.00 | -27.45 | -22.54 |
| 2026-11-01 | timing_no_curfew | -7.53 | -8.24 | -6.82 |
| 2026-11-01 | policy_literature | -2.72 | -4.78 | -0.65 |
| 2026-11-01 | policy_original | -20.18 | -22.23 | -18.13 |
| 2026-11-01 | cleaning_capacity | 0.07 | -0.84 | 0.97 |
| 2026-11-01 | fuel_capacity | -0.62 | -1.23 | -0.02 |
| 2026-11-08 | timing_inherited | -13.52 | -16.94 | -10.09 |
| 2026-11-08 | timing_no_curfew | -7.04 | -7.62 | -6.47 |
| 2026-11-08 | policy_literature | -0.18 | -0.76 | 0.39 |
| 2026-11-08 | policy_original | -6.66 | -10.09 | -3.23 |
| 2026-11-08 | cleaning_capacity | 0.17 | -0.72 | 1.05 |
| 2026-11-08 | fuel_capacity | -0.22 | -0.79 | 0.35 |

Each difference is scenario A minus B, as specified in `scenario_contrasts.csv`. Timing contrasts mean literature minus original; policy contrasts mean disabled minus inherited; cleaning means 6 minus 9 teams; fueling means 6+6 minus 4+4 units. Negative values indicate shorter simulated block turnaround. Welch 95% intervals use independent runs, with no paired seeds and no multiple-comparison adjustment. An interval crossing zero means this pilot does not resolve the direction under that comparison. An interval excluding zero is still conditional model evidence, not an empirical BER causal finding.

The additional exploratory timing-by-policy interaction is the literature-minus-original difference under inherited policy, minus that difference with curfew disabled. A negative estimate means the apparent literature timing benefit is larger under the inherited policy. This contrast was added while inspecting the pilot, and is not a preregistered confirmatory test.

| date | interaction_minutes | ci95_low | ci95_high |
| --- | --- | --- | --- |
| 2026-11-01 | -17.46 | -19.96 | -14.97 |
| 2026-11-08 | -6.48 | -9.88 | -3.08 |

## Mean waiting times

| date | scenario | metric | mean |
| --- | --- | --- | --- |
| 2026-11-01 | cleaning_6_no_curfew | mean_fuel_wait_min | 3.00 |
| 2026-11-01 | cleaning_6_no_curfew | mean_clean_wait_min | 0.35 |
| 2026-11-01 | cleaning_6_no_curfew | mean_tug_wait_min | 0.00 |
| 2026-11-01 | fuel_6plus6_no_curfew | mean_fuel_wait_min | 0.17 |
| 2026-11-01 | fuel_6plus6_no_curfew | mean_clean_wait_min | 0.01 |
| 2026-11-01 | fuel_6plus6_no_curfew | mean_tug_wait_min | 0.02 |
| 2026-11-01 | literature_inherited | mean_fuel_wait_min | 2.64 |
| 2026-11-01 | literature_inherited | mean_clean_wait_min | 0.00 |
| 2026-11-01 | literature_inherited | mean_tug_wait_min | 0.02 |
| 2026-11-01 | literature_no_curfew | mean_fuel_wait_min | 3.04 |
| 2026-11-01 | literature_no_curfew | mean_clean_wait_min | 0.03 |
| 2026-11-01 | literature_no_curfew | mean_tug_wait_min | 0.02 |
| 2026-11-01 | original_inherited | mean_fuel_wait_min | 0.67 |
| 2026-11-01 | original_inherited | mean_clean_wait_min | 0.23 |
| 2026-11-01 | original_inherited | mean_tug_wait_min | 0.44 |
| 2026-11-01 | original_no_curfew | mean_fuel_wait_min | 0.61 |
| 2026-11-01 | original_no_curfew | mean_clean_wait_min | 0.20 |
| 2026-11-01 | original_no_curfew | mean_tug_wait_min | 0.01 |
| 2026-11-08 | cleaning_6_no_curfew | mean_fuel_wait_min | 1.53 |
| 2026-11-08 | cleaning_6_no_curfew | mean_clean_wait_min | 0.22 |
| 2026-11-08 | cleaning_6_no_curfew | mean_tug_wait_min | 0.01 |
| 2026-11-08 | fuel_6plus6_no_curfew | mean_fuel_wait_min | 0.07 |
| 2026-11-08 | fuel_6plus6_no_curfew | mean_clean_wait_min | 0.00 |
| 2026-11-08 | fuel_6plus6_no_curfew | mean_tug_wait_min | 0.00 |
| 2026-11-08 | literature_inherited | mean_fuel_wait_min | 1.89 |
| 2026-11-08 | literature_inherited | mean_clean_wait_min | 0.00 |
| 2026-11-08 | literature_inherited | mean_tug_wait_min | 0.00 |
| 2026-11-08 | literature_no_curfew | mean_fuel_wait_min | 2.04 |
| 2026-11-08 | literature_no_curfew | mean_clean_wait_min | 0.00 |
| 2026-11-08 | literature_no_curfew | mean_tug_wait_min | 0.00 |
| 2026-11-08 | original_inherited | mean_fuel_wait_min | 0.29 |
| 2026-11-08 | original_inherited | mean_clean_wait_min | 0.08 |
| 2026-11-08 | original_inherited | mean_tug_wait_min | 0.00 |
| 2026-11-08 | original_no_curfew | mean_fuel_wait_min | 0.27 |
| 2026-11-08 | original_no_curfew | mean_clean_wait_min | 0.06 |
| 2026-11-08 | original_no_curfew | mean_tug_wait_min | 0.02 |

Cleaning waiting is deplaning completion to cleaning start (PRM demand remains assumed zero); fuel waiting is handling start to fuel dispatch, excluding subsequent vehicle travel; tug waiting is aircraft-ready to allocation. These intervals cannot be compared directly to actual BER queues without observed service timestamps. Resource count is a capacity proxy, not a monetary cost estimate or a staffing recommendation.

## Interpretation for the thesis

With curfew disabled, literature timings reduce mean simulated block duration by 7.53 minutes on November 1 (Welch 95% interval: 6.82–8.24 minutes shorter) and 7.04 minutes on November 8 (6.47–7.62 shorter). Under the inherited policy the corresponding differences are much larger, 25.00 and 13.52 minutes. Consequently the earlier apparent benefit mixes timing changes with their interaction with policy logic; it cannot be attributed to more accurate service times.

Increasing fueling capacity from eight to twelve units reduces final turnaround by only 0.62 minutes on November 1 (difference interval: −1.23 to −0.02 minutes) and 0.22 minutes on November 8 (−0.79 to +0.35). The second interval crosses zero. Large fuel-queue reductions therefore do not demonstrate a consistent large improvement in overall turnaround. Reducing cleaning teams from nine to six yields small estimated increases, 0.07 and 0.17 minutes, with both intervals crossing zero; this is not evidence of equivalence or a justified staffing cut.

- **RQ1:** Available data determine empirical demand and aircraft pairing. Internal durations, carrier profile, passenger count, PRM demand and resource capacities remain assumptions. Repeated simulation does not make unobserved services identifiable.
- **RQ2:** Timing and policy effects should be evaluated separately. Repeated differences establish stability of model outputs under this design; they do not establish improved predictive accuracy. Observed proxy comparisons and short/long-stay stratification remain necessary. The comparator uses the original timing functions inside the same adapted demand model, not the untouched professor example.
- **RQ3:** Compare the resource scenario's effect on final turnaround with its local queue effect. Queue reduction alone is not evidence that the resource controls overall completion. Before any optimization claim, broaden uncertainty sensitivity and use a verified operational policy.

## Confirmed policy/clock limitation

BER's [official guidance](https://corporate.berlin-airport.de/de/nachhaltigkeit/umwelt/fluglaerm/hinweise-zum-nachtflug.html) confirms a core 00:00–05:00 night-flight restriction plus shoulder constraints. The inherited model evaluates its hour condition in UTC; during these November dates this corresponds to 01:00–06:00 Berlin local time. It also applies delays before boarding and pushback rather than representing full movement eligibility and exceptions. See `policy_review.md`, including the official engine source and airport references. A disabled-curfew scenario is therefore a diagnostic contrast, not the preferred real policy.

## Limits and next milestone

The WASM runtime does not expose seed control. Each run uses fresh runtime randomness; results are unpaired. Exact outputs, model hashes and per-case metrics are saved, but bit-for-bit reruns cannot be promised. Five runs per cell provide a pilot estimate; replication count and input sensitivity should be extended before strong conclusions. Models retain fictitious geometry/resources, assumed passenger loads and no complete airline departure timetable or overnight parking policy. The demand cohort includes matched core arrival–departure intervals only; unmatched movements and other excluded traffic do not compete for resources. These are cohort-level scenarios, not complete airport-wide congestion estimates. Each daily run starts with free stands/resources, with no calibrated overnight occupancy or warm-up history. Queue estimates are conditional on that initial state. The remaining mismatch with long observed ground intervals cannot be solved by selecting a faster timing function alone.

Next milestone: prepare a separately versioned local-time movement-policy model with explicit assumptions about shoulder windows and exceptions, review it with the professor, then evaluate observable proxy quantities on separately selected dates. Keep these pilot scenarios as archived references. No parameter selection was optimized against November 8 outcomes in this pilot.

## Reproduction environment

The archived scripts use Python with numpy, pandas, scipy and matplotlib, plus Node.js and the official `@rwth-pads/cpnsim` 0.6.2 WASM runtime installed at `tmp/ocpn_runtime/package/`. The archive includes the twelve built models, their source-case CSVs/manifests, the frozen run plan, per-case results and study scripts; it does not bundle the runtime or complete upstream raw-data collection. Plan paths refer to the study workspace and need adjustment after relocation. Rebuilding models additionally requires the prepared BER core CSV in its documented workspace path. Random-seed control is unavailable, so reproduction means repeating the experimental procedure rather than exactly reproducing each stochastic output.

## Files

- `01_timing_policy_replications.png`: timing/policy means with all run means and confidence intervals.
- `02_resource_sensitivity_replications.png`: final turnaround and fuel-queue effects.
- `03_controlled_contrasts.png`: unpaired scenario differences and intervals.
- `replication_metrics.csv`, `scenario_summary.csv`, `scenario_contrasts.csv`: exact values.
- `runs/*_cases.json`: per-case values for each replication; `runs/*_summary.json`: settings and integrity results.
- `validation.json`: completion/coverage/hash audit.
