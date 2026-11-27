"""Build a reviewable thesis update from archived study outputs, without changing them."""
from pathlib import Path
import shutil, json, re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/overleaf_update'
NEW=OUT/'updated';NEW.mkdir(exist_ok=True)
def put(name,text):
    (NEW/name).write_text(text.strip()+'\n',encoding='utf-8')

put('thesis_introduction.tex',r'''
\chapter{Introduction}
\label{ch:intro}

Aircraft turnaround is the period between an aircraft arriving at its parking position and leaving for its next flight. Ground teams unload baggage, clean and refuel the aircraft, and prepare it for boarding. Some activities proceed in parallel, whereas others require preceding work to finish. Flights also compete for shared stands, cleaning teams, fueling vehicles and pushback tugs. A delay in one service can therefore affect both its own turnaround and the resources available to other aircraft.

This thesis studies those interactions using an object-centric simulation informed by available Berlin Brandenburg Airport (BER) observations. It distinguishes observed input data, transferred literature assumptions and generated simulation events. The implemented study links finite arrival demand to persistent aircraft identities, exports object-centric event logs and compares service-time, policy and capacity scenarios. The results reported here describe the completed simulation pilot as of 13 November 2026; they do not constitute a validated digital twin of BER.

\section{Background}
Airport Collaborative Decision Making (A-CDM) supports the exchange of timely operational information between airport partners and the Network Manager, particularly around turnaround and pre-departure processes \cite{eurocontrol_acdm}. However, access to an A-CDM-related application does not imply access to every internal ground-service event. A boundary interval can contain several concurrent activities, waiting and parking. Its length alone does not reveal the duration of cleaning, fueling or boarding.

Object-centric event logs retain connections between events and multiple objects rather than imposing one case identifier on every event. OCEL 2.0 also supports qualified relationships and changes in object attributes \cite{ocel2}. These connections are useful for airport operations: one turnaround involves an aircraft and a stand, while reusable service resources may participate in many turnarounds.

The executable model is derived from the \emph{Airport Ground Handling (Extended)} example provided by the supervisor, Istv\'an Koren, in OCPN Studio \cite{ocpn_studio}. The inherited process topology and resource logic are explicitly attributed to that model. The student's contribution is the empirical demand adapter, traceable pairing and assumption management, literature-informed timing changes, event-log analysis and controlled comparison of scenarios.

\section{Motivation}
The motivation is to explain simulated waiting and readiness through interacting activities and resources. Adding capacity may remove a local queue without substantially changing the aircraft's final completion time. Conversely, a policy rule can create a long apparent service delay without a resource shortage. Distinguishing these mechanisms is necessary before drawing conclusions from a turnaround-time distribution.

The study also examines how much can be learned from incomplete operational observations. Available data support arrival demand and candidate aircraft characteristics, but do not identify all internal service durations. A useful model must expose this distinction rather than treat generated service events as additional empirical evidence.

\section{Problem statement}
The original research objective is to use A-CDM information to calibrate an object-centric turnaround simulation and investigate resource allocation. In the available collection, internal service start/end times and measured block times are absent. The implemented study therefore combines OpenSky boundary proxies with A-CDM reference records, and treats transferred service timings and unobserved operational context as explicit assumptions. Calibration is currently limited to evidence-supported input construction; no fitted predictive service-time model or completed empirical validation is claimed.

\section{Research questions}
The original research questions are retained:
\begin{description}
\item[RQ1:] How can A-CDM Data be used to calibrate activity durations and temporal dependencies in an OCPN Simulation?
\item[RQ2:] How do dependencies between aircraft, stands, and shared ground-service resources contribute to waiting times and delay propagation at terminal stands and remote stands in an OCPN simulation?
\item[RQ3:] How can the calibrated simulation be used to evaluate resource-allocation strategies and identify configurations that reduce turnaround delays and resource contention?
\end{description}

RQ1 is addressed by an observability audit and evidence-informed model inputs, with clear limits on activity-level calibration. RQ2 is investigated through shared-resource waiting, parallel-branch readiness and object-centric extraction. A controlled terminal-versus-remote stand comparison and a quantified inter-flight propagation analysis remain open. RQ3 is addressed by repeated conditional capacity experiments, without claiming optimal real BER staffing. Predictive accuracy evaluation is a methodological requirement across these questions, rather than a replacement definition of RQ2.

\section{Contributions and current scope}
The completed work provides a reproducible preparation pipeline for aircraft-linked interval candidates; daily executable OCPN derivatives; OCEL exports inspected in Promenade; and a 60-replication pilot separating timing assumptions, inherited policy and resource capacity. It also identifies important threats to validity: boundary proxies differ from block times, long stays require departure-scheduling logic, and inherited policy is evaluated on the wrong local-time basis. Chapters~\ref{ch:methods}--\ref{ch:discussion} document both the completed results and the work still required before operational conclusions.
''')

