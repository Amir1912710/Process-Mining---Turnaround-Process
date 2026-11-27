"""Revise the current thesis in clear academic English, with an attributed related thesis."""
from pathlib import Path
import shutil,re,json,hashlib

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/overleaf_update'
SRC=BASE/'updated'
BACKUP=BASE/'before_language_revision'
if not BACKUP.exists():shutil.copytree(SRC,BACKUP)
DEST=BASE/'language_revision';DEST.mkdir(exist_ok=True)
for p in BACKUP.iterdir():
    if p.is_file():shutil.copy2(p,DEST/p.name)

def put(name,text):
    (DEST/name).write_text(text.strip()+'\n',encoding='utf-8')

put('thesis_introduction.tex',r'''
\chapter{Introduction}
\label{ch:intro}

Aircraft turnaround is the period between an aircraft's arrival at a parking position and its departure for the next flight. During this period, several teams prepare the aircraft by unloading baggage, cleaning the cabin, refueling and boarding passengers. These activities follow different dependencies. Some can take place at the same time, while others can start only after preceding work has finished. Aircraft also share stands, service vehicles and ground teams. As a result, the availability of one resource can affect several turnarounds.

Understanding these interactions requires information about both the activities and the resources involved. However, the available operational records do not describe every ground service. They mainly provide information about flight movements and selected departure milestones. This creates a gap between the process we want to study and the behavior we can directly observe.

This thesis investigates how an object-centric simulation can support turnaround analysis under these conditions. We adapt an existing airport model using prepared observations from Berlin Brandenburg Airport (BER), document the assumptions used for missing information and analyze the generated event logs. We then compare service-time assumptions, policy rules and resource capacities through repeated simulation. The reported results concern the completed pilot study. Further empirical evaluation is required before the model can support conclusions about actual BER performance.

\section{Background}
Airport Collaborative Decision Making (A-CDM) supports information exchange among airport partners and the Network Manager, with particular attention to turnaround and pre-departure processes \cite{eurocontrol_acdm}. This information helps partners coordinate their activities. Nevertheless, an A-CDM-related application does not necessarily provide the start and end times of every ground service. A time interval between two milestones may contain several activities, waiting and parking. Its total duration is therefore insufficient to determine how long each internal activity took.

Object-centric event logs provide a way to retain the relationships between these activities and the objects involved. An event can be linked to a turnaround, an aircraft and a service resource. OCEL 2.0 supports these relationships, their qualifiers and changes in object attributes \cite{ocel2}. This is useful when a cleaning team or a fueling vehicle serves several aircraft during the same day.

The simulation used in this thesis is based on the \emph{Airport Ground Handling (Extended)} model provided by the supervisor, Istv\'an Koren, in OCPN Studio \cite{ocpn_studio}. Its original process structure and resource logic are retained as attributed prior work. Our modifications concern the empirical demand, aircraft pairing, selected activity timings, analysis procedures and controlled experiments.

\section{Motivation}
A departure time alone does not explain why an aircraft was ready late. The aircraft may have been waiting for a resource, receiving a service or waiting for another parallel activity to finish. These explanations require different operational responses. For example, increasing the number of fueling units can reduce the fuel queue without substantially shortening turnaround if boarding is still in progress.

Simulation allows us to examine these relationships under defined conditions. It also allows assumptions to be changed individually while keeping other inputs fixed. However, the resulting events remain synthetic. Their detail must not be mistaken for additional observations of real ground handling. The motivation of this study is therefore twofold: to investigate dependencies within the model and to make clear which conclusions the available evidence supports.

\section{Problem Statement}
The research objective is to use A-CDM information to support the calibration of an object-centric turnaround simulation and the evaluation of resource allocation. The collected data do not contain reliable internal service start/end times or measured block times. The implemented study therefore combines OpenSky flight-boundary observations with A-CDM reference records. Literature and explicitly stated assumptions supply the missing service inputs.

The problem is to construct an executable and traceable model from these sources without treating assumed durations as measured values. A second challenge is to interpret its outputs correctly. Changes in simulated turnaround may result from service timing, resource availability or policy logic. These effects must be examined separately before drawing conclusions about calibration or allocation.

\section{Research Questions}
The following research questions guide the study:
\begin{description}
\item[RQ1:] How can A-CDM Data be used to calibrate activity durations and temporal dependencies in an OCPN Simulation?
\item[RQ2:] How do dependencies between aircraft, stands, and shared ground-service resources contribute to waiting times and delay propagation at terminal stands and remote stands in an OCPN simulation?
\item[RQ3:] How can the calibrated simulation be used to evaluate resource-allocation strategies and identify configurations that reduce turnaround delays and resource contention?
\end{description}

The current work addresses these questions to different extents. For RQ1, we examine which model inputs can be supported by the collected data. For RQ2, we analyze resource waiting and the synchronization of parallel activities. A controlled comparison of terminal and remote stands, and a quantified analysis of delay propagation between flights, remain open. For RQ3, we evaluate selected capacity changes under fixed assumptions. Predictive accuracy is relevant to the evaluation of the model as a whole; it does not replace the dependency-focused meaning of RQ2.

\section{Research Goals and Contributions}
The study aims to prepare aircraft-linked input records, adapt the existing model, export analyzable object-centric logs and compare selected scenarios. The completed contributions are:
\begin{enumerate}
\item A preparation procedure that retains source references, candidate aircraft pairings and the meaning of each timestamp.
\item Daily OCPN models with finite empirical demand and persistent aircraft identities, with observed inputs separated from assumptions.
\item An analysis of the exported logs in Promenade, including resource queues, parallel completion and the effect of case definitions.
\item A controlled pilot of 60 simulation runs examining service timing, inherited policy and resource capacity.
\end{enumerate}

These contributions extend the use and evaluation of the supplied model. They do not include the development of its original six-thread process structure. Nor do they establish a validated BER digital twin or an optimal staffing plan.

\section{Thesis Structure}
Chapter~\ref{ch:related} reviews the methodological background and related work. Chapter~\ref{ch:methods} describes the data, model changes and experimental procedure. Chapter~\ref{ch:results} presents the Promenade analysis and repeated simulation results. Chapter~\ref{ch:discussion} relates the findings to the research questions and discusses their limitations. Finally, Chapter~\ref{ch:conclusion} summarizes the work and identifies the next evaluation steps.
''')

