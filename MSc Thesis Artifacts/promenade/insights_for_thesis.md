# Promenade analysis of the BER MSc simulation outputs

Analysis date: 13 November 2026. All figures concern **simulated behavior**, with empirical arrival demand and literature-based or inherited assumptions. They are not measurements of BER ground services.

## Scope and provenance

All three completed OCEL outputs from the package were imported into the user's **Turnaround Flights** workspace at https://app.promenade.run/:

| Scenario | Turnarounds | OCEL events | OCEL objects |
|---|---:|---:|---:|
| November 1, literature timings | 271 | 10,288 | 1,247 |
| November 8, literature timings | 238 | 9,046 | 1,123 |
| November 1, original timing functions | 271 | 10,298 | 1,255 |

The original-timing comparator has the same empirical demand adapter and other study modifications. It is not the unchanged professor baseline. November 8 is a later-date scenario; no fitted predictive calibration or completed held-out validation is claimed.

The all-core `.ocpn` contains 10,940 prepared cases but was only load-tested. **This analysis does not represent a completed 10,940-case simulation.** There is no full-period OCEL in the package to import. Do not extrapolate the daily results to the whole period.

Promenade views used: log Overview; Cases & variants with leading object type Turnaround; Performance Spectrum restricted to Turnaround; Object Dynamics / Activity Timing with Turnaround and next-after 1:1 pairing. Paired in-block/off-block results were checked against independent event-log calculations. Charts 01–06b are supplementary Python calculations from the same exported logs, not Promenade-generated charts. Images labeled `promenade` are actual application captures/exports.

An OC-DFG was successfully discovered using Promenade's SQL action and saved in the workspace. Screenshot 16 preserves the exploratory graph; it is visually dense and is not recommended as a main paper figure. The separate metro-map layout stalled and was canceled; no completed metro-map result is claimed.

## Findings useful for RQ2: timing changes and model validity

| Simulated in-block → off-block, minutes | Nov 1 literature | Nov 8 literature | Nov 1 original timings |
|---|---:|---:|---:|
| Mean | 62.33 | 59.59 | 84.95 |
| Median | 55.62 | 57.34 | 64.37 |
| 90th percentile | 72.48 | 72.83 | 80.12 |
| Maximum | 434.83 | 116.70 | 421.95 |

Promenade rounds these to means of 62, 60 and 85 minutes and medians of 56, 57 and 64 minutes. Every paired-duration analysis has zero unmatched starts. See screenshots 10, 14 and 15 and the native export 11.

For the November 1 run, the median changes by −8.75 minutes (approximately −13.6%) and the mean by −22.62 minutes. This establishes that the timing assumptions materially affect the simulated outputs. It does **not** establish a causal benefit, better predictive accuracy, or a staffing improvement: these are single stochastic runs with different random draws and branch realizations, and curfew interactions affect the tails.

An apparently good median can hide a poor distributional match. November 1's simulated planned-arrival-to-takeoff proxy has median **79.63 minutes**, close to the observed proxy median **79.12 minutes**. But its mean is **85.63 minutes**, against **156.17 observed**, giving mean bias −70.55 minutes and mean absolute discrepancy 92.09 minutes. November 8's mean bias is −101.60 minutes and MAE 116.00 minutes. These are proxy discrepancies, not errors against measured AIBT–AOBT.

The simulator starts work after arrival and departs when ready; many observed intervals include parking, timetable buffers or uncertain pairings. Therefore, stratify short operational stays and long/overnight stays, introduce independently justified departure schedule/parking behavior, and recheck linkage before fitting aggregate durations. Do not stretch cleaning or fueling merely to match all observed ground intervals. Figure 04 visualizes this issue.

## Findings useful for RQ3: queueing versus the completion constraint

| Mean simulated waiting, minutes | Nov 1 literature | Nov 8 literature | Nov 1 original timings |
|---|---:|---:|---:|
| Cleaning resource wait after deplaning | 0.018 | 0.000 | 0.096 |
| Fuel dispatch wait after handling start | 3.785 | 1.255 | 0.413 |
| Tug allocation wait after aircraft ready | 0.033 | 0.000 | <0.001 |

Fuel dispatch is the clearest queueing signal in these scenarios. November 1's 90th-percentile fuel dispatch wait is **14.20 minutes**, and its maximum is **38.28 minutes**. Cleaning-team or tug additions are not justified by these runs' waiting times. This does not mean those resources can safely be reduced at the real airport; capacities and service inputs are assumed.

The final branch reaching the six-thread handling join was recovered from the actual output-token availability timestamps, including any post-transition arc delay:

| Last handling branch ready | Nov 1 literature | Nov 8 literature | Nov 1 original timings |
|---|---:|---:|---:|
| Cabin / boarding | 230 (84.9%) | 192 (80.7%) | 267 (98.5%) |
| Fuel | 21 (7.7%) | 10 (4.2%) | 0 |
| Baggage hold | 20 (7.4%) | 36 (15.1%) | 4 (1.5%) |