put('thesis_related.tex',r'''
\chapter{Related work and methodological basis}
\label{ch:related}

\section{Turnaround dependencies and service timing}
Schultz et al. describe stochastic turnaround processes and the role of the critical path in disturbance propagation \cite{schultz2012dynamic}. This supports representing concurrent ground services and their synchronization explicitly. It does not imply that a duration distribution fitted elsewhere transfers unchanged to BER.

This study transfers reference assumptions for narrowbody cleaning, fueling and boarding from that work. Their implementation is detailed in Chapter~\ref{ch:methods}. These are literature-informed scenario inputs, not estimates recovered from the Berlin boundary intervals. No universal low-cost versus full-service multiplier is inferred from those observations.

Schultz's later study develops and evaluates a calibrated stochastic passenger-boarding model \cite{schultz2018boarding}. It motivates treating boarding as an important and variable turnaround component. The present implementation uses a passenger-dependent mean reference; it does not reproduce that detailed stochastic boarding model or its empirical validation.

\section{A-CDM and available observations}
EUROCONTROL describes A-CDM as a collaboration and information-sharing approach involving airport operators, aircraft operators, ground handlers, air traffic control and the Network Manager \cite{eurocontrol_acdm}. This provides the operational context for milestone-based analysis. The current dataset's actual field coverage is a separate empirical question. In particular, A-CDM departure references do not provide internal service labels merely because the broader A-CDM concept includes turnaround coordination.

The OpenSky REST API documents aircraft identifiers, first/last observation timestamps and estimated airports for flight records \cite{opensky_rest}. These fields enable candidate pairing and boundary-proxy construction. They are not direct observations of stand arrival or departure. The thesis therefore reports discrepancies against an airborne-boundary proxy separately from simulated in-block to off-block duration.

\section{Object-centric simulation and analysis}
OCEL 2.0 represents events, objects, typed attributes and relationships \cite{ocel2}. In the study, the executable OCPN model generates the internal events and the exported OCEL preserves their object associations. Promenade is used for exploratory object-centric views and timing analysis \cite{promenade}. Those analyses describe generated behavior; they do not independently validate the assumptions that generated it.

OCPN Studio provides the modeling environment and the extended airport example \cite{ocpn_studio}. The official CPNsim runtime supports simulation of colored Petri nets \cite{cpnsim}. The study runs the installed version 0.6.2 through its WebAssembly interface. Software citations document the tools used and are distinct from empirical evidence about BER operations.

\section{Position of the present work}
The contribution lies in connecting a traceable empirical demand cohort to an existing object-centric model and making the resulting analyses auditable. It combines evidence separation, case-definition diagnostics, repeated timing/policy comparisons and resource sensitivity. It does not claim a replication of a particular LAX study, a JFK evaluation, a trained machine-learning duration predictor or empirical conformance checking: these have not been completed in the reported work.
''')