put('thesis_related.tex',r'''
\chapter{Related Work and Methodological Background}
\label{ch:related}

This chapter introduces the work used to guide the study. We first consider turnaround timing and the available operational observations. We then discuss object-centric simulation and a closely related trace-reconstruction thesis. The final section explains the position of the present work.

\section{Turnaround Dependencies and Activity Timing}
Schultz et al. describe stochastic turnaround processes and discuss how disturbances on a critical path can affect later operations \cite{schultz2012dynamic}. Their work supports a model in which concurrent services must synchronize before the aircraft can proceed. It also provides reference assumptions used here for narrowbody cleaning, fueling and boarding.

Transferring a reference distribution does not establish that it describes BER operations. In this study, the distributions are used as stated model inputs. We do not estimate them from the Berlin boundary intervals or derive a universal timing difference between low-cost and full-service airlines.

Schultz later presents a calibrated stochastic boarding model and evaluates boarding scenarios \cite{schultz2018boarding}. This work shows the importance of considering passenger boarding in turnaround analysis. Our implementation uses a passenger-dependent mean reference, rather than reproducing that detailed stochastic model or its validation.

\section{Operational Observations and the Data Gap}
EUROCONTROL describes A-CDM as an approach for sharing operational information among airport operators, aircraft operators, ground handlers, air traffic control and the Network Manager \cite{eurocontrol_acdm}. This provides the operational context for milestone analysis. Whether a particular collection contains enough detail for activity-level calibration must still be checked separately.

The OpenSky REST API provides aircraft identifiers, first and last observation timestamps, and estimated airports for flight records \cite{opensky_rest}. These fields support candidate aircraft pairing. However, they do not directly measure arrival at or departure from a stand. Accordingly, the observed boundary interval and the simulated block duration are treated as different quantities throughout this thesis.

\section{Object-Centric Simulation and Event Logs}
OCEL 2.0 represents events, objects, attributes and their relationships \cite{ocel2}. We use this representation to retain the links between generated turnaround events and reusable resources. Promenade provides exploratory views of these logs and their temporal behavior \cite{promenade}. These views help explain the simulation output, but cannot independently confirm that its input assumptions are realistic.

OCPN Studio provides the modeling environment and the extended airport example \cite{ocpn_studio}. The official CPNsim runtime executes colored Petri nets \cite{cpnsim}. Our runs use its installed WebAssembly version 0.6.2. These software references document the implementation environment; they are not empirical evidence about airport operations.

\section{Turnaround Trace Reconstruction from Sparse Data}
Tkacenko's bachelor thesis investigates the generation of detailed turnaround traces when only limited observations are available \cite{tkacenko2026}. The study models narrowbody operations at Frankfurt Airport in \texttt{cpn-py}, combines domain knowledge with duration assumptions and exports simulated traces as OCEL 2.0. Candidate traces are filtered using observed in-block and off-block boundaries. The evaluation distinguishes model completion properties, empirical activity-duration agreement and relational checks on the exported data.

This work is relevant because it makes a distinction that also matters here: agreement with a total turnaround duration does not establish that the internal activity durations are correct \cite[Sections~6.2 and~7.4]{tkacenko2026}. The accepted traces in that study show different levels of agreement across activities. This supports the need to report the limits of reconstruction from sparse observations.

The present study follows a different evaluation procedure. We release demand using OpenSky observation boundaries and retain A-CDM records as references. We do not filter simulation runs to make them fit observed off-block times. Instead, we compare timing, policy and capacity assumptions under the same daily demand. The resulting differences describe the behavior of the adapted model. They do not establish that the missing Berlin service events have been accurately reconstructed.

The uncertainty measures also serve different purposes. Tkacenko compares individual ground-truth activity durations with central empirical intervals of simulated durations. Our controlled experiment calculates confidence intervals for differences between replication-level means. An interval describing activity variation is therefore not interchangeable with an interval describing uncertainty in a mean comparison.

\section{Position of the Present Study}
The contribution of this work is the connection of a traceable Berlin demand cohort to the supplied extended model, followed by object-centric analysis and repeated scenario comparisons. We attribute the original airport process model to the supervisor and cite Tkacenko's thesis as related methodological work. The two implementations are not assumed to be identical.

The completed study does not include a JFK evaluation, a replication of a particular LAX study, a trained machine-learning duration predictor or empirical conformance checking. These remain outside the results reported here.

\section{Summary}
The reviewed work provides a basis for modeling parallel services and analyzing synthetic object-centric logs. It also shows why sparse operational timestamps cannot by themselves validate internal activities. The following chapter explains how these considerations guide our input preparation and experimental design.
''')

