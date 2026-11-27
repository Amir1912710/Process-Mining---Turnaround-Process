import fs from 'node:fs/promises';
import path from 'node:path';
const root='C:/Users/amira/Documents/ChatGPT/Thesis Project';
const base=path.join(root,'output/acdm_primary_20261119');
const ink='#142B40',teal='#087F8C',muted='#506276';
function text(s,value,x,y,w,h,size=28,bold=false,color=ink){
 const t=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 t.text=value.replace(/([a-z])(?=\d)/g,'$1 ').replace(/(\d)(?=[A-Za-z])/g,'$1 ');t.text.style={typeface:'Arial',fontSize:size,bold,color};return t;
}
function slide(p,title,source,notes){
 const s=p.slides.add({width:1280,height:720});s.background.fill='#FFFFFF';
 text(s,title,72,48,1136,100,44,true);
 text(s,source,72,656,1136,36,15,false,muted);
 s.speakerNotes.text=notes+'\n\nProgress window: 12 October–19 November 2026. Meeting: 20 November 2026. The earlier simulation remains an exploratory pilot.\n\nReference details\nSchultz, M., Kunze, T., Oreschko, B., and Fricke, H. (2012). Dynamic Turnaround Management in a Highly Automated Airport Environment. ICAS. https://www.icas.org/icas_archive/ICAS2012/PAPERS/808.PDF\nSchultz, M. (2018). Fast Aircraft Turnaround Enabled by Reliable Passenger Boarding. Aerospace, 5(1), 8. https://doi.org/10.3390/aerospace5010008\nTkacenko, E. (2026). Bridging the Data Gap in Aviation by Reconstructing Turnaround Traces with Colored Petri Nets. Bachelor thesis, RWTH Aachen University. Supplied manuscript.\nPrimary source definitions: https://openskynetwork.github.io/opensky-api/rest.html and https://www.eurocontrol.int/concept/airport-collaborative-decision-making\nProject evidence: output/acdm_primary_20261119/summary.json, output/controlled_study_v21/pilot_results.md, promenade/insights_for_thesis.md.';
 return s;
}
function paras(s,items,y=170,size=28,gap=112){items.forEach((v,i)=>text(s,v,72,y+i*gap,1136,gap-16,size));}
function table(s,values,y,widths,height=360,font=25){
 values=values.map(row=>row.map(v=>typeof v==='string'?v.replace(/([a-z])(?=\d)/g,'$1 ').replace(/(\d)(?=[A-Za-z])/g,'$1 '):v));
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:72,top:y,width:1136,height,columnWidths:widths,values});
 t.styleOptions={headerRow:true,bandedRows:false};t.borders.assign({fill:'#D5DFE7',width:1,style:'solid'});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){const cell=t.getCell(r,c);cell.fill=r===0?ink:'#FFFFFF';cell.text.style={typeface:'Arial',fontSize:font,color:r===0?'#FFFFFF':ink,bold:r===0};}
 return t;
}
async function image(s,file,x,y,w,h){s.images.add({path:path.join(root,file),contentType:file.endsWith('.jpg')?'image/jpeg':'image/png',alt:file,fit:'contain',position:{left:x,top:y,width:w,height:h}});}
export async function buildMeeting(p){
 p.slides.delete(p.slides.items.map(s=>s.id));
 let s=slide(p,'Airport turnaround study','Amir Abdelsayed   /   ELTE Data Science MSc','Supervisor:István Koren. Meeting20 November2026. This is the final meeting deck for the stated progress period, not a claim that thesis validation is complete.');
 text(s,'Progress and evidence review',72,220,1120,90,54,true,teal);
 text(s,'12 October–19 November 2026',72,340,1100,60,32);
 text(s,'Professor meeting: 20 November 2026',72,430,1100,60,30);

 s=slide(p,'Work completed in this progress period','Evidence: project reports, prepared data, OCPN outputs and thesis sources','Workstream overview for the requested12Oct–19Nov period. EarlierDSLab1/2 reports provide the starting foundation; do not claim that their historical experiments ran within this period. Evidence:tmp/literature_review/lab1_report.txt,lab2_report.txt; output/controlled_study_v21/validation.json; output/overleaf_update/language_revision_manifest.json.');
 table(s,[['Workstream','Completed output'],['Foundation','Reviewed DS Lab work and the supplied extended model'],['Data','Prepared aircraft pairs and audited A-CDM snapshots'],['Simulation','Adapted demand/timing and completed60 repeated runs'],['Analysis','Inspected OCEL logs in Promenade and tested capacities'],['Writing','Updated thesis, references and English style'] ],170,[260,876],420,25);

 s=slide(p,'Research questions','Source: original research questions in the Overleaf introduction','Exact original RQs remain in the manuscript. RQ1 asks A-CDM calibration of activity durations/dependencies. RQ2 asks dependencies among aircraft,stands,shared resources and waiting/delay propagation at terminal/remote stands. RQ3 asks resource-allocation configurations reducing delay/contention. Predictive accuracy does not replace RQ2.');
 paras(s,['RQ1: Which durations and dependencies can A-CDM support?','RQ2: How do aircraft, stands and shared resources contribute to waiting and delay propagation?','RQ3: Which resource configurations reduce modeled delays and contention?'],180,30,135);

 s=slide(p,'Data provenance and current scope','Source: frozen reconstruction audit and19 November A-CDM audit','output/BER_Combined_Dataset/dataset_manifest.json; output/acdm_primary_20261119/summary.json. The10940rows originate in OpenSky.826core pairs have candidate A-CDM reference links.1322source A-CDM departure records span five snapshots.0complete measured A-CDM landing/block pairs. No numerical relabeling.');
 table(s,[['Dataset','Rows','Role'],['BER A-CDM departures','1,322','Primary empirical observations'],['Eligible actual takeoffs','1,286','Departure analysis cohort'],['Unique OpenSky candidates','1,257','External correspondence check'],['OpenSky aircraft-pair reconstruction','10,940','Separate auxiliary demand pilot'],['Core pairs with A-CDM references','826','Candidate enrichment within pilot'] ],170,[560,140,436],410,24);
 text(s,'The10,940 surveillance-based pairs remain separate from primary A-CDM observations.',72,603,1136,43,24,true,teal);

 s=slide(p,'A-CDM snapshot coverage','Source: data/acdm/days manifests, verified against CSV and JSON','output/acdm_primary_20261119/summary.json. Pagination/source-date snapshots do not establish complete full-day coverage. Dates are separated and sourceSTD timezone contract remains unverified.15canceled+21other records lackeligibleATOT.');
 table(s,[['Source date','Records','Eligible ATOT','OpenSky candidates'],['1 November','289','283','280'],['5 November','257','251','244'],['8 November','264','250','243'],['15 November','254','249','242'],['16 November','258','253','248'],['Total','1,322','1,286','1,257'] ],166,[320,240,260,316],410,25);
 text(s,'Five separated snapshots. Continuous October–November coverage remains unavailable.',72,603,1136,45,24,false,teal);

 s=slide(p,'Milestone meanings','Sources: source-field audit and EUROCONTROL A-CDM documentation','https://www.eurocontrol.int/concept/airport-collaborative-decision-making; data/acdm/prepared/README.md; newprimarysummary. TOBT/TSATvalues are targets,not issue events or actual groundservice execution. ATOT sourceactualtakeoff. ProviderSTD/taxitime semantics and timezone stillneedconfirmation.');
 table(s,[['Field or interval','What the available data support'],['TOBT / TSAT','Departure targets retained as source values'],['ATOT','Recorded actual takeoff'],['ATOT minus TSAT','Takeoff relative to a target approval value'],['Landing, AIBT, AOBT','Absent from the primary departure snapshots'],['Cleaning, fueling, boarding','No observed service start/end timestamps'] ],170,[370,766],410,25);

 s=slide(p,'OpenSky departure cross-check','Source: independently retrieved flight observations and the matching audit','tools/audit_acdm_primary.py; summary.json. Normalizecallsign,testUTCandEurope/Berlinhypotheses,tolerance30min,uniqueonly,noreusedflight.1257/1286=97.74%.1237/1257=98.41%within1minute. Statistics conditional on selected matches. FirstSeen is a surveillanceproxy. No independent registration mapping.');
 text(s,'1,257 of1,286 eligible A-CDM takeoffs have a unique candidate',72,169,1136,86,34,true,teal);
 table(s,[['Matched-subset statistic','Result'],['Within one minute','1,237 of1,257 matches'],['Within five minutes','All1,257 matches'],['Median signed OpenSky minus ATOT','−0.117 min (−7 s)'],['Median absolute difference','0.133 min (8 s)'] ],285,[750,386],285,25);
 text(s,'Agreement supports departure correspondence. Arrival and service accuracy remain untested.',72,603,1136,45,24);

 s=slide(p,'A-CDM departure targets and takeoff','Source: complete eligible TOBT / TSAT / ATOT triples, n=1,283','summary.json target_metrics_complete_triples. Allnegativevaluesretained.1261nonnegative sensitivitycases,22completecasesfailatleastonenonnegativecriterion. Source update history unavailable. Theseare target/actual differences,not taxi/service/wait intervals.');
 table(s,[['Difference in minutes','Mean','Median'],['TSAT minus TOBT','1.30','0.00'],['ATOT minus TSAT','12.58','12.12'],['ATOT minus TOBT','13.88','12.93'] ],180,[620,258,258],270,28);
 text(s,'22 complete records fail a nonnegative-sequence rule and remain available for review.',72,493,1136,80,28);
 text(s,'These intervals do not identify service time or actual resource queueing.',72,594,1136,44,27,true,teal);

 s=slide(p,'Observed object-centric departure log','Source: BER_ACDM_Observed_Departures_UTC_Hypothesis.ocel.json','The log contains1257ActualTakeoff events,2236objects:1257Departure893Aircraft86Stand. A-CDM supplieseventdata. OpenSky selects unique correspondences only. Everyeventtimestamp interpretsnaiveATOTasUTC,supportedempiricallybutprovidercontractunconfirmed. TOBT/TSAT remainattributes. Customintegritychecks,notformalschemavalidation. PromenadeUIimport verification is reported separately.');
 await image(s,'output/acdm_primary_20261119/promenade_acdm_overview.jpg',72,165,800,410);
 text(s,'1,257 takeoff events\n\n2,236 objects\n3 object types\n\nUTC hypothesis explicit',912,185,296,370,28,true,teal);
 text(s,'TOBT / TSAT remain attributes. A single milestone cannot measure full turnaround.',72,601,1136,45,25);

 s=slide(p,'Model attribution and student contribution','Source: preserved professor baseline and study build manifests','IstvánKorenprovidedAirportGroundHandlingExtended. Sourcehashb83e78fbdaa2289c406e359cffc080935bd3ba586bae2f6a1858c77fa8f379d2. Originalbaselineunchanged. tools/build_msc_ocpn.py. Existing simulationusesOpenSkyarrivals. New metadata-onlycopiespreserveexecutablecontent. No A-CDM-only calibration claimed.');
 table(s,[['Inherited baseline','Student study work'],['Six parallel service threads','Finite empirical demand adapter'],['Resource allocation and synchronization','Paired persistent aircraft identities'],['Illustrative geometry and original timings','Transferred narrowbody timing references'],['Extended airport model structure','OCEL checks, Promenade analysis and experiments'] ],180,[568,568],330,26);
 text(s,'The completed simulator is an auxiliary exploratory pilot using OpenSky demand.',72,570,1136,60,28,true,teal);

 s=slide(p,'Service-time assumptions','References: Schultz et al.(2012), Schultz(2018)','SchultzM,KunzeT,OreschkoB,FrickeH2012DynamicTurnaroundManagementinaHighlyAutomatedAirportEnvironment,ICAS https://www.icas.org/icas_archive/ICAS2012/PAPERS/808.PDF. SchultzM2018FastAircraftTurnaroundEnabledbyReliablePassengerBoarding,Aerospace5(1),8 DOI10.3390/aerospace5010008. Transferrednarrowbodyinputs,notBERfits. Boardingdeterministicmean. Engine scale-first. Load85%,PRM0,unknowncarrier remainassumptions.');
 table(s,[['Activity','Narrowbody reference in minutes'],['Cleaning','5 + Weibull(shape2.16, scale6.76)'],['Fueling','2 + Gamma(shape1.64, scale9.12)'],['Boarding','2.3 +0.075 × assumed passengers'] ],180,[300,836],290,29);
 text(s,'No measured service timestamps or justified universal budget/full-service coefficient.',72,520,1136,90,28);

 s=slide(p,'Promenade analysis of the auxiliary pilot','Source: actual Promenade capture from the November1 simulation log','promenade/10_promenade_nov1_block_turnaround.jpg; promenade/insights_for_thesis.md. Threepreviouslogs imported,nov1n27110,288events1247objects,nov8n2389046events1123objects,comparatorn27110298events1255objects. Generatedevents. Directone-to-onepairedTurnaroundmilestonesavoidexpandedcasecontamination. Image is original application capture.');
 await image(s,'promenade/10_promenade_nov1_block_turnaround.jpg',72,165,800,410);
 text(s,'271 paired turnarounds\n\nMean62.33min\nMedian55.62min',912,188,296,320,30,true,teal);
 text(s,'Generated simulation behavior under assumed service and resource inputs',72,601,1136,40,25);

 s=slide(p,'Local queues and final readiness','Source: token-availability analysis of the two literature-timing pilot logs','promenade/resource diagnostics andinsights. Cabinlast230/271and192/238. Fuel21and10,hold20and36. Lastreadybranchdescriptive,notcausalproof. Singlepilotfuelmeans3.785and1.255notrepeatedmeans. Bodyshowscabinsharesonlytoavoidconfusingreplicatedqueuevalues.');
 text(s,'Cabin and boarding finish last in84.9% and80.7% of the two daily pilot cohorts',72,170,1136,110,36,true,teal);
 paras(s,['Fuel dispatch has the clearest local queue, but its waiting can overlap cabin work.','A resource can reduce its queue without substantially changing final turnaround.','The repeated capacity experiments test whether that distinction persists.'],320,29,100);

 s=slide(p,'Controlled experimental design','Source: frozen experiment_plan.json and validation.json','output/controlled_study_v21. Sixscenarios×twodates×fivereplications=60.509uniquecoreintervalsreused=15270generatedexecutions. independentfreshRNGunpaired,seedsnotexposed.95%Welchintervalsforcomparisonsnofamilywisecorrection. Noempiricalpredictivecalibration. Exactdesignbeforeexecutions;interactionaddedexploratoryduringinspection.');
 table(s,[['Design element','Setting'],['Demand dates','1 November and8 November'],['Timing/policy cells','Original/literature crossed with inherited/disabled curfew'],['Capacity cells','6 cleaning teams or6+6 fuel units, literature/disabled'],['Replications','Five per cell,60runs overall'],['Input versus generated cases','509reused intervals,15,270simulated executions'] ],170,[350,786],390,25);
 text(s,'Uncertainty describes Monte Carlo variation under fixed assumptions.',72,603,1136,42,26,true,teal);

 s=slide(p,'Timing effects depend on policy','Source: repeated pilot contrasts, difference in mean block minutes','scenario_contrasts.csv. Literatureminusoriginal:inheritedNov1−24.9956CI−27.4509−22.5403;Nov8−13.5184CI−16.9437−10.0932. DisabledNov1−7.5313CI−8.2390−6.8236;Nov8−7.04094CI−7.61547−6.4664. Fiveunpairedrunspercell. Noaccuracyimprovementorrealpolicycausalityclaim.');
 table(s,[['Literature minus original','1 November','8 November'],['Inherited policy','−25.00 [−27.45,−22.54]','−13.52 [−16.94,−10.09]'],['Disabled curfew','−7.53 [−8.24,−6.82]','−7.04 [−7.62,−6.47]'] ],180,[400,368,368],240,26);
 text(s,'95% Welch intervals across independent replication means',72,453,1136,50,26);
 text(s,'The larger inherited-policy difference cannot establish more accurate service timings.',72,537,1136,85,29,true,teal);

 s=slide(p,'Fuel capacity reduces waiting more than turnaround','Source: repeated literature-timing pilot with curfew disabled','scenario_summary.csv fuel4+4baselineNov1queue3.041697Nov8 2.039552;fuel6+6 .168278and.066275. Blockdelta−.623161CI[−1.225333,−.020989]and−.221513CI[−.792311,.349285]. Conditionalcapacities,notactualBERstaffing. Chartshowsmeansonly;blockintervalsvisibleintext.');
 const ch=s.charts.add('bar',{position:{left:72,top:165,width:660,height:400},titlePlacement:'none',categories:['1 November','8 November'],series:[{name:'8 fuel units',values:[3.042,2.040],fill:teal},{name:'12 fuel units',values:[.168,.066],fill:'#C27A30'}],hasLegend:true,legend:{position:'bottom',textStyle:{typeface:'Arial',fontSize:21}},barOptions:{direction:'column',grouping:'clustered'},xAxis:{textStyle:{typeface:'Arial',fontSize:22}},yAxis:{title:{text:'Mean fuel-dispatch waiting, minutes',textStyle:{typeface:'Arial',fontSize:20}},textStyle:{typeface:'Arial',fontSize:20},numberFormatCode:'0.0'},dataLabels:{showValue:true,numberFormatCode:'0.00',position:'outEnd',textStyle:{typeface:'Arial',fontSize:20}}});
 text(s,'Overall block change\n\nNov1:−0.62min\n95% CI[−1.23,−0.02]\n\nNov8:−0.22min\n95% CI[−0.79,0.35]',785,190,423,350,29);
 text(s,'The November8 overall interval includes zero. Local queue reduction alone is insufficient.',72,588,1136,62,26,true,teal);

 s=slide(p,'Policy and realism limitations','Sources: installed runtime clock probe and official BER night guidance','output/controlled_study_v21/clock_probe.json,policy_review.md. https://corporate.berlin-airport.de/de/nachhaltigkeit/umwelt/fluglaerm/hinweise-zum-nachtflug.html. RuntimehourUTCconfirmed00Zreturns0Berlin1. Inherited00–05UTCbecomes01–06BerlininNov. Helperaffectspreboarding/push,notcompleteeligiblemovementpolicy. Disabledhelperdiagnosticonly.');
 paras(s,['The inherited hour helper uses UTC. Its00:00–05:00 condition becomes01:00–06:00 Berlin local time in November.','The model also applies delays before boarding and pushback clearance. A verified movement-policy model remains necessary.','Fictitious geometry, missing competing traffic and free initial resources limit airport-wide conclusions.','Long parking stays and departure schedules require separate treatment.'],167,28,112);

 s=slide(p,'Current answers to the research questions','Sources: primary audit and separately preserved pilot findings','OriginalRQsremainunchanged. RQ1partialidentifieddeparturecontextmissinginternalservices. RQ2auxbranchreadinessandqueuepartial,terminalremoteandcontrolledinterflightpropagationpending. RQ3conditionalresourceexperimentnotoptimalstaffing. ACDMonlyturnaroundrequiresarrival/blockdata.');
 table(s,[['Question','Supported now','Remaining evidence'],['RQ1','A-CDM departure inputs and external time correspondence','Arrival/block and service timestamps'],['RQ2','Modeled queues and parallel readiness in the auxiliary pilot','Stand comparison and inter-flight propagation'],['RQ3','Repeated conditional capacity comparisons','Broader uncertainty, allocation objective and empirical validation'] ],175,[160,488,488],360,25);

 s=slide(p,'Thesis changes and evidence boundaries','Source: A-CDM primary manuscript revision prepared19 November','Newmainmethods/resultsuseACDM1322andcrosscheck1257. Earlier10940OpenSkycohortand60runsmoveappendicesunchanged. BibliographyincludesSchultz2012/2018Tkacenko2026,softwareprimarydocs. Englishmatchesrequestedclearacademicstylewithoriginalwording. Source-onlylabelcopiesOCPNmetadata no rerunclaimed.');
 paras(s,['Primary chapters: A-CDM source coverage, target-value descriptions and the independent OpenSky departure check.','Appendices: the earlier OpenSky demand reconstruction, OCPN method and all existing Promenade/pilot results.','Preserved results and model behavior. Clear labels distinguish observed data, assumptions and generated events.','The manuscript remains a research draft with explicit unfinished evaluation.'],170,28,110);

 s=slide(p,'Decisions for the next milestone','Source: model-readiness audit and original research objectives','Meetingdecisionpointsratherthanunilateralclaimsfuturevalidationcomplete. KeeporiginalRQscopeunlessprofessorapprovesscopechange. NeedarrivalAIBT/AOBTwithtimezoneverified, terminalremotecontext, modelpolicy. No groundserviceestimationsfromATOT−TSAT.');
 paras(s,['Empirical scope: retain a departure-focused A-CDM study, or obtain arrival/block milestones for full turnaround calibration?','Operational model: confirm local movement policy and stand scope before new realism claims.','Evaluation: agree on separate dates, observable metrics and uncertainty sensitivity.','RQ2 completion: define terminal/remote and delay-propagation experiments.'],170,29,112);

 s=slide(p,'Selected references and reproducible outputs','Meeting20 November2026   /   Supporting citations appear in speaker notes','[1]SchultzM,KunzeT,OreschkoB,FrickeH2012DynamicTurnaroundManagementinaHighlyAutomatedAirportEnvironment.ICAS https://www.icas.org/icas_archive/ICAS2012/PAPERS/808.PDF\n[2]SchultzM2018FastAircraftTurnaroundEnabledbyReliablePassengerBoarding.Aerospace5(1),8 https://doi.org/10.3390/aerospace5010008\n[3]TkacenkoE2026BridgingtheDataGapinAviationbyReconstructingTurnaroundTraceswithColoredPetriNets.Bachelorthesis,RWTHAachen,user-suppliedmanuscript.\n[4]https://www.ocel-standard.org/\n[5]https://openskynetwork.github.io/opensky-api/rest.html\n[6]https://www.eurocontrol.int/concept/airport-collaborative-decision-making\n[7]https://elte-dsed.github.io/ocpn-studio/\n[8]https://app.promenade.run/\n[9]https://corporate.berlin-airport.de/de/nachhaltigkeit/umwelt/fluglaerm/hinweise-zum-nachtflug.html\nProjectfiles:output/acdm_primary_20261119/summary.json;output/controlled_study_v21/pilot_results.md;promenade/insights_for_thesis.md.');
 paras(s,['Schultz et al.(2012): stochastic turnaround management and service-time references.','Schultz(2018): passenger boarding and turnaround reliability.','Tkacenko(2026): turnaround trace reconstruction from sparse observations.','Deliverables: primary A-CDM table, departure cross-check, observed OCEL, pilot models, thesis and experiment archive.'],170,28,112);
 return {slides:p.slides.items.length};
}