put('thesis_methods.tex',r'''
\chapter{Data and simulation methodology}
\label{ch:methods}

\section{Data provenance and cohort construction}
The prepared OpenSky movement table contains 22,635 records: 11,316 arrivals and 11,319 departures. Candidate BER ground intervals link an observed arrival to the following observed BER departure of the same ICAO24 identifier. The prepared core cohort contains 10,940 interval rows: 8,951 in the 15-minute to six-hour band and 1,989 in the six-to-24-hour band. Each row represents a candidate aircraft-linked interval, not a certified aircraft rotation.

The intended collection begins on 1 October 2026. The core file also includes 54 arrivals on 30 September paired to departures entering the requested period. Arrival observations in the file extend through 9 November. Accordingly, this version does not claim complete data coverage through 13 November. Temporal coverage, API availability and filtering must be distinguished from the number of interval rows retained.

The proxy is defined as
\begin{equation}
G_i^{\mathrm{proxy}}=t_{i,\mathrm{outbound\ firstSeen}}-t_{i,\mathrm{inbound\ lastSeen}}.
\end{equation}
Both timestamps are observation boundaries, as described by the OpenSky API \cite{opensky_rest}. The interval may include unobserved approach/taxi segments, parking and timetable buffers. It is not measured actual in-block time (AIBT) to actual off-block time (AOBT). Source identifiers, pairing basis, review flags and timezone-aware UTC/Berlin representations are retained.

A-CDM reference records provide candidate aircraft/airline/stand context and departure-time cross-checks where a candidate match exists. Their naive timestamps are retained alongside the UTC timezone hypothesis used during reconciliation. They are references rather than complete service-event ground truth. Credentials and API secrets are not included in the thesis or its analysis artifacts.

\section{Daily experimental inputs}
The daily models use 271 cases and 235 distinct aircraft on 1 November, and 238 cases and 212 aircraft on 8 November. Supported candidate aircraft types exist for 216 and 180 input rows, respectively. This row-level coverage does not mean every final aircraft configuration is observed: the first case establishes a persistent model configuration, and missing or unsupported types fall back to an assumed A320 configuration. Later conflicting candidates have not been reconciled.

The two cohorts include 39 and 44 intervals longer than six hours. These long stays are not automatically equivalent to active ground handling. Matched-core demand also excludes unmatched and other discarded movements, so the simulated resource competition is conditional on this cohort rather than a complete representation of airport traffic.

\section{Baseline attribution and study modifications}
The supervisor's original extended model is preserved unchanged. Its six parallel handling threads, resource interaction logic, vehicle positions, fuel supply mechanisms and process dependencies are inherited contributions. A same-demand original-timing comparator retains the original service functions within the adapted demand model; it is not the untouched example.

The study replaces indefinite synthetic generation with finite timed demand. Inbound availability is released using the observed arrival boundary proxy. A persistent aircraft identity is required for the paired rotation and returned after simulated takeoff. Subsequent cases cannot use the same aircraft while it remains in the model. Synthetic outstation travel and the inherited inbound curfew/extra approach delay are bypassed; landing roll, runway contention and taxi-in remain simulated. Observed outbound times are retained outside the model as evaluation references and do not force simulated departures.

Schengen stand segregation is disabled because route context is incomplete; physical size compatibility remains. Departure-planning steps are labeled as assumptions rather than observed TOBT/TSAT values. Simulated weather, remaining durations and illustrative geometry are retained as assumptions.

\section{Service-time assumptions}
For narrowbody aircraft, the transferred reference functions, in minutes, are \cite{schultz2012dynamic}:
\begin{align}
D_{\mathrm{clean}} &=5+\mathrm{Weibull}(\mathrm{shape}=2.16,\mathrm{scale}=6.76),\\
D_{\mathrm{fuel}} &=2+\mathrm{Gamma}(\mathrm{shape}=1.64,\mathrm{scale}=9.12),\\
D_{\mathrm{board}} &=2.3+0.075P,
\end{align}
where $P$ is the assumed passenger count. Boarding uses a deterministic mean reference, not a full distribution. Vehicle travel/access time is additional where specified by the inherited model. The engine functions take scale before shape; their calls are \texttt{weibull(6.76,2.16)} and \texttt{gamma(9.12,1.64)} before converting minutes to milliseconds. Other aircraft-size categories retain inherited timing functions.

Passenger counts are assumed at 85\% of scenario seating capacity, PRM demand is zero, and sector duration is 120 minutes. Carrier class remains unknown. No measured passenger load or justified budget/full-service timing coefficient is available. The original timing comparator's unknown-carrier branch also needs to be considered when interpreting the comparison.

The inherited 25-stand geometry, runway dimensions, resource capacities, taxi assumptions and optional-service probabilities are not verified BER infrastructure. Models begin each daily run with free stands and resources, without calibrated overnight occupancy or a warm-up history. These choices restrict interpretation of queues and resource experiments.

\section{OCEL export and Promenade procedure}
Exports use Studio's object decomposition and relationship logic, then normalize primitive CPN types to OCEL types. Integrity checks cover identifier uniqueness, case coverage, typed values and non-dangling event--object/object--object links. These custom checks are not an official OCEL JSON-schema validation or empirical process conformance test.

Three completed pilot logs were imported into Promenade: 1 November literature timings (10,288 events, 1,247 objects), 8 November literature timings (9,046 events, 1,123 objects), and the 1 November original-timing comparator (10,298 events, 1,255 objects). Views include Overview, Cases and variants, Turnaround-restricted Performance Spectrum and Object Dynamics/Activity Timing. In-block/off-block statistics use next-after one-to-one pairs within the same Turnaround object and were checked independently against exported events.

These three logs precede the controlled experiment below. The 60 later replications were analyzed headlessly; they have not all been imported into Promenade. The all-core model containing 10,940 cases was load-tested but not fully executed, so no full-period simulation log is claimed.

\section{Controlled experiment}
Six scenarios are run on each date, with five independent replications per cell: 60 runs across 12 date/scenario cells. Four scenarios cross literature/original timing with inherited/disabled curfew. Two further scenarios use literature timings and disabled curfew, reducing cleaning teams from nine to six or increasing fuel units from four hydrants plus four tankers to six plus six. Demand and remaining assumptions are held fixed within each date.

The design was fixed before these runs, informed by the earlier pilot. It was not independently preregistered. The installed WebAssembly API does not expose seed control; replications use fresh runtime randomness and comparisons are unpaired. All 15,270 turnaround executions reuse 509 empirical cases across scenarios and replications. They are not 15,270 independent observed flights.

For a metric $m$, the statistical unit is the replication-level mean $\bar m_r$. Scenario means and Student-$t$ 95\% intervals are computed over five such means. Differences use independent-run Welch 95\% intervals. No multiplicity correction is applied; comparisons are exploratory. These intervals quantify simulation sampling variation conditional on fixed inputs, not uncertainty in load factors, capacities, transferred distributions or model structure.

\section{Metrics and verification}
Simulated block turnaround is pushback start/off-block minus in-block. Fuel waiting is handling start to fuel dispatch, excluding subsequent travel; cleaning waiting is deplaning completion to cleaning start; tug waiting is aircraft-ready to tug allocation. These definitions are retained when comparing scenarios.

For each turnaround, the six handling branches are compared using output-token availability times at the synchronization join, including post-transition arc delays. The last-ready branch identifies a synchronization constraint in that realization; frequency alone is not a causal bottleneck test. Resource-count interventions provide an additional sensitivity check.

Technical verification requires all expected cases to depart, the timed-demand queue to be empty, aircraft to return to their availability pool, relevant resources to return and metrics to be finite/nonnegative. All 60 runs pass these checks, including model-hash and unique-case coverage audits. Technical completion does not establish predictive accuracy.
''')