Thus, **the largest queue is not automatically the branch that determines readiness**. Most fuel waiting can be absorbed while cabin work continues. Figure 06b supports this argument, but last-to-finish frequency is not a causal bottleneck measure. A proper resource experiment must rerun the model and measure the change in final turnaround, resource time and cost.

Recommended experiments: vary fuel resource count/dispatch policy; vary cleaning capacity downward and upward to locate the onset of congestion; vary passenger load and service-time uncertainty; distinguish contact and remote stands. Keep arrival demand fixed within a date, use repeated replications, report uncertainty, and evaluate complete turnaround rather than only local waiting.

## An inherited policy that must be reviewed before empirical conclusions

Promenade's turnaround performance spectrum shows three November 1 flows extending into the next morning. Direct paired analysis finds **3 cases with start-up approval → off-block over 30 minutes**, with intervals of approximately **326.48, 292.75 and 350.90 minutes**. The original-timing scenario has 8 such cases and also 8 cases with cleaning completion → boarding start over 30 minutes.

Code inspection identifies inherited `curfew_delay` on **e191** (start-up approval to pushback clearance) and **e106** (cleaning completion to pre-boarding queue). These use the original fictitious airport's night-ban logic. They are not independently verified BER regulations, and the time helper's timezone also requires review. Only the synthetic inbound curfew was bypassed in the first adaptation; these downstream applications remain. Preserve this version as the analyzed reference and revise policy in a separately versioned next model.

Do not interpret these long modeled delays as evidence about actual Berlin night operations. A next experiment should compare the current inherited policy with a separately verified BER policy or a clearly labeled no-curfew sensitivity scenario. Figure 05 and screenshot 09 document the issue.

## Object-centric extraction is itself a methodological result

Promenade's November 1 Overview reports **2 object graph components, with 94% of objects in the largest**. Shared aircraft, stands and vehicles join many rotations. A connected-component case definition would therefore merge much of the day rather than yield one aircraft turnaround per case.

Leading-type Turnaround extraction returns **271 executions and 271 variants** at the chosen settings. This high variability reflects the enriched event graph, parallel interleavings and resource associations; it is not proof of 271 operational procedures or deviations. The expanded first execution includes shared-resource events such as tanker reloads and displays about 16.7 hours, which is not that turnaround's in-block-to-off-block time. Use direct Turnaround-paired milestones for duration statistics and inspect expansion scope before interpreting execution graphs. Screenshot 08 is retained as a methodological diagnostic, not an empirical turnaround-time result.

## RQ1 interpretation and suggested paper wording

The simulation provides internal event timestamps that can be analyzed in Promenade. Their availability does not make them measured observations. BER/OpenSky data inform input availability and paired identities; literature and explicit assumptions determine internal service times. Cleaning, fueling and boarding remain unidentifiable from the current boundary proxies alone.

Suggested results paragraph:

> The exported object-centric simulation logs were imported into Promenade to inspect temporal performance, shared-resource interactions and execution definitions. For the November 1 scenario, 271 matched simulated in-block/off-block pairs yielded a median of 55.62 minutes under the literature-informed timings, compared with 64.37 minutes under the same-demand original-timing comparator. Fuel dispatch exhibited more queueing than cleaning or tug allocation, while the cabin/boarding branch was last ready in 84.9% of turnarounds. These descriptive single-run results identify targets for controlled sensitivity experiments rather than establish improved empirical accuracy or optimal BER staffing. The analysis also exposed inherited curfew assumptions and case-expansion effects that must be resolved before operational conclusions are drawn.

## Figure guide

- `01_simulated_turnaround_comparison.png`: scenario distributions for RQ2.
- `02_service_duration_comparison.png`: cleaning, fueling and boarding interval distributions. Cleaning and remote boarding include access time.
- `03_resource_waiting.png`: queueing comparison for RQ3.
- `04_observed_proxy_vs_simulation.png`: observability and long-stay mismatch for RQ1/RQ2.
- `05_inherited_policy_diagnostic.png`: policy artefact diagnostic.
- `06_aircraft_identity_release_delay.png`: no arrival release delay in these three runs; a technical check, not an inbound-delay prediction result.
- `06a_shared_resource_workload.png`: distinct turnarounds per resource; counts are not time utilization.
- `06b_last_ready_handling_branch.png`: last-ready branch at the handling join.
- `07`–`15`: actual Promenade captures and native timing-chart exports, as identified by filenames. Promenade screenshots show the app's local-date display; the underlying OCEL event times remain UTC.
- `16_promenade_discovered_ocdfg.jpg`: exploratory SQL-discovered OC-DFG; dense graph, not a quantitative result.

Exact statistics, per-case values and last-ready branch assignments are included as CSV/JSON. The analysis scripts are `tools/analyze_promenade_package.py` and `tools/analyze_promenade_resources.py` in the project root. Literature/provenance and original model assumptions are documented in `output/ocpn/README.md`.