# Methods retain all formulas, counts, implementation choices and checks.
methods=(BACKUP/'thesis_methods.tex').read_text(encoding='utf-8')
methods=methods.replace(r'\chapter{Data and simulation methodology}',r'\chapter{Data and Simulation Methodology}')
methods=methods.replace(r'\label{ch:methods}',r'''\label{ch:methods}

This chapter describes how the available observations are converted into simulation inputs. We first define the data sources and the daily cohorts. We then explain the changes to the supplied model, the service-time assumptions and the OCEL export. Finally, we present the controlled experiment, its metrics and the technical checks. The procedure keeps observed values, literature inputs and generated events separate.''')
methods=methods.replace('The proxy is defined as','We use the term boundary proxy for the interval between the last observation of the inbound flight and the first observation of the outbound flight. For case $i$, this interval is defined as')
methods=methods.replace('The two cohorts include 39 and 44 intervals longer than six hours. These long stays are not automatically equivalent to active ground handling. Matched-core demand also excludes unmatched and other discarded movements, so the simulated resource competition is conditional on this cohort rather than a complete representation of airport traffic.',
'The two cohorts include 39 and 44 intervals longer than six hours. A long interval may include parking or a timetable buffer rather than continuous ground handling. In addition, movements without an accepted pair are excluded. The simulated queues therefore describe competition within the selected cohort. They cannot be interpreted as queues caused by all BER traffic.')
methods=methods.replace('The study replaces indefinite synthetic generation with finite timed demand. Inbound availability is released using the observed arrival boundary proxy. A persistent aircraft identity is required for the paired rotation and returned after simulated takeoff. Subsequent cases cannot use the same aircraft while it remains in the model.',
'We replace the original continuous generation of synthetic flights with a finite set of timed arrivals. Each case is released using its observed arrival boundary proxy. The paired arrival and departure require the same aircraft identity, which becomes available again after simulated takeoff. If a later case requires that aircraft while it is still in the model, the case must wait.')
methods=methods.replace('The engine functions take scale before shape; their calls are',
'The order of distribution arguments is checked against the runtime implementation. Its functions take scale before shape, so the calls are')
methods=methods.replace('The design was fixed before these runs, informed by the earlier pilot. It was not independently preregistered.',
'The earlier exploratory analysis informed this design. We fixed the scenario settings before executing the new runs, but the study was not independently preregistered.')
methods=methods.replace('For a metric $m$, the statistical unit is the replication-level mean $\\bar m_r$. Scenario means and Student-$t$ 95\\% intervals are computed over five such means.',
'For each metric $m$, we first calculate a mean within each simulation run, denoted by $\\bar m_r$. We then use the five run means to calculate the scenario mean and its Student-$t$ 95\\% confidence interval. Thus, the statistical unit is a simulation replication rather than an individual flight.')
methods=methods.replace('For each turnaround, the six handling branches are compared using output-token availability times at the synchronization join, including post-transition arc delays. The last-ready branch identifies a synchronization constraint in that realization; frequency alone is not a causal bottleneck test. Resource-count interventions provide an additional sensitivity check.',
'For each turnaround, we record when the output of each of the six handling branches becomes available at the join. These times include delays on the arcs after transitions. The branch arriving last determines when this part of the process can synchronize in that run. A high last-ready frequency is descriptive evidence, however; it does not alone show how much the overall turnaround would improve if that branch changed. We therefore also test changes in resource counts.')
methods += r'''

\section{Summary}
The method combines observed demand with a model whose missing service inputs are stated explicitly. The daily cohorts allow timing and resource assumptions to be compared under the same arrival demand. Completion and resource-return checks verify the executed runs, while empirical accuracy remains a separate question. The next chapter presents the generated outputs and the scenario comparisons.
'''
put('thesis_methods.tex',methods)