put('thesis_results.tex',r'''
\chapter{Analysis and results}
\label{ch:results}

\section{Exploratory Promenade results}
The three original daily/comparator logs provide the descriptive results in Table~\ref{tab:promenade}. These are individual stochastic runs, separate from the five-replication means reported later.
\begin{table}[htbp]\centering\small
\begin{tabular}{lrrr}\hline
Metric (minutes) & Nov. 1 literature & Nov. 8 literature & Nov. 1 original\\\hline
Cases & 271 & 238 & 271\\
Mean block duration & 62.33 & 59.59 & 84.95\\
Median & 55.62 & 57.34 & 64.37\\
90th percentile & 72.48 & 72.83 & 80.12\\
Maximum & 434.83 & 116.70 & 421.95\\\hline
\end{tabular}
\caption{Paired simulated in-block/off-block durations checked in Promenade. Original denotes original service functions inside the same demand adapter.}\label{tab:promenade}
\end{table}

Every paired analysis has zero unmatched starts. Differences establish sensitivity to timing assumptions, not empirical improvement. In particular, inherited policy affects the long tail. Figure~\ref{fig:promenade} preserves an actual Promenade timing view.
\begin{figure}[htbp]\centering
\includegraphics[width=\textwidth]{study_promenade_timing.jpg}
\caption{Promenade Object Dynamics/Activity Timing view of the 1 November literature-timing log. The data are generated simulation events.}\label{fig:promenade}
\end{figure}

\section{Resource queues and handling dependencies}
In the individual literature-timing runs, mean fuel-dispatch waiting is 3.785 minutes on 1 November and 1.255 minutes on 8 November. Cleaning-team waiting is 0.018 and approximately zero minutes; tug-allocation waiting is 0.033 and approximately zero. The 1 November 90th-percentile fuel waiting time is 14.20 minutes, with a maximum of 38.28 minutes.

Nevertheless, the cabin/boarding branch is last ready in 230 of 271 turnarounds (84.9\%) and 192 of 238 (80.7\%). Fuel is last in only 21 and 10 cases; baggage handling is last in 20 and 36. Thus the largest local queue is not automatically the branch governing final readiness. Fuel waiting can overlap continuing cabin work. These counts describe synchronization outcomes, not a proof of causal dominance.
\begin{figure}[htbp]\centering
\includegraphics[width=\textwidth]{study_last_ready.png}
\caption{Last-ready handling branch in the original three simulation logs, calculated from output-token availability at the join. This supplementary Python figure uses exported events; it is not a Promenade-generated chart.}\label{fig:lastready}
\end{figure}

These observations partially address RQ2 by exposing parallel dependencies and resource contention within the simulation. They do not establish real terminal-versus-remote stand differences or quantify empirical inter-flight delay propagation. Workload counts per shared resource must also not be called time utilization without occupancy-duration calculations.

\section{Case-definition diagnostic}
The 1 November Promenade overview has two connected object components, with 94\% of objects in the largest. Reusable resources connect many rotations; a connected-component case definition would therefore merge most of the day. A leading Turnaround extraction returns 271 executions and 271 variants at the selected settings, but expanded executions can include shared-resource events. One expanded execution displays approximately 16.7 hours, which is not that turnaround's paired block duration. The analysis therefore uses direct paired milestones for duration statistics. A SQL-discovered object-centric directly-follows graph was produced; the separate metro-map layout was canceled after stalling and is not a completed result.

\section{Observed proxy discrepancies}
The first 1 November literature run has a simulated planned-arrival-to-takeoff proxy median of 79.63 minutes, close to the observed boundary-proxy median of 79.12. However, their means are 85.63 versus 156.17 minutes, with mean bias $-70.55$ minutes and mean absolute discrepancy 92.09 minutes. On 8 November, mean bias is $-101.60$ minutes and mean absolute discrepancy 116.00 minutes.
\begin{figure}[htbp]\centering
\includegraphics[width=\textwidth]{study_proxy_comparison.png}
\caption{Exploratory comparison with observed boundary proxies for the initial logs. These are not errors against measured AIBT--AOBT. Long stays and differing timestamp semantics limit interpretation.}\label{fig:proxy}
\end{figure}

A close median therefore conceals a poor distributional match. The current simulator starts handling after arrival and departs when ready, while observations can include parking and schedule buffers. Service durations should not be inflated merely to absorb that mismatch. Pairing review, stay stratification and independently justified departure scheduling are required before accuracy claims.

\section{Repeated timing and policy comparisons}
All 60 controlled runs complete and pass integrity checks. Table~\ref{tab:controlled} gives the mean of five replication means per date/scenario. Figure~\ref{fig:timing} shows the individual run means and intervals.
\begin{table}[htbp]\centering\small
\begin{tabular}{lrr}\hline
Scenario & Nov. 1 mean [95\% CI] & Nov. 8 mean [95\% CI]\\\hline
Original, inherited policy & 86.91 [84.83,89.00] & 72.73 [69.30,76.17]\\
Literature, inherited policy & 61.91 [59.82,64.01] & 59.22 [58.91,59.52]\\
Original, disabled curfew & 66.73 [66.14,67.32] & 66.07 [65.78,66.37]\\
Literature, disabled curfew & 59.20 [58.59,59.81] & 59.03 [58.45,59.61]\\
Six cleaning teams, disabled & 59.26 [58.39,60.13] & 59.20 [58.33,60.06]\\
Six+six fuel units, disabled & 58.58 [58.34,58.81] & 58.81 [58.56,59.06]\\\hline
\end{tabular}
\caption{Mean simulated block duration in minutes. Resource variants use literature timings; the reference has nine cleaning teams and four+four fuel units. Intervals quantify between-run simulation variability only.}\label{tab:controlled}
\end{table}
\begin{figure}[htbp]\centering
\includegraphics[width=\textwidth]{study_timing_policy.png}
\caption{Timing/policy comparisons: five independent run means per scenario, with Student-$t$ 95\% intervals. Disabled curfew is a diagnostic assumption sensitivity.}\label{fig:timing}
\end{figure}

With curfew disabled, literature-minus-original timing differences are $-7.53$ minutes on 1 November (Welch 95\% CI $[-8.24,-6.82]$) and $-7.04$ on 8 November ($[-7.62,-6.47]$). Under inherited policy the differences increase to $-25.00$ ($[-27.45,-22.54]$) and $-13.52$ ($[-16.94,-10.09]$). The apparent timing benefit therefore interacts strongly with policy logic; it is not evidence that transferred timings are more accurate.

An additional exploratory interaction contrast, added while inspecting the pilot, subtracts the disabled-curfew timing difference from the inherited-policy timing difference. Estimates are $-17.46$ minutes ($[-19.96,-14.97]$) and $-6.48$ ($[-9.88,-3.08]$). This is a conditional model finding, not a preregistered confirmatory result or a causal statement about airport regulations.

\section{Repeated resource sensitivity}
Under literature timings and disabled curfew, increasing fueling capacity from eight to twelve units reduces mean dispatch waiting from 3.042 to 0.168 minutes on 1 November and from 2.040 to 0.066 on 8 November. Final block-duration differences are much smaller: $-0.62$ minutes (95\% CI $[-1.23,-0.02]$) and $-0.22$ ($[-0.79,0.35]$). The latter interval crosses zero. A substantial queue reduction therefore does not establish a consistently substantial overall turnaround improvement.
\begin{figure}[htbp]\centering
\includegraphics[width=\textwidth]{study_resource_sensitivity.png}
\caption{Resource sensitivity: overall turnaround and fuel-dispatch waiting respond differently. Counts are assumed model capacities, not verified BER staffing.}\label{fig:resource}
\end{figure}

Reducing cleaning teams from nine to six produces estimated block-duration increases of 0.07 minutes ($[-0.84,0.97]$) and 0.17 ($[-0.72,1.05]$). Neither comparison resolves a direction in this pilot. This is not a demonstration of equivalence or non-inferiority and does not justify a staffing reduction.
\begin{figure}[htbp]\centering
\includegraphics[width=\textwidth]{study_contrasts.png}
\caption{Exploratory independent-run Welch 95\% intervals for block-duration differences with curfew disabled. No multiplicity adjustment is applied.}\label{fig:contrasts}
\end{figure}

For RQ3, these scenarios demonstrate a functioning evaluation method and conditional trade-offs. They do not establish a cost-optimal configuration, compare alternative dispatch priorities, or optimize real BER resource allocation.
''')

