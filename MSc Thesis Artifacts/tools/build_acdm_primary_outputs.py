"""Create an observed-takeoff OCEL, labeled pilot models, and a provenance-correct thesis."""
from pathlib import Path
import json,csv,shutil,re,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'output/acdm_primary_20261119'
S=json.loads((BASE/'summary.json').read_text())
with (BASE/'ACDM_Berlin_Primary_With_OpenSky_Check.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
chosen=[r for r in rows if r['crosscheck_status']=='unique_callsign_time_candidate_not_identity_verification']
objects={};events=[]
for r in chosen:
 time=datetime.fromisoformat(r['atot']).replace(tzinfo=timezone.utc).isoformat()
 fid='departure:'+r['record_key'];relations=[]
 def obj(typ,value):
  oid=typ.lower()+':'+value
  if oid not in objects:objects[oid]={'id':oid,'type':typ,'attributes':[],'relationships':[]}
  return oid
 objects[fid]={'id':fid,'type':'Departure','attributes':[],'relationships':[]}
 relations.append({'objectId':fid,'qualifier':'departure'})
 for typ,field,qual in [('Aircraft','aircraft_reg','aircraft'),('Stand','parking_pos','departure_stand')]:
  if r[field]:
   oid=obj(typ,r[field]);relations.append({'objectId':oid,'qualifier':qual});objects[fid]['relationships'].append({'objectId':oid,'qualifier':qual})
 attrs=[{'name':k,'value':r[k]} for k in ['record_key','source_day','callsign','aircraft_icao','tobt','tsat','atot']]
 attrs.append({'name':'timestamp_basis','value':'A-CDM ATOT interpreted as UTC, supported by cross-check; provider timezone contract unconfirmed'})
 for k in ['atot_minus_tobt_min','atot_minus_tsat_min']:
  if r[k]!='':attrs.append({'name':k,'value':float(r[k])})
 events.append({'id':'atot:'+r['record_key'],'type':'ActualTakeoff','time':time,'attributes':attrs,'relationships':relations})
log={'objectTypes':[{'name':t,'attributes':[]} for t in ['Departure','Aircraft','Stand']],'eventTypes':[{'name':'ActualTakeoff','attributes':[{'name':k,'type':'string'} for k in ['record_key','source_day','callsign','aircraft_icao','tobt','tsat','atot','timestamp_basis']]+[{'name':k,'type':'float'} for k in ['atot_minus_tobt_min','atot_minus_tsat_min']]}],'objects':list(objects.values()),'events':events}
assert len(events)==1257 and len({e['id'] for e in events})==1257
for e in events:
 for rel in e['relationships']:assert rel['objectId'] in objects
(BASE/'BER_ACDM_Observed_Departures_UTC_Hypothesis.ocel.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
modeldir=BASE/'exploratory_pilot_models';modeldir.mkdir(exist_ok=True)
modelchecks=[]
for name in ['BER_MSc_2026-11-01.ocpn','BER_MSc_2026-11-08.ocpn','BER_MSc_timing_baseline.ocpn']:
 src=ROOT/'output/ocpn'/name;d=json.loads(src.read_text(encoding='utf-8'))
 original={k:v for k,v in d.items() if k not in ['metadata','ocpnName']}
 d['ocpnName']='EXPLORATORY OpenSky demand pilot - '+name.replace('.ocpn','')
 d['metadata']['name']=d['ocpnName']
 d['metadata']['description']='Exploratory pilot using OpenSky-derived arrival demand. A-CDM supplies only candidate reference attributes in this historical build. NOT an A-CDM-only calibrated model. Service timings transferred from literature or inherited. Do not relabel 10,940 OpenSky pairs as A-CDM records. Existing analyzed behavior preserved; metadata-only revision.'
 d['metadata']['version']='2.0-provenance-label-review'
 target=modeldir/name;target.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
 assert {k:v for k,v in d.items() if k not in ['metadata','ocpnName']}==original
 modelchecks.append({'file':name,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'labeled_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'simulation_structure_and_inputs_unchanged':True})
(modeldir/'review.json').write_text(json.dumps(modelchecks,indent=2),encoding='utf-8')
(modeldir/'README.md').write_text('''# Exploratory pilot, provenance labels reviewed

Only names and metadata descriptions change. Petri nets, inputs, timing functions, settings and monitors are identical to the analyzed source files. This is not a new execution or an A-CDM-only calibration. Original models and logs remain untouched.

An A-CDM-only full turnaround model requires arrival/AIBT and departure/AOBT observations or independently justified additional assumptions. The five departure snapshots do not contain those arrival/block milestones. Consequently no new purported observed-turnaround model or service-time fit is generated from these departure-only records.
''',encoding='utf-8')
OUT=BASE/'overleaf_updated';OUT.mkdir(exist_ok=True)
BEFORE=BASE/'overleaf_before'
for p in BEFORE.iterdir():shutil.copy2(p,OUT/p.name)
def put(name,s):(OUT/name).write_text(s.strip()+'\n',encoding='utf-8')
put('thesis_methods.tex',r'''
\chapter{A-CDM Data and Evaluation Method}
\label{ch:methods}
This chapter defines the primary empirical dataset and the role of the independent cross-check. Every primary row comes from the BER A-CDM application. OpenSky contributes comparison observations only. The earlier turnaround reconstruction and its simulation experiments are documented separately in the appendices.

\section{Primary Source and Unit of Analysis}
The primary collection contains 1,322 departure records from five finalized snapshots of the BER A-CDM application. The source dates are 1, 5, 8, 15 and 16 November 2026, contributing 289, 257, 264, 254 and 258 records, respectively. These are separated snapshots, not continuous observations from October to November. Pagination captures the records returned for the requested scheduled-departure date; it does not independently establish complete airport coverage.

Each row represents one departure record. The source provides callsign, aircraft registration/type, selected stand/runway attributes and departure fields including TOBT, TSAT and ATOT. It does not provide the inbound landing time, AIBT, AOBT or internal cleaning, fueling and boarding timestamps required for a measured full-turnaround case. We therefore do not label these rows as complete landing-to-next-takeoff intervals.

The preparation procedure preserves canceled and incomplete records in the master table. It verifies CSV/JSON agreement, manifest row counts and the hashes of saved raw responses. Source keys, dates and review flags remain available for each row. No missing milestones or service durations are synthesized.

\section{Inclusion Rules and Timestamp Meanings}
There are 1,286 records with eligible ATOT and valid source identifiers/date/airport fields. The remaining 36 records include 15 canceled departures and 21 other records without an eligible actual takeoff. A complete TOBT/TSAT/ATOT triple exists for 1,283 eligible departures. A sensitivity subset of 1,261 also requires nonnegative differences for the target sequence; the master table retains all records. Negative differences require interpretation rather than automatic correction.

TOBT is a target off-block value and TSAT is a target start-up approval value. Their source timestamps describe planned targets, not the times those targets were issued and not actual execution of a service. ATOT is the source actual-takeoff field. The precise source mapping of STD and the meaning of \texttt{taxitime} still require confirmation. We retain the original naive timestamps and keep timezone hypotheses explicit.

For complete eligible triples, we describe
\begin{align}
\Delta_{\mathrm{target}}&=\mathrm{TSAT}-\mathrm{TOBT},\\
\Delta_{\mathrm{ATOT,TSAT}}&=\mathrm{ATOT}-\mathrm{TSAT},\\
\Delta_{\mathrm{ATOT,TOBT}}&=\mathrm{ATOT}-\mathrm{TOBT}.
\end{align}
These differences characterize departure targets and their relation to takeoff. They are not measured cleaning time, taxi time, resource queueing or AIBT--AOBT duration. End-of-day target values cannot automatically be treated as information available to an earlier prediction.

\section{OpenSky as an External Departure Cross-Check}
We compare A-CDM ATOT with OpenSky's first observation of the outbound flight. OpenSky remains the external comparison source in this primary analysis and does not create primary A-CDM rows. Its flight boundaries are surveillance-derived proxies \cite{opensky_rest}.

The matching procedure normalizes callsigns and tests two explicit interpretations of each naive A-CDM ATOT: UTC and Europe/Berlin. A candidate must agree in callsign and fall within 30 minutes of the interpreted ATOT. We retain a unique candidate only when no other A-CDM row reuses its OpenSky flight. Missing and ambiguous matches remain visible. Data retrieved for 15 and 16 November extend this cross-check beyond the earlier saved dates; earlier simulation inputs remain frozen.

For a unique candidate, the signed difference is
\begin{equation}
\delta_i=t^{\mathrm{OpenSky}}_{i,\mathrm{firstSeen}}-t^{\mathrm{A\mbox{-}CDM}}_{i,\mathrm{ATOT}}.
\end{equation}
We report the signed and absolute differences together with match coverage. Agreement supports temporal correspondence, but does not certify aircraft identity, independently document the provider's timezone contract or establish completeness. The difference statistics are conditional on the matching rule. A departure cross-check does not validate arrival or internal service events.

\section{Observed Object-Centric Departure Log}
The new empirical OCEL contains one ActualTakeoff event for each of the 1,257 uniquely matched records. Every event timestamp and its source fields originate in A-CDM. The export uses the empirically supported UTC hypothesis and retains the original naive ATOT plus an explicit timestamp-basis attribute. This is an assumption for exploratory import, not a claim of a verified API timezone contract.

Departure, Aircraft and Stand objects retain available source identities. Missing aircraft or stand values do not create invented identities. TOBT and TSAT remain attributes of the takeoff event; they are not converted into observed boarding or start-up events. This log can support inspection of departures and object relationships in Promenade, but cannot yield a measured turnaround duration from a single observed milestone per flight.

\section{Scope of the OCPN Work}
The supplied extended airport model remains the supervisor's baseline. The completed OCPN/Promenade pilot uses a different, auxiliary OpenSky-derived demand cohort. Its details and unchanged numerical results appear in the appendices. The new A-CDM-primary analysis does not relabel those runs or treat them as A-CDM-only calibration.

No complete A-CDM-only turnaround model is claimed at this stage. Initializing and evaluating one requires arrival/block milestones or additional assumptions that would need independent justification. Source-label updates to copies of the pilot models preserve their process structure and analyzed inputs. They do not constitute new simulations.
''')
put('thesis_results.tex',r'''
\chapter{Empirical A-CDM Analysis}
\label{ch:results}
This chapter presents findings from the A-CDM primary collection. We distinguish source coverage, correspondence with OpenSky and descriptive target intervals. The historical simulation results remain a separate exploratory study in the appendices.

\section{Snapshot Coverage}
\begin{table}[htbp]\centering\small
\begin{tabular}{lrrr}\hline
Source date & Records & Eligible ATOT & Unique OpenSky candidates\\\hline
1 November & 289 & 283 & 280\\
5 November & 257 & 251 & 244\\
8 November & 264 & 250 & 243\\
15 November & 254 & 249 & 242\\
16 November & 258 & 253 & 248\\\hline
Total & 1,322 & 1,286 & 1,257\\\hline
\end{tabular}
\caption{A-CDM primary records and departure cross-check coverage. Dates describe the source snapshots rather than continuous period coverage.}\label{tab:acdmcoverage}
\end{table}
The collection includes 1,286 OFF, 15 XLD, 17 SKD and four COM source statuses. The primary record count includes canceled and unfinished departures. Across all 1,322 rows, registration is missing in 14, stand in 19 and runway in 24. These omissions restrict analyses requiring those fields but do not invalidate every departure metric. The data contain no observed full-turnaround pairs with both arrival and departure/block milestones.

\section{Departure-Time Correspondence}
Of the 1,286 eligible actual takeoffs, 1,257 have a unique callsign/time candidate, corresponding to 97.7\%. The remaining 29 have no candidate within the specified tolerance. All retained candidates support the UTC interpretation rather than Europe/Berlin under this rule.

Among the retained candidates, the median signed OpenSky-minus-A-CDM difference is $-0.117$ minutes, approximately seven seconds earlier. The median absolute difference is 0.133 minutes, approximately eight seconds. Mean absolute difference is 0.224 minutes. There are 1,237 matches within one minute and all 1,257 within five minutes. The signed range is approximately $[-3.12,4.00]$ minutes.

These results provide evidence of close departure-time correspondence for the matched subset. They do not establish exact takeoff ground truth from OpenSky, complete airport coverage or the identity of every physical aircraft. Because the matching procedure selects candidates within 30 minutes, the reported difference distribution is conditional on that selection. Missing matches are not automatically operational failures.

\section{Target-to-Takeoff Descriptions}
For the 1,283 complete eligible triples, Table~\ref{tab:acdmmetrics} summarizes the source-value differences. Negative values remain in the analysis and are available for review.
\begin{table}[htbp]\centering\small
\begin{tabular}{lrr}\hline
Difference (minutes) & Mean & Median\\\hline
TSAT minus TOBT & 1.30 & 0.00\\
ATOT minus TSAT & 12.58 & 12.12\\
ATOT minus TOBT & 13.88 & 12.93\\\hline
\end{tabular}
\caption{Descriptive target/actual differences for complete eligible A-CDM departure triples, $n=1,283$. These are not service or queue durations.}\label{tab:acdmmetrics}
\end{table}
The nonnegative sensitivity subset contains 1,261 records. Thus, 22 complete triples fail at least one nonnegative-sequence requirement. This does not prove that all such records are erroneous. Target revisions and different milestone meanings can affect ordering, and the current snapshots do not preserve a full target-update history.

\section{Relation to the Earlier 10,940-Row Table}
The 10,940 pairing-screened rows are an auxiliary reconstruction from OpenSky inbound/outbound observations. Only 826 have a candidate A-CDM reference link in the frozen build. Their existence does not enlarge the primary A-CDM collection to 10,940 rows. The full candidate table has 11,203 rows before the earlier screening rules.

The auxiliary table approximates an aircraft's arrival-to-next-departure interval. It is neither a measured A-CDM turnaround table nor measured AIBT--AOBT. The earlier 60 simulation runs reuse 509 of those interval candidates across scenarios and replications. Their 15,270 generated executions are not additional empirical observations.

\section{Model Readiness}
The A-CDM collection supports departure-level descriptions and an independent timestamp correspondence check. It does not identify cleaning, fueling or boarding distributions, inbound release times or measured block duration. The next calibration step requires additional arrival/block observations or an agreed, explicitly assumed scope. The retained exploratory simulation results remain useful for studying dependencies under stated assumptions.
''')
# Retain all prior model and simulation material without changing its evidence or results.
oldmethods=(BEFORE/'thesis_methods.tex').read_text(encoding='utf-8').replace(r'\chapter{Data and Simulation Methodology}',r'\chapter{Auxiliary OpenSky-Demand Simulation Method}').replace(r'\label{ch:methods}',r'\label{app:auxmethods}')
oldmethods=oldmethods.replace(r'\label{app:auxmethods}',r'''\label{app:auxmethods}
\noindent\textbf{Historical exploratory pilot.} This appendix preserves the earlier OpenSky-derived demand method. It is separate from the A-CDM primary analysis and is not an A-CDM-only calibration. The numerical inputs and results remain unchanged.''')
oldresults=(BEFORE/'thesis_results.tex').read_text(encoding='utf-8').replace(r'\chapter{Analysis and Results}',r'\chapter{Auxiliary Simulation and Promenade Results}').replace(r'\label{ch:results}',r'\label{app:auxresults}')
oldresults=oldresults.replace(r'\label{app:auxresults}',r'''\label{app:auxresults}
\noindent\textbf{Historical exploratory pilot.} The following results describe generated behavior under OpenSky-derived demand and literature/inherited assumptions. They are not new A-CDM-only results.''')
put('thesis_auxiliary_pilot.tex',oldmethods+'\n\n'+oldresults)

intro=(BEFORE/'thesis_introduction.tex').read_text(encoding='utf-8')
intro=intro.replace('We adapt an existing airport model using prepared observations from Berlin Brandenburg Airport (BER), document the assumptions used for missing information and analyze the generated event logs. We then compare service-time assumptions, policy rules and resource capacities through repeated simulation.', 'The primary empirical analysis uses departure records from the Berlin Brandenburg Airport (BER) A-CDM application, with OpenSky serving as an independent departure-time cross-check. Separately, we document an earlier simulation pilot that adapted an existing airport model using an auxiliary OpenSky reconstruction. The two studies retain their actual data origins.')
intro=intro.replace('The implemented study therefore combines OpenSky flight-boundary observations with A-CDM reference records. Literature and explicitly stated assumptions supply the missing service inputs.', 'The primary departure study therefore keeps A-CDM as the source of every empirical row and uses OpenSky only to cross-check its takeoff observations. The earlier OpenSky-demand simulation remains an auxiliary pilot. Literature and explicitly stated assumptions supply that pilot\'s missing service inputs.')
intro=intro.replace('For RQ1, we examine which model inputs can be supported by the collected data.', 'For RQ1, we examine which inputs the primary A-CDM observations can support and which remain unavailable.')
intro=intro.replace('For RQ2, we analyze resource waiting and the synchronization of parallel activities.', 'For RQ2, the auxiliary simulation analyzes resource waiting and the synchronization of parallel activities.')
intro=intro.replace('For RQ3, we evaluate selected capacity changes under fixed assumptions.', 'For RQ3, the auxiliary pilot evaluates selected capacity changes under fixed assumptions.')
intro=intro.replace('Chapter~\\ref{ch:methods} describes the data, model changes and experimental procedure. Chapter~\\ref{ch:results} presents the Promenade analysis and repeated simulation results.', 'Chapter~\\ref{ch:methods} defines the primary A-CDM data and departure cross-check. Chapter~\\ref{ch:results} presents its empirical findings. Appendices~\\ref{app:auxmethods} and~\\ref{app:auxresults} preserve the separate OCPN/Promenade pilot and repeated simulation results.')
intro=intro.replace(r'\section{Research Goals and Contributions}',r'''\section{Research Goals and Contributions}
The current primary contribution is an audited collection of 1,322 A-CDM departures and its external timestamp cross-check. The earlier 10,940 rows originate in OpenSky and remain auxiliary. They cannot be described as A-CDM observations by changing labels.
''')
put('thesis_introduction.tex',intro)
related=(BEFORE/'thesis_related.tex').read_text(encoding='utf-8')
related=related.replace('The present study follows a different evaluation procedure. We release demand using OpenSky observation boundaries and retain A-CDM records as references.', 'The earlier auxiliary pilot follows a different evaluation procedure: it releases demand using OpenSky observation boundaries and retains A-CDM records as references. The current primary empirical analysis instead starts with A-CDM departure rows and uses OpenSky solely for external correspondence checks.')
put('thesis_related.tex',related)
discussion=(BEFORE/'thesis_discussion.tex').read_text(encoding='utf-8')
discussion=discussion.replace(r'\label{ch:discussion}',r'''\label{ch:discussion}
\section{Primary and Auxiliary Evidence}
The primary empirical findings use 1,322 A-CDM departure records, of which 1,286 contain eligible ATOT. OpenSky provides 1,257 unique departure correspondence candidates. The 10,940 aircraft-pair rows and all previously reported OCPN/Promenade results belong to the separate auxiliary reconstruction. Their numbers and limitations remain available in the appendices. No model-only result is relabeled as an observed A-CDM service duration.
''')
discussion=discussion.replace('The collected observations support a finite arrival schedule, candidate aircraft pairings and checks on selected flight attributes.', 'The auxiliary OpenSky observations supported a finite arrival schedule and candidate aircraft pairing. The primary A-CDM collection supports departure targets, actual takeoffs and selected flight attributes, but does not supply measured inbound release times.')
discussion=discussion.replace(r'\subsection{RQ2: dependencies, queues and propagation}',r'''\subsection{RQ2: dependencies, queues and propagation}
The following dependency findings concern the auxiliary simulation. The new departure-only empirical log cannot by itself recover ground-service queues or full turnaround propagation.
''')
discussion=discussion.replace(r'\subsection{RQ3: conditional resource evaluation}',r'''\subsection{RQ3: conditional resource evaluation}
The capacity scenarios remain conditional pilot experiments using auxiliary demand. We have not recalibrated them from the five A-CDM departure snapshots.
''')
put('thesis_discussion.tex',discussion)
put('thesis_conclusion.tex',r'''
\chapter{Conclusion}
\label{ch:conclusion}
This thesis now distinguishes a primary A-CDM empirical analysis from an earlier auxiliary simulation study. The primary collection contains 1,322 departure records from five saved dates. Source checks establish CSV/JSON consistency and traceability. Of 1,286 eligible actual takeoffs, 1,257 have a unique OpenSky callsign/time candidate. The close timestamp correspondence supports the departure comparison for that subset, subject to proxy and timezone limitations.

For RQ1, the A-CDM observations support departure-level descriptions and checks on selected attributes. They do not provide arrival/block milestones or internal service observations needed for full activity calibration. OpenSky validation cannot supply those missing fields while also claiming that all inputs originate in A-CDM.

For RQ2 and RQ3, the auxiliary OCPN/Promenade work demonstrates analysis of shared-resource waiting and selected capacity scenarios. Its 60 replications and numerical findings remain unchanged in the appendices. The 10,940-row input cohort originates in OpenSky, and its generated outputs remain conditional model evidence. These results do not establish an A-CDM-only calibrated BER turnaround model or optimal real staffing.

\section{Future Work}
The next step is to agree on the empirical scope with the supervisor and obtain reliable arrival/block milestones if full turnaround calibration remains the objective. Further work must also correct local-time movement policy, separate long stays and evaluate matching observable quantities on independently selected dates. Terminal/remote comparisons and controlled inter-flight delay propagation remain necessary for a fuller answer to RQ2.

The completed work provides an auditable A-CDM primary dataset, a reproducible departure cross-check and a documented exploratory simulation. Its value depends on preserving these distinctions rather than increasing the apparent evidence by relabeling reconstructed or simulated records.
''')
repro=(BEFORE/'thesis_reproducibility.tex').read_text(encoding='utf-8')
repro=repro.replace(r'\label{app:repro}',r'''\label{app:repro}
\section{A-CDM Primary Update}
The current primary file is \texttt{ACDM\_Berlin\_Primary\_With\_OpenSky\_Check.csv}. It contains 1,322 source A-CDM rows. The cross-check file and summary retain all eligibility/matching outcomes. The observed-takeoff OCEL contains the 1,257 uniquely matched records, with one takeoff event per departure and an explicit UTC hypothesis. The export does not create target or ground-service events.

The previous model packages and results below refer to the auxiliary OpenSky-demand pilot. Metadata-reviewed copies clarify that origin while preserving all executable content. The original baseline and analyzed versions remain untouched.
''')
put('thesis_reproducibility.tex',repro)
main=(BEFORE/'elteikthesis_en.tex').read_text(encoding='utf-8')
abstract='''This thesis investigates airport turnaround analysis under limited operational observations. The primary empirical collection contains 1,322 departure records from the Berlin Brandenburg Airport A-CDM application. OpenSky provides an independent departure-time cross-check rather than the source of these primary rows. Among 1,286 eligible actual takeoffs, 1,257 have a unique callsign/time correspondence candidate, and 1,237 of those agree within one minute. Target-to-takeoff differences describe departure values but do not measure ground-service durations. A separate earlier study used an auxiliary OpenSky reconstruction to adapt an object-centric airport simulation and analyze its generated logs in Promenade. Its 60 repeated runs remain conditional pilot evidence and appear separately in the appendices. The 10,940 reconstructed aircraft intervals are not A-CDM observations. The primary A-CDM collection lacks arrival/block milestones and internal service timestamps, which prevents a claim of full turnaround calibration from those records alone. The contribution is an auditable empirical collection, an explicit correspondence method and a documented exploratory simulation, with their sources and limits kept distinct.'''
main=re.sub(r'(\\addcontentsline\{toc\}\{chapter\}\{Abstract\}\n).*?(\n\\cleardoublepage)',lambda m:m.group(1)+abstract+m.group(2),main,count=1,flags=re.S)
main=main.replace(r'\input{thesis_reproducibility.tex}',r'\input{thesis_reproducibility.tex}'+'\n\\cleardoublepage\n'+r'\input{thesis_auxiliary_pilot.tex}')
put('elteikthesis_en.tex',main)
(BASE/'ocel_integrity.json').write_text(json.dumps({'events':len(events),'objects':len(objects),'object_counts':{t:sum(o['type']==t for o in objects.values()) for t in ['Departure','Aircraft','Stand']},'event_types':['ActualTakeoff'],'source':'A-CDM only for event data','timestamp_basis':'explicitUTC hypothesis','all_relationships_resolve':True,'formal_schema_validation':False},indent=2),encoding='utf-8')
print('Prepared A-CDM OCEL, metadata-only pilot model copies and10 Overleaf source files.')