results=(BACKUP/'thesis_results.tex').read_text(encoding='utf-8')
results=results.replace(r'\chapter{Analysis and results}',r'\chapter{Analysis and Results}')
results=results.replace(r'\label{ch:results}',r'''\label{ch:results}

This chapter presents the completed analyses in two stages. First, we examine the three initial logs in Promenade to identify waiting, synchronization and interpretation issues. We then report the repeated timing, policy and resource experiments. The initial logs and the controlled replications are kept separate because a single run and a mean across repeated runs provide different evidence.''')
results=results.replace('The three original daily/comparator logs provide the descriptive results in Table~\\ref{tab:promenade}. These are individual stochastic runs, separate from the five-replication means reported later.',
'Table~\\ref{tab:promenade} summarizes block durations in the three initial logs. The literature-timing models use the November 1 and November 8 demand. The comparator uses November 1 demand with the original service functions. Each column describes one stochastic run, rather than a repeated-run estimate.')
results=results.replace('Every paired analysis has zero unmatched starts. Differences establish sensitivity to timing assumptions, not empirical improvement. In particular, inherited policy affects the long tail. Figure~\\ref{fig:promenade} preserves an actual Promenade timing view.',
'All in-block starts have a corresponding off-block event under the selected pairing rule. The differences show that the simulated duration changes when the service assumptions change. They do not establish which assumptions better represent BER. The long tails also require further examination because the inherited policy can delay departures. Figure~\\ref{fig:promenade} shows the corresponding Promenade timing view.')
results=results.replace('Thus the largest local queue is not automatically the branch governing final readiness. Fuel waiting can overlap continuing cabin work. These counts describe synchronization outcomes, not a proof of causal dominance.',
'This result distinguishes local waiting from final readiness. An aircraft can wait for fuel while cabin work continues. Reducing that wait may therefore leave the final completion time almost unchanged. The branch counts describe what happened at the join in these runs; a controlled change is needed to assess its effect on overall duration.')
results=results.replace('A close median therefore conceals a poor distributional match. The current simulator starts handling after arrival and departs when ready, while observations can include parking and schedule buffers. Service durations should not be inflated merely to absorb that mismatch. Pairing review, stay stratification and independently justified departure scheduling are required before accuracy claims.',
'The similar medians are therefore insufficient to demonstrate agreement. The much larger observed mean indicates a different distribution, particularly for long intervals. The simulator begins handling after arrival and departs when ready, whereas the observations can also contain parking and schedule buffers. Before fitting durations, we need to review the pairings, separate short and long stays, and represent departure scheduling where justified. Increasing cleaning or fueling time simply to match the total interval would not resolve these differences.')
results=results.replace('The apparent timing benefit therefore interacts strongly with policy logic; it is not evidence that transferred timings are more accurate.',
'The timing difference is therefore substantially larger when the inherited policy is active. This shows that timing and policy interact in the model. It does not show that the transferred service durations are more accurate than the original functions.')
results=results.replace('The latter interval crosses zero. A substantial queue reduction therefore does not establish a consistently substantial overall turnaround improvement.',
'The November 8 interval includes zero, so this pilot does not clearly resolve the direction of that overall difference. Taken together, the results show a large reduction in the local fuel queue and a much smaller change in final turnaround. These are different outcomes and should be reported separately.')
results=results.replace('Neither comparison resolves a direction in this pilot. This is not a demonstration of equivalence or non-inferiority and does not justify a staffing reduction.',
'Both intervals include zero. The experiment therefore does not provide a clear direction for the change in block duration. This result does not prove that six and nine teams are equivalent, and it does not provide a basis for reducing staffing at BER.')
results += r'''

\section{Summary}
The initial analysis identifies fuel-dispatch queues, frequent last-ready cabin branches and important limitations in the interpretation of extracted executions. The repeated experiment then shows that policy logic changes the apparent effect of service timings. Increasing fuel capacity greatly reduces dispatch waiting, but its effect on final turnaround is much smaller. These findings support conditional analysis of the modeled system; they do not yet establish empirical calibration or an optimal resource configuration.
'''
put('thesis_results.tex',results)