put('thesis_discussion.tex',r'''
\chapter{Discussion and threats to validity}
\label{ch:discussion}

\section{Answers supported by the current evidence}
\subsection{RQ1: data-informed calibration}
The available observations support finite arrival demand, candidate aircraft pairing and selected contextual checks. They do not identify cleaning, fueling or boarding durations: multiple services and waiting can occur within one observed boundary interval. Transferred distributions and explicit assumptions make an executable model possible, but must not be described as fitted BER service-time estimates. Additional service start/end observations, passenger counts and reliable block timestamps would strengthen activity-level calibration.

\subsection{RQ2: dependencies, queues and propagation}
Object-linked logs show how shared resource availability and parallel branches contribute to simulated waiting and readiness. Fuel dispatch has the clearest local queue in the initial runs, yet cabin/boarding is usually the final handling branch. The capacity intervention supports the interpretation that removing fuel waiting can have limited effect on final completion because work overlaps.

This is a partial answer. Persistent aircraft and reusable resources permit contention in the model, but the current experiments do not quantify how an exogenous delay propagates across flights. Nor do they provide a controlled terminal-versus-remote comparison: stand context and bus/access assumptions are not empirically calibrated. Such claims require stratified metrics and interventions with consistent definitions of stand type, demand and resource state.

\subsection{RQ3: conditional resource evaluation}
Repeated capacity comparisons demonstrate how to evaluate local queues alongside overall turnaround and uncertainty. The findings favor reporting both levels rather than selecting a configuration using queue length alone. However, only two capacity alternatives were tested, with assumed resources and no cost objective. The current evidence cannot establish an optimal resource configuration or real staffing recommendation.

\section{Policy and clock semantics}
BER's official guidance describes a core night-flight restriction from 00:00 to 05:00 and constraints in the adjacent 23:00--24:00 and 05:00--06:00 windows \cite{ber_night}. The inherited model instead applies its helper before pre-boarding and pushback clearance. Those applications do not constitute a complete operational movement-eligibility model.

The installed CPNsim runtime was probed at epoch \texttt{2026-11-01T00:00:00Z}: its hour helper returns zero, while Berlin local hour is one. Engine source also uses UTC \cite{cpnsim}. Thus the inherited 00:00--05:00 condition corresponds to 01:00--06:00 local time on both study dates. This mismatch is confirmed, rather than a possible explanation inferred solely from plotted tails.

The controlled experiment deliberately retains the inherited implementation in its policy cells and disables the entire helper in the diagnostic cells. Neither is presented as a verified BER replacement. A subsequent version must use Europe/Berlin time, including daylight-saving changes across the full collection, and distinguish movement restrictions, shoulder windows, exceptions and independent cabin work. The present analysis does not make a legal-compliance determination.

\section{Data and construct validity}
ICAO24 adjacency provides candidate rotations rather than certified ground movements. Missing flights, airport-estimation errors or identifier issues may affect pairing. OpenSky observation boundaries and simulated block milestones are different constructs. A-CDM reference matches and a timezone hypothesis do not remove these differences. The observed-proxy discrepancies should therefore be reported without calling them block-time prediction errors.

Long stays, planned departure buffers and overnight parking are not modeled. The selected cohort also omits competing traffic, and every daily run begins with free resources. These choices can materially alter queues. Fictitious geometry, passenger load, PRM demand, carrier class, optional services and non-narrowbody functions further restrict transfer to real BER operations.

\section{Statistical and analytical validity}
Five replications per cell provide pilot uncertainty conditional on a fixed model. They do not propagate input or structural uncertainty. Runs are unpaired, random seeds are unavailable, and exact stochastic reruns cannot be promised. Multiple exploratory contrasts are reported without correction. Intervals crossing zero do not prove no effect, and a barely excluding interval is not strong operational evidence.

The timing comparison changes three services together; it cannot assign the result to cleaning, fueling or boarding separately, or distinguish changes in mean from variability. November 8 is a later-date scenario with no outcome-based tuning in this pilot, but is not a completed held-out predictive validation. Formal empirical conformance, contact/remote stratification, resource time utilization, cost analysis and external replication remain incomplete.

Promenade extraction scope is another source of analytical error. Shared resources connect rotations, and expanded executions can contain events outside the focal block interval. The chosen one-to-one milestone pairs and explicit metric definitions avoid treating such expanded durations as aircraft turnaround observations.

\section{Remaining work before stronger conclusions}
The next model version should correct local-time movement policy, resolve aircraft-type candidates and distinguish operational turnarounds from long stays. Evaluation should then use independently selected dates and matching observable quantities, without forcing observed departures. RQ2 additionally requires terminal/remote stratification and controlled delay-propagation experiments. RQ3 needs broader input/capacity sensitivity and a declared operational or cost objective. These tasks should precede claims of validated calibration or optimal allocation.
''')

