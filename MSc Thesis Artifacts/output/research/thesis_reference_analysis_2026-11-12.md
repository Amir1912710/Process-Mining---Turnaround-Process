# Thesis reference and feasibility analysis

Prepared for Amir Abdelsayed, 12 November 2026.

## Main recommendation

Keep **Data-Driven Object-Centric Simulation for Airport Turnaround Analysis and Resource Optimization** as the working direction. Preserve OCPN Studio as the core simulator, as selected in the September meeting. The defensible contribution is to establish how sparse observations can calibrate and evaluate observable parts of that simulation, then examine resource and delay effects under explicit assumptions.

The current data support a departure-focused empirical pilot. They do not yet identify measured cleaning, fueling, boarding or baggage durations, nor validate the entire turnaround process. A useful MSc contribution can include this observability boundary: explain which parameters are supported by measurements, which require literature assumptions, and how uncertainty changes policy conclusions. This is a proposed contribution, not an established claim of novelty against all literature.

## 1. Materials actually reviewed

- GitHub repository [Process-Mining---Turnaround-Process](https://github.com/Amir1912710/Process-Mining---Turnaround-Process), main tree at commit `6eb96b0e35aea86efdaac10e2e066de01baf9cf4` as returned during this review.
- Lab1 January 12 final report, Lab2 June 13 final report, Lab1 exported bibliography, Lab2 case construction and event-log code, data-quality and airline-comparison reports.
- Lab2 `final/cleaned_dataset.csv` and `data/processed/turnaround_cases.csv`, downloaded read-only for analysis. Earlier processed OpenSky outputs and the final BER study are different datasets.
- Local September 24 meeting slides, including their embedded paper screenshots; thesis proposal slides; existing project-state review of the October draft and extended airport model.
- Finalized Berlin daily CSVs and collection manifests under `data/acdm/days`. Failed attempts, previews and superseded snapshots were excluded from the empirical total.
- The professor's notes supplied in this chat: deepen analysis, investigate JFK, assess what A-CDM can establish, replicate the LAX study, explain RQ1/RQ3, and start the MSc paper.

Literature coverage below distinguishes papers whose substantive text was available from records/abstracts only. It is a targeted starting review, not a systematic literature review. No simulation, optimization or new predictive model was run. No external LLM service received the datasets.

## 2. What Lab1 and Lab2 establish

### Lab1: a methodological starting point

The report describes 30,550 reconstructed cases. Internal activities were synthesized proportionally between flight timestamps. Consequently, discovery and fitness describe the constructed log; they do not independently establish the airport's real cleaning/fueling concurrency. The report itself recognizes that the perfect classification score follows from using duration to predict a label defined from duration. Treat this as pipeline groundwork, not evidence of operational prediction accuracy.

The reported mean ground interval of about 18.76 hours includes long stays. Separate short turnarounds, overnight parking, maintenance and ambiguous matches before interpreting ground time operationally. ADS-B first/last observation timestamps also need source-semantic verification before being equated with wheels-on/wheels-off events.

### Lab2: a closer simulation foundation

The final report and CSV describe **2,070 BER cases**, in February 21–March 4 and April 17–24, 2026 collection windows. I reproduced the overall mean of **146.36 minutes** and median of **138 minutes** from the final CSV, using the report's next-day correction when departure precedes arrival. Those are arrival-to-departure intervals under the source definitions; they are not automatically AIBT-to-AOBT turnaround durations.

The final report describes OCPN aircraft/resource interactions and estimated internal activity timing. It reports a Random Forest F1 of 0.892, which was not retrained here. Scheduled ground time can be a legitimate early feature if genuinely available then; its strong relationship to the target alone does not prove leakage. However, verify its provenance and prediction-time availability. More critically, using the actual departure endpoint to distribute simulated durations makes agreement with that same endpoint a reconstruction result rather than independent predictive validation. In the MSc experiment, release the simulated departure from that constraint.

The earlier processed pipeline has **28,417 OpenSky-derived cases**, with 27,944 cases retained in its four-event log. Its code constructs AIBT/AOBT using fixed taxi offsets. Do not merge those proxy milestones with the new API observations as though all were measured.

The existing app-log code also orders TOBT/EOBT/TSAT/CTOT by their target times. A target time is not the time at which the target was issued or revised. This distinction matters for both process discovery and prediction. Rott et al. [1] explicitly discuss target-time events creating excessive apparent process variants.

### Bibliography repairs

The final Lab2 bibliography has dates that should be corrected before reuse: Fricke & Schultz's *Improving Aircraft Turn Around Reliability* is **2008**, not 2018 [8]; the reviewed Luo et al. manuscript is **2022**, not the report's 2019 entry [4]. Cite Halmesaari as a master's thesis [12]. The ESREL volume entry is a whole edited book: if using a particular safety chapter, identify its actual chapter author/title instead of citing the editors as the study authors. Other undated conference entries need individual verification.

## 3. Berlin A-CDM: current empirical evidence

Only these finalized daily datasets were found:

| STD date selected from API | Departure records | ATOT present |
|---|---:|---:|
| 2026-11-01 | 289 | 283 |
| 2026-11-05 | 257 | 251 |
| 2026-11-08 | 264 | 250 |
| Total | **810** | **784** |

All 810 record IDs are unique across these files. TOBT and TSAT each have 27 missing values; CTOT is present for 166 records; aircraft registration is missing for 11, parking position for 13. Absence of CTOT can reflect unregulated flights rather than defective data, so do not impute it as zero or call every absence an error. Completeness of the airport's full traffic day and the raw API timestamp timezone remain unverified in the manifests.

| Difference computed directly from saved timestamps | Matched records | Mean (min) | Median (min) | Interpretation |
|---|---:|---:|---:|---|
| TSAT − TOBT | 783 | 1.35 | 0.00 | Target sequencing gap; not measured queue waiting |
| ATOT − TSAT | 782 | 12.97 | 12.68 | Actual take-off relative to target start-up; not actual taxi-out |
| ATOT − TOBT | 782 | 14.32 | 13.46 | Composite target-to-takeoff interval |
| TOBT − STD | 783 | 9.66 | 0.00 | Target/schedule difference; confirm STD's milestone meaning |
| ATOT − CTOT | 166 | 1.47 | 0.97 | Take-off/slot difference for CTOT-bearing records |

Seven TSAT−TOBT values are negative, and one ATOT−TSAT value is negative. Flag and inspect these records before model fitting; they may involve target updates, recording semantics or timing inconsistencies. Preserve both an unfiltered audit and a documented clean analysis. The API `taxitime` field has mean 10.32 minutes, but its estimated/planned/actual meaning must be established before calibrating actual taxi behavior.

The files contain no AIBT, AOBT, service start/end events, crew/equipment assignments or target revision histories. Therefore:

- Analyze missingness, target relationships, take-off/slot differences, aircraft/airline/stand/runway context and departure demand patterns.
- Use final target-to-actual differences descriptively. A model using end-of-day final TOBT/TSAT values is not automatically a forecast available hours earlier.
- Do not call ATOT−STD pure departure delay if STD refers to scheduled off-block: that mixes milestone definitions and includes a surface phase.
- Do not infer AOBT as ATOT minus `taxitime` without explicitly labeling the result a proxy and validating the field semantics.
- Neither stand occupancy nor causal effects of extra ground crews are observed directly here.

Three separated days are suitable for a pilot, with very weak evidence for generalization. A chronological or leave-one-day-out analysis could illustrate stability, but cannot establish seasonal robustness. Do not randomly split records and imply independent day-level validation.

## 4. The professor's LAX and delay-propagation papers

The paper images embedded in slide 3 of the September 24 deck identify these **exact two papers**:

1. **Mark Hansen (2002)**, *Micro-level analysis of airport delay externalities using deterministic queuing models: a case study* [6]. This is the LAX study. It studies arrival runway queues and the delay a flight imposes on other flights; it is not a study estimating internal turnaround service durations.
2. **Nabin Kafle and Bo Zou (2016)**, *Modeling flight delay propagation: A new analytical-econometric approach* [7]. It separates propagated and newly formed delay while accounting for flight and ground buffers. It is not specifically a JFK-only study.

### What replicating Hansen would require

Obtain the full paper and reproduce its exact queue, runway and counterfactual assumptions. Required concepts include arrival demand/queue-entry times, service capacity or separations, runway configuration and baseline delay. A first-come-first-served demonstration can use start time `s_i=max(a_i,c_(i-1))`, completion `c_i=s_i+p_i`, and waiting `w_i=s_i-a_i`, but this is a generic illustrative queue, not a reconstruction of Hansen's full method.

A useful related OCPN experiment is a paired counterfactual: keep traffic and random draws fixed, perturb one flight's timing or change a resource policy, and measure the change in delay for all other flights. The direct delay, external delay and total delay should be reported separately. This is an adaptation of the externality question to shared airport resources, not a completed LAX replication. Removing an aircraft can also remove its demand, so define and justify the intervention carefully.

**Berlin feasibility:** the current departure-only snapshots cannot empirically replicate Hansen's arrival-queue study. ATOT is an observed output, not a queue-entry observation. Fitting capacity to ATOT and validating against that same ATOT would be circular. Ground-resource counterfactuals remain conditional simulation results until the queue/resource parameters are independently supported.

**Kafle & Zou feasibility:** testing aircraft-rotation propagation requires linked inbound/outbound actual and scheduled times across consecutive legs and an explicit buffer definition. Berlin departure snapshots alone lack those linked arrival observations. Correlation between nearby departures does not prove one delayed the other.

## 5. JFK: what is already available, and what to use

The repository's earlier `turnaround_cases.csv` already contains these selected OpenSky-derived intervals. Statistics below are recomputed from that file, before extra matching validation:

| Airport | Cases | Mean interval (min) | Median (min) | Missing aircraft type |
|---|---:|---:|---:|---:|
| JFK / KJFK | 159 | 103.48 | 95.20 | 34 |
| LAX / KLAX | 197 | 111.13 | 105.90 | 36 |
| BER / EDDB | 161 | 72.67 | 68.23 | 26 |

Their arrival dates are all December 11, 2025 in UTC. These are a selected sample subject to the pipeline's duration filters, aircraft matching and observation coverage. They are not comparable representative airport populations. The apparent airport differences can reflect aircraft/airline mix, censoring, time-window boundaries and matching error. Do not interpret them as airport efficiency rankings.

For the professor's next JFK experiment, use **BTS Reporting Carrier On-Time Performance** [16]. The documented fields include scheduled/actual gate arrival/departure, wheels-on/off and tail number. Pair consecutive legs of the same aircraft at JFK, handle local dates/timezones and midnight explicitly, remove or separately classify diversions/cancellations and ambiguous rotations, and distinguish short service turns from overnight stays. BTS covers reported operations, not all JFK traffic or all international carriers. It still does not observe cleaning or fueling tasks.

Recommended JFK analysis: derive gate-to-gate turnaround boundaries, inbound delay, outbound delay, scheduled ground interval, and delay absorption across the matched rotation; stratify by carrier, time and scheduled interval, then evaluate on later dates. Estimating operational buffer requires a defensible minimum service-time model, not simply calling every scheduled ground minute a buffer.

The 2016 JFK neural-network paper [13] is a candidate comparison for flight-delay prediction, not a paper confirmed in your meeting slides. Its incoming-flight prediction target differs from resource-constrained turnaround simulation. Berlin can support a separately defined departure prediction problem, but cannot reproduce its incoming-flight experiment from the current departure snapshots.

## 6. Clarifying the MSc research questions

### RQ1: calibration

**Suggested wording:** How can available A-CDM observations calibrate the observable temporal behavior of an object-centric airport simulation, and which turnaround parameters remain unidentifiable from sparse milestones?

In practice: define each observed timestamp; map it to a model event or target; select an observable response; estimate a simple empirical baseline and a context-dependent alternative; carry their uncertainty into simulation. Compare airline, aircraft, time and stand/runway context only where sample sizes permit. Literature [1–5,8,11,14–15] supports the motivation and method, but does not make missing BER internal durations observable.

With current files, begin with departure target-to-actual intervals and sequencing behavior. A stronger activity-duration RQ1 needs actual service events or an additional justified identification method. Matching aggregate turnaround duration does not uniquely identify several parallel task durations.

### RQ2: independent evaluation

**Suggested wording:** To what extent does calibration improve reproduction of held-out observable milestone behavior relative to the unchanged baseline?

Choose KPIs that are present in the evaluation data. Compare distributions and context groups, not only one mean. Use MAE for genuinely paired predicted times and distributional measures/quantiles for stochastic outputs. Evaluate interval coverage as well as point accuracy. Any generated internal OCEL remains simulated evidence; its formal validity does not validate its empirical timings [9–10].

### RQ3: decisions and external effects

**Suggested wording:** Under explicit resource and timing assumptions, how do alternative resource capacities and allocation policies affect delay, contention and delay imposed on other flights in the calibrated simulation?

Compare a fixed baseline with a small set of capacities/policies, such as an extra pushback unit, a different dispatch priority or a peak-period capacity schedule. Use repeated paired random seeds, hold demand constant, and report uncertainty plus resource cost/capacity. Report waiting, utilization and throughput as simulation KPIs; evaluate observed take-off patterns where possible. Literature [3,6–8,17] supports these decision questions. Gate occupancy and crew contention require additional empirical data to validate. Do not report a BER staffing optimum from assumed resource pools as an observed operational fact.

## 7. Prioritized annotated references

**[1] Rott, J., König, F., Häfke, H., Schmidt, M., Böhm, M., Kratsch, W., & Krcmar, H. (2023).** *Process Mining for resilient airport operations: A case study of Munich Airport’s turnaround process.* Journal of Air Transport Management, 112, 102451. [DOI](https://doi.org/10.1016/j.jairtraman.2023.102451). **Highest priority:** A-CDM data analysis, process-mining feasibility and data quality. Adapt the observable milestone analysis; do not imply your departure snapshots have Munich's full event coverage. Publisher abstract and substantive section snippets reviewed, plus your Lab reports' treatment.

**[2] Rozinat, A., Mans, R. S., Song, M., & van der Aalst, W. M. P. (2009).** *Discovering simulation models.* Information Systems, 34(3), 305–327. [DOI](https://doi.org/10.1016/j.is.2008.09.002); [institutional record](https://publications.rwth-aachen.de/record/714662/). **Highest priority:** connect log-based performance/resource information to CPN simulation and log-based evaluation. Supports the workflow, not airport-specific parameters. Metadata and abstract reviewed.

**[3] Sng, Z. Y., & Hansman, R. J. (2019).** *A Petri Net Framework for the Representation and Analysis of Aircraft Turnaround Operations.* MIT ICAT Report 2019-05. [Open institutional record and PDF](https://hdl.handle.net/1721.1/121164). **Highest priority:** empirical calibration, Monte Carlo, critical paths and operational changes. A close methodological example for RQ1/RQ3, using Changi rather than BER. Research report, not a journal article; detailed repository abstract reviewed.

**[4] Luo, M., Schultz, M., Fricke, H., & Desart, B. (2022).** *Data-driven fusion of turnaround sub-processes to predict aircraft ground time.* ATRS conference manuscript. [Author/institution-hosted full text](https://fis.tu-dresden.de/portal/files/68852159/ATRS_2022_mlu_v4.0_final.pdf). **Highest priority:** subprocess overlaps and contextual prediction. The needed service-duration fields exceed current BER API coverage. Cite the reviewed 2022 manuscript; do not copy the Lab2 2019 date. Substantive manuscript passages reviewed.

**[5] Cui, Y., Ma, L., Ding, Q., He, X., Xiao, F., & Cheng, B. (2024).** *Aircraft turnaround time dynamic prediction based on Time Transition Petri Net.* PLOS ONE, 19(7), e0305237. [DOI and open article](https://doi.org/10.1371/journal.pone.0305237). **Highest priority:** temporal process structure and probabilistic prediction. Useful RQ1 comparison; its reported accuracy is not a benchmark achievable with your different data. Open article reviewed.

**[6] Hansen, M. (2002).** *Micro-level analysis of airport delay externalities using deterministic queuing models: a case study.* Journal of Air Transport Management, 8(2), 73–87. [DOI](https://doi.org/10.1016/S0969-6997(01)00045-X); [Berkeley abstract](https://its.berkeley.edu/node/5831). **Professor's confirmed LAX paper.** Use for flight-level external-delay questions and counterfactual design. Full method must be obtained before claiming replication. Institutional abstract and meeting screenshot reviewed.

**[7] Kafle, N., & Zou, B. (2016).** *Modeling flight delay propagation: A new analytical-econometric approach.* Transportation Research Part B: Methodological, 93, 520–542. [DOI](https://doi.org/10.1016/j.trb.2016.08.012); [publisher](https://www.sciencedirect.com/science/article/pii/S0191261515302010). **Professor's confirmed second paper.** Use for propagation versus new delay and schedule-buffer concepts. Requires linked flight rotations beyond current BER coverage. Publisher substantive passages and meeting screenshot reviewed.

**[8] Fricke, H., & Schultz, M. (2008).** *Improving Aircraft Turn Around Reliability: Specific Aircraft Body Design Parts hamper Ground Handling and Airport Performance.* ICRAT, pp. 335–343. [Conference proceedings](https://www.icrat.org/previous-conferences/3rd-international-conference/icrat2008_proceedingscomplete.pdf). Supports empirical timing variability, dependency and Monte Carlo reasoning. Literature assumptions from this study should be labeled as transferred assumptions. Relevant proceedings text reviewed.

**[9] van der Aalst, W. M. P., & Berti, A. (2020).** *Discovering Object-centric Petri Nets.* Fundamenta Informaticae, 175(1–4), 1–40. [DOI](https://doi.org/10.3233/FI-2020-1946); [open preprint](https://arxiv.org/abs/2010.02047). Supports the multiple-object rationale. Distinguish the formalism described here from the timed colored implementation details of OCPN Studio. Abstract, institutional metadata and author-hosted method excerpt reviewed.

**[10] Berti, A., et al. (2023).** *OCEL (Object-Centric Event Log) 2.0 Specification.* Version 2.0, October 16. [Official specification](https://www.ocel-standard.org/2.0/ocel20_specification.pdf). Supports explicit objects, relationships, qualifiers and changing attributes in simulation export. A technical specification; valid export does not establish correct airport behavior. Specification abstract/metamodel description reviewed.

**[11] Schmidt, M. (2017).** *A review of aircraft turnaround operations and simulations.* Progress in Aerospace Sciences, 92, 25–38. [DOI](https://doi.org/10.1016/j.paerosci.2017.05.002). Use for background, parallel activities and simulation context. Avoid carrying old forecast figures into the Introduction as current traffic forecasts. Publisher abstract and introduction reviewed.

**[12] Halmesaari, E. (2020).** *Interpretable machine learning for prediction of aircraft turnaround times: An explainable aggregated approach.* Master's thesis, Aalto University. [Institutional repository](https://aaltodoc.aalto.fi/handle/123456789/97524). Useful XGBoost/SHAP implementation reference. Its richer operational features are not all available in BER snapshots. Thesis title page and abstract reviewed; supporting reference, not a peer-reviewed journal study.

**[13] Khanmohammadi, S., Tutun, S., & Kucuk, Y. (2016).** *A New Multilevel Input Layer Artificial Neural Network for Predicting Flight Delays at JFK Airport.* Procedia Computer Science, 95, 237–244. [DOI](https://doi.org/10.1016/j.procs.2016.09.321). Optional JFK prediction comparison. Predicts incoming-flight delay and does not validate internal turnaround resources. Publisher abstract reviewed; not confirmed as the professor's intended JFK paper.

**[14] De Falco, P., Kubat, J., Kuran, V., Rodriguez Varela, J., Plutino, S., & Leonardi, A. (2023).** *Probabilistic Prediction of Aircraft Turnaround Time and Target Off-Block Time.* SESAR Innovation Days, paper 26. [Open paper](https://engagektn.eu/wp-content/uploads/2024/01/SIDs_2023_paper_26-final.pdf). Particularly useful for predictive distributions and prediction horizons. Its defined response `TOBT_last − AIBT` is target-based, not the same as `AOBT − AIBT`. Abstract and target/metric sections reviewed.

**[15] Tang, X., Wu, J., Wu, C.-L., Ding, Y., & Zhang, S. (2025).** *Dynamic prediction of aircraft turnaround milestone times using a cascaded gradient boosting model for improved airport collaborative decision-making.* Journal of Air Transport Management, 128, 102842. [DOI](https://doi.org/10.1016/j.jairtraman.2025.102842). Recent RQ1 comparison for dynamic milestone prediction. Requires progressive operational observations absent from a single end-of-day snapshot. Publisher abstract, conclusions and author metadata reviewed.

**[16] U.S. Bureau of Transportation Statistics.** *Reporting Carrier On-Time Performance: field definitions and Airline On-Time Statistics.* [Fields](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ); [data access](https://transtats.bts.gov/ONTIME/). Primary data documentation for a stronger JFK/LAX analysis. Gate times, wheels times and tail IDs support linked rotation work. Official documentation reviewed; no new BTS dataset was downloaded or analyzed here.

**[17] Sahadevan, D., Al Ali, H., Notman, D., & Mukandavire, Z. (2023).** *Optimising Airport Ground Resource Allocation for Multiple Aircraft Using Machine Learning-Based Arrival Time Prediction.* Aerospace, 10(6), 509. [DOI and open article](https://doi.org/10.3390/aerospace10060509). Supporting RQ3 reference linking arrival uncertainty and resource planning. Transfer the decision framework cautiously; its operational assumptions/data concern Dubai. Publisher abstract and methods reviewed. It is not evidence that BER resource capacities are known.

**[18] EUROCONTROL (2025).** *EUROCONTROL Specification for Airport Collaborative Decision Making (A-CDM).* Edition 1.0. [Official specification page](https://www.eurocontrol.int/publication/eurocontrol-specification-airport-collaborative-decision-making-cdm). Use together with the [2017 Implementation Manual, version 5.0](https://www.eurocontrol.int/publication/airport-collaborative-decision-making-cdm-implementation-manual) for timestamp and milestone semantics. Consult [BER's own glossary](https://corporate.berlin-airport.de/en/business-partners/airlines-handling/airport-cdm/faqs-glossar.html) for local interpretation. These explain concepts but do not independently document every raw API field.

## 8. Recommended first analysis for the paper

Start with a reproducible **data observability and departure performance analysis**: the dataset layers and provenance; actual versus estimated versus target timestamp mapping; daily coverage and missingness; target-to-actual interval distributions; contextual variation and flagged inconsistencies. Cite [1,14,18] for the method and interpretation. This is feasible now and supplies a defensible bridge from the Labs to the MSc.

Then build the independent calibration/evaluation comparison for observable departure behavior. Keep internal handling durations literature-based with sensitivity ranges until supported by additional measurements. Use JFK/BTS as a bounded secondary validation/rotation study, and Hansen-style external-delay experiments as an RQ3 extension after baseline behavior is established. The evidence does not justify attempting full turnaround calibration, JFK prediction, LAX queue replication and staffing optimization as four equally mature studies at once.

This review produced analysis and references only. No empirical causal effect, completed replication, optimized staffing plan or validated MSc simulation is claimed.