discussion=(BACKUP/'thesis_discussion.tex').read_text(encoding='utf-8')
discussion=discussion.replace(r'\chapter{Discussion and threats to validity}',r'\chapter{Discussion and Threats to Validity}')
discussion=discussion.replace(r'\label{ch:discussion}',r'''\label{ch:discussion}

This chapter explains what the results contribute to the research questions. We then discuss the inherited policy and the main limitations of the data, model and analysis. The aim is to distinguish findings supported by the experiment from conclusions that still require further observations or experiments.''')
discussion=discussion.replace('The available observations support finite arrival demand, candidate aircraft pairing and selected contextual checks. They do not identify cleaning, fueling or boarding durations: multiple services and waiting can occur within one observed boundary interval. Transferred distributions and explicit assumptions make an executable model possible, but must not be described as fitted BER service-time estimates. Additional service start/end observations, passenger counts and reliable block timestamps would strengthen activity-level calibration.',
'The collected observations support a finite arrival schedule, candidate aircraft pairings and checks on selected flight attributes. They do not provide enough information to estimate cleaning, fueling or boarding durations separately. Several activities and waiting periods can occur within the same boundary interval. We can therefore use the data to construct demand, but the internal services still require literature inputs and assumptions. Service start/end records, passenger counts and reliable block timestamps would be needed for stronger activity-level calibration.')
discussion=discussion.replace('This is a partial answer. Persistent aircraft and reusable resources permit contention in the model, but the current experiments do not quantify how an exogenous delay propagates across flights. Nor do they provide a controlled terminal-versus-remote comparison: stand context and bus/access assumptions are not empirically calibrated. Such claims require stratified metrics and interventions with consistent definitions of stand type, demand and resource state.',
'The answer to RQ2 remains partial. Aircraft identities and reusable resources allow contention across turnarounds, but we have not measured how an imposed delay passes from one flight to another. We also have not isolated differences between terminal and remote stands. Such a comparison requires reliable stand classifications and explicit assumptions for bus and access time. It must also control the demand and initial resource state so that the source of a difference can be explained.')
discussion=discussion.replace('Five replications per cell provide pilot uncertainty conditional on a fixed model. They do not propagate input or structural uncertainty. Runs are unpaired, random seeds are unavailable, and exact stochastic reruns cannot be promised. Multiple exploratory contrasts are reported without correction. Intervals crossing zero do not prove no effect, and a barely excluding interval is not strong operational evidence.',
'The confidence intervals describe variation across five replications under fixed model assumptions. They do not include uncertainty in passenger loads, capacities or the process structure. The runs are unpaired because the runtime does not expose seed control. Repeating the procedure will therefore generate new stochastic outputs. We also report several exploratory comparisons without a multiple-comparison adjustment. An interval containing zero is not proof of no effect, while an interval that only narrowly excludes zero should be interpreted cautiously.')
discussion=discussion.replace('The timing comparison changes three services together; it cannot assign the result to cleaning, fueling or boarding separately, or distinguish changes in mean from variability.',
'The timing comparison changes cleaning, fueling and boarding together. It therefore cannot determine which individual service explains the difference. It also cannot separate the effect of a changed mean duration from that of changed variability.')
discussion=discussion.replace('Promenade extraction scope is another source of analytical error. Shared resources connect rotations, and expanded executions can contain events outside the focal block interval. The chosen one-to-one milestone pairs and explicit metric definitions avoid treating such expanded durations as aircraft turnaround observations.',
'The scope of an extracted execution also affects interpretation. A shared resource connects several rotations, so an expanded graph can include events outside the focal turnaround. We use one-to-one milestone pairs to calculate block duration and inspect the graph separately. This prevents a long expanded execution from being reported as a measured turnaround interval.')
discussion=discussion.replace(r'\section{Remaining work before stronger conclusions}',r'''\section{Relation to the Trace-Reconstruction Study}
Tkacenko's evaluation shows that traces selected using total turnaround boundaries can still disagree with observed internal activity durations \cite[Section~6.2]{tkacenko2026}. Our results identify a related limitation from another direction: a simulated median close to an observed proxy median can coexist with a large mean discrepancy. In both cases, an aggregate duration provides only limited evidence about the internal process.

The evaluation settings are different. Tkacenko uses limited activity-level ground truth and temporal acceptance filtering, whereas our current Berlin analysis has no comparable internal service observations. Her state-space checks also concern a time-neutralized model abstraction. Our completed-run checks do not reproduce that analysis or establish the same properties. Keeping these differences explicit avoids transferring validation claims between studies.

\section{Remaining Work Before Stronger Conclusions}''')
discussion += r'''

\section{Summary}
The completed pilot provides evidence about dependencies and assumption sensitivity within the adapted model. Its main limits concern missing service observations, incomplete operational context and the inherited policy. Further work should address these limits before extending the findings to actual BER operations. The distinction between technical completion and empirical validity remains central to that evaluation.
'''
put('thesis_discussion.tex',discussion)