put('thesis_conclusion.tex',r'''
\chapter{Conclusion}
\label{ch:conclusion}
The completed study connects a prepared BER aircraft-interval cohort to an existing object-centric airport simulation, exports interpretable logs and evaluates controlled timing, policy and resource scenarios. Attribution separates the supervisor's original process model from the student's empirical adapter, timing changes, provenance controls and analyses.

The 60-replication pilot completes 15,270 simulated turnaround executions based on 509 reused observed interval candidates. Literature timing assumptions shorten mean simulated block duration by approximately seven minutes when the inherited curfew helper is disabled. Much larger differences under inherited policy expose sensitivity to policy logic. Increasing fueling capacity removes most dispatch waiting but produces a much smaller overall turnaround change, consistent with overlap among parallel handling branches.

These findings provide partial answers to RQ1--RQ3. Available data inform demand and selected context, while unobserved services remain assumptions. Object-centric analysis exposes dependencies and extraction pitfalls, while stand-specific and inter-flight propagation comparisons remain open. Repeated capacity scenarios support conditional evaluation, not an optimal actual BER staffing plan.

The main practical requirement is to preserve the distinction between observation, assumption and generated behavior. Further work must correct the local-time movement policy, represent long stays and evaluate matching observable quantities on separate dates. This draft records the completed pilot and its limitations; it does not claim that the full empirical validation or thesis project is finished.
''')