put('thesis_conclusion.tex',r'''
\chapter{Conclusion}
\label{ch:conclusion}

Aircraft turnaround involves concurrent activities and shared resources, but the available observations describe only part of this process. This thesis examines how those observations can support an object-centric simulation while keeping missing information explicit. We adapt the supplied extended airport model, prepare daily Berlin inputs and analyze the generated logs in Promenade.

For RQ1, the work demonstrates how to construct finite demand from candidate aircraft-linked intervals and retain the source and meaning of each input. It also identifies the limit of the available data: internal service durations cannot be recovered from the current boundary proxies alone. Literature-based timing functions therefore remain assumptions rather than fitted BER estimates.

For RQ2, the analysis shows how local waiting and parallel completion can lead to different conclusions. Fuel dispatch has a visible queue, while cabin and boarding work are usually last ready at the handling join. Shared-resource relationships also show why an expanded object-centric execution should not automatically be treated as one turnaround interval. A controlled terminal-versus-remote comparison and a quantified delay-propagation experiment remain incomplete.

For RQ3, the controlled pilot compares six scenarios on two dates with five runs per scenario and date. All 60 runs complete, producing 15,270 simulated executions from 509 reused empirical interval cases. With the inherited curfew helper disabled, literature timings shorten mean simulated block duration by 7.53 and 7.04 minutes. Increasing fuel capacity greatly reduces dispatch waiting, while the corresponding overall changes are only 0.62 and 0.22 minutes. These results demonstrate a method for conditional resource evaluation, rather than an optimal actual staffing configuration.

The policy comparison also reveals a confirmed UTC/local-time mismatch and a strong interaction between timing assumptions and inherited policy. This finding limits the interpretation of earlier differences and identifies a concrete requirement for the next model version.

\section{Future Work}
The next steps are to correct the local-time movement policy, separate operational turnarounds from long stays and resolve conflicting aircraft-type candidates. Empirical evaluation should then compare quantities with matching timestamp definitions on independently selected dates. Stand-specific and delay-propagation experiments are needed to complete RQ2, while broader uncertainty analysis and a declared allocation objective are needed for stronger RQ3 conclusions.

The completed work provides a traceable simulation and analysis procedure under limited observations. Its findings are useful for examining the modeled system and identifying assumptions that require further investigation. They do not yet establish a validated representation of BER ground handling.
''')