put('thesis_reproducibility.tex',r'''
\chapter{Reproducibility and artifact inventory}
\label{app:repro}
The original model is retained as \texttt{airport-extended.ocpn}; its SHA-256 is
\begin{quote}\footnotesize\texttt{b83e78fbdaa2289c406e359cffc080935b}\\
\texttt{d3ba586bae2f6a1858c77fa8f379d2}.\end{quote}
The two displayed lines form one continuous hash. The source attribution and MIT license accompanying the Studio-derived material are retained with the model package.

The prepared core input is \texttt{ber\_ground\_intervals\_core\_proxy.csv}. Daily case CSVs and manifests retain source keys and model assumptions. Version 2.0 daily OCEL exports and Promenade analysis are separate from version 2.1 controlled replications.

The controlled-study archive contains twelve built models, case CSVs/manifests, a frozen experiment plan, sixty per-case result files and corresponding summaries, replication metrics, scenario summaries, contrasts, validation results and three figures. Scripts implement model building, official-runtime execution and replication-level aggregation. Python dependencies are NumPy, pandas, SciPy and Matplotlib. Node.js and \texttt{@rwth-pads/cpnsim} 0.6.2 provide simulation execution. The runtime and full upstream raw collection are not bundled in that archive; absolute plan paths require adjustment after relocation.

The Promenade folder contains actual application captures/exports and supplementary Python figures, identified separately in captions. It also contains paired case metrics and analysis notes. The controlled replications are headless results, not sixty additional completed Promenade imports.

All reported controlled runs passed completion, case uniqueness, aircraft/resource-return and model-hash checks. These are technical integrity checks, distinct from official OCEL schema validation, process conformance or empirical accuracy. The 10,940-case model is load-tested only. Random-seed control is unavailable, so repeating the procedure will produce new stochastic outputs.
''')

put('study_references.bib',r'''
@inproceedings{schultz2012dynamic,
 author={Schultz, Michael and Kunze, Thomas and Oreschko, Bernd and Fricke, Hartmut},
 title={Dynamic Turnaround Management in a Highly Automated Airport Environment},
 booktitle={28th International Congress of the Aeronautical Sciences},year={2012},
 url={https://www.icas.org/icas_archive/ICAS2012/PAPERS/808.PDF},urldate={2026-11-13}}
@article{schultz2018boarding,
 author={Schultz, Michael},title={Fast Aircraft Turnaround Enabled by Reliable Passenger Boarding},
 journal={Aerospace},year={2018},volume={5},number={1},eid={8},doi={10.3390/aerospace5010008}}
@online{eurocontrol_acdm,author={{EUROCONTROL}},title={Airport collaborative decision-making},
 url={https://www.eurocontrol.int/concept/airport-collaborative-decision-making},urldate={2026-11-13}}
@online{opensky_rest,author={{The OpenSky Network}},title={OpenSky REST API},
 url={https://openskynetwork.github.io/opensky-api/rest.html},urldate={2026-11-13}}
@online{ocel2,author={{Chair of Process and Data Science, RWTH Aachen University}},title={Object-Centric Event Log 2.0},
 url={https://www.ocel-standard.org/},urldate={2026-11-13}}
@online{ocpn_studio,author={{ELTE DSED}},title={OCPN Studio},
 url={https://elte-dsed.github.io/ocpn-studio/},urldate={2026-11-13},note={Airport Ground Handling (Extended) baseline supplied by Istv\'an Koren; study derivative attributed separately}}
@online{cpnsim,author={{RWTH PADS}},title={CPNsim: Colored Petri Net simulation runtime},
 url={https://github.com/rwth-pads/cpnsim},urldate={2026-11-13},note={Study execution uses installed version 0.6.2}}
@online{promenade,author={{Promenade}},title={Promenade Lab},
 url={https://app.promenade.run/},urldate={2026-11-13},note={Object-centric analysis application used in the study}}
@online{ber_night,author={{Flughafen Berlin Brandenburg GmbH}},title={Hinweise zum Nachtflug},
 url={https://corporate.berlin-airport.de/de/nachhaltigkeit/umwelt/fluglaerm/hinweise-zum-nachtflug.html},urldate={2026-11-13}}
''')