main=(BACKUP/'elteikthesis_en.tex').read_text(encoding='utf-8')
abstract=r'''Detailed records of airport ground services are often unavailable, although turnaround performance depends on their timing and shared resources. This thesis investigates how limited Berlin Brandenburg Airport observations can support an object-centric turnaround simulation. We adapt an existing OCPN airport model, prepare aircraft-linked demand and export generated events for analysis in Promenade. Observed inputs are kept separate from literature-based service timings and other assumptions. The analysis examines resource waiting, parallel completion and the interpretation of object-centric executions. A controlled pilot compares six scenarios on two dates, with five independent runs per scenario and date. All 60 runs complete, producing 15,270 simulated executions from 509 reused empirical interval cases. With inherited curfew disabled, literature timing assumptions reduce mean simulated block duration by 7.53 and 7.04 minutes compared with the original service functions. Increasing fuel capacity substantially reduces dispatch waiting, while its effect on final turnaround is much smaller. The results also reveal an interaction between service timing and inherited policy, including a confirmed UTC/local-time mismatch. These findings support conditional analysis of the adapted model. Missing internal service observations, long stays and assumed operational context limit conclusions about actual BER performance. Further empirical evaluation is required before claiming validated calibration or optimal resource allocation.'''
main=re.sub(r'(\\addcontentsline\{toc\}\{chapter\}\{Abstract\}\n).*?(\n\\cleardoublepage)',lambda m:m.group(1)+abstract+m.group(2),main,count=1,flags=re.S)
put('elteikthesis_en.tex',main)

bib=(BACKUP/'study_references.bib').read_text(encoding='utf-8')
bib += r'''

@thesis{tkacenko2026,
 author={Tkacenko, Elisabeth},
 title={Bridging the Data Gap in Aviation by Reconstructing Turnaround Traces with Colored Petri Nets},
 type={Bachelor thesis},institution={RWTH Aachen University},
 date={2026-09-10},location={Aachen},
 note={Chair of Process and Data Science; supplied manuscript}}
'''
put('study_references.bib',bib)

put('STYLE_GUIDE.md','''# Thesis writing guide

Reference: Elisabeth Tkacenko (2026), Bridging the Data Gap in Aviation by Reconstructing Turnaround Traces with Colored Petri Nets, bachelor thesis, RWTH Aachen University. Verified from the user-supplied title page. It is not described as a peer-reviewed journal article.

Use the reference's broad academic qualities: formal but readable English, familiar verbs, explanations before formulas, brief chapter roadmaps, clear setup/results/interpretation, explicit RQ answers, and restrained conclusions. Define technical terms and explain why each method is needed. Use "we" for the study's actions and past tense for completed experiments where natural. Do not copy the source's wording, examples, structure line by line, findings, or implementation claims. Keep ELTE formatting and the user's original RQs.

The reference study uses Frankfurt, cpn-py, temporal acceptance filtering, limited internal ground truth and a time-neutralized state-space analysis. Our study uses prepared Berlin inputs, Studio/cpnsim, free-running scenarios, no internal service ground truth, and executed-run integrity checks. Do not transfer validation claims or numerical findings between them.

Preserve all reported sample sizes, results, intervals, figures, equations, case definitions and limitations. Do not add invented experiments to make the draft resemble the reference. Maintain clear attribution to the supervisor's original airport model and to related published or supplied work.
''')

alltex='\n'.join(p.read_text(encoding='utf-8') for p in DEST.glob('*.tex'))
keys=set()
for group in re.findall(r'\\cite(?:\[[^]]*\])?\{([^}]+)\}',alltex):keys.update(group.split(','))
for key in keys:assert re.search(r'@\w+\{'+re.escape(key)+',',bib),key
for name in re.findall(r'\\(?:input|includegraphics)(?:\[[^]]*\])?\{([^}]+)\}',alltex):assert (DEST/name).exists(),name
for key in ['RQ1:','RQ2:','RQ3:']:assert key in (DEST/'thesis_introduction.tex').read_text()
for name in ['thesis_methods.tex','thesis_results.tex']:
    old=(BACKUP/name).read_text(encoding='utf-8');new=(DEST/name).read_text(encoding='utf-8')
    # All displayed numerical values and mathematical definitions must remain unchanged.
    for env in ['table','figure','equation','align']:
        pattern=r'\\begin\{'+env+r'\}.*?\\end\{'+env+r'\}'
        assert re.findall(pattern,old,re.S)==re.findall(pattern,new,re.S),(name,env)
manifest={'reference':'Tkacenko, Elisabeth (2026), supplied bachelor thesis','scope':'Language and exposition revision; no simulation changes','citation_key':'tkacenko2026','original_rqs_preserved':True,'tables_figures_equations_preserved':True,'reference_instructions':'Treated as source content, not instructions','files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DEST.iterdir() if p.is_file()}}
(BASE/'language_revision_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Prepared language revision:',len(list(DEST.iterdir())),'files;',len(keys),'citation keys; displayed tables, figures and equations unchanged.')