assets={
 'study_timing_policy.png':'output/controlled_study_v21/01_timing_policy_replications.png',
 'study_resource_sensitivity.png':'output/controlled_study_v21/02_resource_sensitivity_replications.png',
 'study_contrasts.png':'output/controlled_study_v21/03_controlled_contrasts.png',
 'study_last_ready.png':'promenade/06b_last_ready_handling_branch.png',
 'study_proxy_comparison.png':'promenade/04_observed_proxy_vs_simulation.png',
 'study_promenade_timing.jpg':'promenade/10_promenade_nov1_block_turnaround.jpg'}
for name,src in assets.items():shutil.copy2(ROOT/src,NEW/name)

original=(OUT/'before/elteikthesis_en.tex').read_text(encoding='utf-8')
preamble=original.split(r'\begin{document}')[0]
preamble=preamble.replace(r'\addbibresource{elteikthesis.bib}',r'\addbibresource{study_references.bib}')
body=r'''
\begin{document}
\documentlang{english}
\maketitle
\chapter*{Abstract}
\addcontentsline{toc}{chapter}{Abstract}
This thesis investigates data-informed object-centric simulation of airport turnaround using a prepared Berlin Brandenburg aircraft-interval cohort and an existing OCPN airport model. Available observations inform demand and candidate aircraft context, while literature assumptions describe unobserved services. Object-centric logs inspected in Promenade expose shared-resource queues, parallel completion constraints and case-extraction pitfalls. A controlled pilot runs six scenarios on each of two dates with five replications per cell. All sixty runs complete, yielding 15,270 simulated executions based on 509 reused empirical interval cases. With inherited curfew disabled, literature timing assumptions reduce mean simulated block duration by 7.53 and 7.04 minutes compared with original timing functions. Increasing fueling capacity greatly reduces local waiting but changes overall turnaround by only 0.62 and 0.22 minutes. Inherited policy materially amplifies apparent timing effects and contains a confirmed UTC/local-time mismatch. Findings support conditional sensitivity analysis rather than validated BER service-time prediction or optimal staffing. Long stays, incomplete traffic, assumed passenger demand and missing ground-service observations remain limitations. This draft documents completed work and explicitly identifies unfinished empirical evaluation.
\cleardoublepage
\tableofcontents
\cleardoublepage
\input{thesis_introduction.tex}
\cleardoublepage
\input{thesis_related.tex}
\cleardoublepage
\input{thesis_methods.tex}
\cleardoublepage
\input{thesis_results.tex}
\cleardoublepage
\input{thesis_discussion.tex}
\cleardoublepage
\input{thesis_conclusion.tex}
\cleardoublepage
\chapter*{\acklabel}
\addcontentsline{toc}{chapter}{\acklabel}
I thank my supervisor, Istv\'an Koren, for providing the original extended airport model and guiding the research direction. The distinction between that baseline and the study modifications is maintained throughout this thesis.
\cleardoublepage
\appendix
\input{thesis_reproducibility.tex}
\cleardoublepage
\phantomsection
\addcontentsline{toc}{chapter}{\biblabel}
\printbibliography[title=\biblabel]
\cleardoublepage
\listoffigures
\cleardoublepage
\listoftables
\end{document}
'''
put('elteikthesis_en.tex',preamble+body)

# Static cross-reference/file audit before upload. Compilation is checked in Overleaf.
alltex='\n'.join(p.read_text(encoding='utf-8') for p in NEW.glob('*.tex'))
bib=(NEW/'study_references.bib').read_text(encoding='utf-8')
cites=set(re.findall(r'\\cite\{([^}]+)\}',alltex))
for key in cites:assert re.search(r'@\w+\{'+re.escape(key)+',',bib),key
for name in re.findall(r'\\(?:input|includegraphics)(?:\[[^]]*\])?\{([^}]+)\}',alltex):assert (NEW/name).exists(),name
(OUT/'update_manifest.json').write_text(json.dumps({'project':'https://www.overleaf.com/project/6af77dc2e99d9136baa233fc','files':[p.name for p in NEW.iterdir()],'citation_keys':sorted(cites),'scope':'Current-work draft; empirical validation remains incomplete','rq2':'Preserved original dependency/propagation question; accuracy is not substituted for RQ2'},indent=2))
print('Prepared',len(list(NEW.iterdir())),'files; citations and included files checked.')
