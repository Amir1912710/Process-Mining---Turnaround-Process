"""Aggregate at replication level; intervals never treat flights as independent runs."""
import json,hashlib,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/controlled_study_v21'
plan=json.loads((OUT/'experiment_plan.json').read_text())
df=pd.DataFrame(json.loads((OUT/'replication_results.json').read_text()))
assert len(df)==len(plan['jobs']) and df.complete.all()
assert not df.duplicated(['date','scenario','replication']).any()
for job in plan['jobs']:
    match=df[(df.date==job['date'])&(df.scenario==job['scenario'])&(df.replication==job['replication'])]
    assert len(match)==1
    p=Path(job['model']);assert hashlib.sha256(p.read_bytes()).hexdigest()==match.iloc[0].model_sha256
    m=json.loads(p.with_name(p.stem+'_manifest.json').read_text());assert match.iloc[0].cases==m['cases']
    case=json.loads(Path(job['output']+'_cases.json').read_text());assert len(case)==m['cases'] and len({c['case'] for c in case})==m['cases']
df.to_csv(OUT/'replication_metrics.csv',index=False)
metrics=['mean_block_min','median_block_min','p90_block_min','mean_fuel_wait_min','p90_fuel_wait_min','mean_clean_wait_min','mean_tug_wait_min','long_approval_cases','long_preboard_cases','cabin_last_share']
aggregates=[]
for (date,scenario),g in df.groupby(['date','scenario']):
 for metric in metrics:
    x=g[metric].to_numpy();sd=x.std(ddof=1);half=t.ppf(.975,len(x)-1)*sd/np.sqrt(len(x))
    aggregates.append(dict(date=date,scenario=scenario,metric=metric,replications=len(x),mean=x.mean(),sd_between_runs=sd,ci95_low=x.mean()-half,ci95_high=x.mean()+half,run_min=x.min(),run_max=x.max()))
agg=pd.DataFrame(aggregates);agg.to_csv(OUT/'scenario_summary.csv',index=False)
contrast_specs=[('timing_inherited','literature_inherited','original_inherited'),('timing_no_curfew','literature_no_curfew','original_no_curfew'),('policy_literature','literature_no_curfew','literature_inherited'),('policy_original','original_no_curfew','original_inherited'),('cleaning_capacity','cleaning_6_no_curfew','literature_no_curfew'),('fuel_capacity','fuel_6plus6_no_curfew','literature_no_curfew')]
contrasts=[]
for date,g in df.groupby('date'):
 for name,a,b in contrast_specs:
  for metric in ['mean_block_min','mean_fuel_wait_min']:
    x=g[g.scenario==a][metric].to_numpy();y=g[g.scenario==b][metric].to_numpy();vx=x.var(ddof=1)/len(x);vy=y.var(ddof=1)/len(y);se=np.sqrt(vx+vy)
    dof=(vx+vy)**2/(vx*vx/(len(x)-1)+vy*vy/(len(y)-1)) if se else np.inf
    half=t.ppf(.975,dof)*se if se else 0
    delta=x.mean()-y.mean()
    contrasts.append(dict(date=date,contrast=name,scenario_a=a,scenario_b=b,metric=metric,difference_a_minus_b=delta,ci95_low=delta-half,ci95_high=delta+half,method='Unpaired Welch t interval; exploratory, no multiplicity adjustment'))
con=pd.DataFrame(contrasts);con.to_csv(OUT/'scenario_contrasts.csv',index=False)
interactions=[]
for date,g in df.groupby('date'):
 specs=[('literature_inherited',1),('original_inherited',-1),('literature_no_curfew',-1),('original_no_curfew',1)]
 estimate=0;variances=[]
 for scenario,sign in specs:
    x=g[g.scenario==scenario].mean_block_min.to_numpy();estimate+=sign*x.mean();variances.append((x.var(ddof=1)/len(x),len(x)-1))
 variance=sum(v for v,n in variances);dof=variance**2/sum(v*v/n for v,n in variances);half=t.ppf(.975,dof)*np.sqrt(variance)
 interactions.append(dict(date=date,interaction_minutes=estimate,ci95_low=estimate-half,ci95_high=estimate+half,definition='(literature-original under inherited policy) minus (literature-original with curfew disabled)',interpretation='Additional exploratory contrast; conditional interaction in model output'))
pd.DataFrame(interactions).to_csv(OUT/'timing_policy_interaction.csv',index=False)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
dates=sorted(df.date.unique());colors=['#16858a','#c47a39','#6d68b0','#529144']
def finish(fig,name,caption):
 fig.text(.02,.015,caption,fontsize=8,color='#555');fig.tight_layout(rect=(0,.06,1,.95));fig.savefig(OUT/(name+'.png'),dpi=220,bbox_inches='tight');plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(12,5.8))
order=['original_inherited','literature_inherited','original_no_curfew','literature_no_curfew'];labels=['Original\ninherited policy','Literature\ninherited policy','Original\nno curfew','Literature\nno curfew']
for ax,date in zip(axs,dates):
 for i,s in enumerate(order):
    vals=df[(df.date==date)&(df.scenario==s)].mean_block_min.to_numpy();r=agg[(agg.date==date)&(agg.scenario==s)&(agg.metric=='mean_block_min')].iloc[0]
    ax.bar(i,r['mean'],color=colors[i],alpha=.7,width=.65);ax.errorbar(i,r['mean'],yerr=r.ci95_high-r['mean'],fmt='none',color='#222',capsize=4);ax.scatter(i+np.linspace(-.10,.10,len(vals)),vals,color='#222',s=20,zorder=3)
 ax.set(title=date,ylabel='Mean simulated block turnaround (minutes)',ylim=(0,100),xticks=range(4),xticklabels=labels);ax.grid(axis='y',alpha=.2);ax.tick_params(axis='x',labelsize=8)
fig.suptitle('Timing and inherited policy: five independent runs per scenario',fontsize=14)
finish(fig,'01_timing_policy_replications','SIMULATION PILOT • Dots = run means; bars/95% t intervals describe simulation sampling variation only. No-curfew is an assumption sensitivity.')
fig,axs=plt.subplots(1,2,figsize=(12,5.7));order=['literature_no_curfew','cleaning_6_no_curfew','fuel_6plus6_no_curfew'];labels=['9 cleaning teams\n4 + 4 fuel units','6 cleaning teams\n4 + 4 fuel units','9 cleaning teams\n6 + 6 fuel units']
for ax,metric,title in zip(axs,['mean_block_min','mean_fuel_wait_min'],['Overall turnaround','Fuel dispatch queue']):
 for j,date in enumerate(dates):
    centers=np.arange(3)+(j-.5)*.32;rs=[agg[(agg.date==date)&(agg.scenario==s)&(agg.metric==metric)].iloc[0] for s in order]
    ax.bar(centers,[r['mean'] for r in rs],width=.30,color=colors[j],label=date);ax.errorbar(centers,[r['mean'] for r in rs],yerr=[r.ci95_high-r['mean'] for r in rs],fmt='none',color='#222',capsize=4)
 ax.set(title=title,ylabel='Mean minutes per run',xticks=range(3),xticklabels=labels);ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2);ax.tick_params(axis='x',labelsize=8)
fig.suptitle('Resource effects with literature timings and curfew disabled',fontsize=14)
finish(fig,'02_resource_sensitivity_replications','SIMULATION PILOT • Five runs/cell, 95% t intervals. Assumed capacities; no real BER staffing recommendation.')
fig,axs=plt.subplots(1,2,figsize=(12,5.5))
for ax,date in zip(axs,dates):
 for i,(name,label) in enumerate([('timing_no_curfew','Literature − original timing'),('cleaning_capacity','6 − 9 cleaning teams'),('fuel_capacity','6+6 − 4+4 fuel units')]):
    r=con[(con.date==date)&(con.contrast==name)&(con.metric=='mean_block_min')].iloc[0]
    ax.errorbar(r.difference_a_minus_b,i,xerr=[[r.difference_a_minus_b-r.ci95_low],[r.ci95_high-r.difference_a_minus_b]],fmt='o',color=colors[i],capsize=4)
 ax.axvline(0,color='#777',ls='--',lw=1);ax.set(title=date,yticks=range(3),yticklabels=['Literature − original timing','6 − 9 cleaning teams','6+6 − 4+4 fuel units'],xlabel='Difference in mean simulated block turnaround (min)');ax.grid(axis='x',alpha=.2)
fig.suptitle('Exploratory scenario contrasts, with curfew disabled',fontsize=14)
finish(fig,'03_controlled_contrasts','Independent-run Welch 95% intervals • Not paired random seeds • Conditional on all remaining model assumptions • No multiple-comparison correction.')
checks={'replications_completed':len(df),'scenario_date_cells':int(df.groupby(['date','scenario']).ngroups),'turnaround_executions':int(df.cases.sum()),'all_completed':bool(df.complete.all()),'all_model_hashes_match':True,'all_case_counts_unique_and_complete':True,'baseline_original_sha256':hashlib.sha256(Path(r'C:\Users\amira\Desktop\ELTE\Thesis\airport-extended.ocpn').read_bytes()).hexdigest()}
assert checks['baseline_original_sha256']=='b83e78fbdaa2289c406e359cffc080935bd3ba586bae2f6a1858c77fa8f379d2'
(OUT/'validation.json').write_text(json.dumps(checks,indent=2))
def table(frame):
 cols=list(frame.columns)
 lines=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
 for _,row in frame.iterrows():lines.append('| '+' | '.join(f'{v:.2f}' if isinstance(v,(float,np.floating)) else str(v) for v in row)+' |')
 return '\n'.join(lines)
main=agg[agg.metric=='mean_block_min'][['date','scenario','mean','ci95_low','ci95_high']].rename(columns={'mean':'Mean block minutes','ci95_low':'95% lower','ci95_high':'95% upper'})
effects=con[con.metric=='mean_block_min'][['date','contrast','difference_a_minus_b','ci95_low','ci95_high']].rename(columns={'difference_a_minus_b':'Difference minutes','ci95_low':'95% lower','ci95_high':'95% upper'})
interaction_table=pd.DataFrame(interactions)[['date','interaction_minutes','ci95_low','ci95_high']]
resource=agg[agg.metric.isin(['mean_fuel_wait_min','mean_clean_wait_min','mean_tug_wait_min'])][['date','scenario','metric','mean']]
report=f'''# Controlled simulation pilot — v2.1

Completed {len(df)} independent replications across {checks['scenario_date_cells']} date/scenario cells: five runs per cell, on November 1 and November 8, 2026. All {checks['turnaround_executions']:,} simulated turnaround executions completed and passed case/aircraft/resource-return checks. These executions reuse **509 empirical interval cases**, not {checks['turnaround_executions']:,} new observed turnarounds. This is not a full-period simulation.

## Design

The design was fixed before these new runs, informed by the earlier exploratory results. It is a pilot, not an independently preregistered confirmatory study. Four cells per date cross original/literature service-time functions with inherited/disabled curfew. Two additional cells vary cleaning teams from 9 to 6 or fueling units from 4 hydrants + 4 tankers to 6 + 6, under literature timings and disabled curfew. Arrival demand, aircraft identities, passenger-load assumption and remaining model logic are held constant within each date.

Model files are in `models/`; exact settings and hashes are in companion manifests. `experiment_plan.json` specifies all runs. The original professor model and the previously analyzed package remain unchanged. The no-curfew models are sensitivity scenarios, not realistic BER replacements.

## Mean simulated in-block to off-block duration

{table(main)}

Intervals are Student-t 95% confidence intervals for the mean of **five replication-level means**. They describe Monte Carlo variability conditional on the fixed input/model assumptions. They do not quantify uncertainty in passenger loads, measured input proxies, service distributions, airport capacities or model structure. Negative lower endpoints, if any, are mathematical interval estimates and not feasible negative durations.

## Exploratory differences between scenarios

{table(effects)}

Each difference is scenario A minus B, as specified in `scenario_contrasts.csv`. Timing contrasts mean literature minus original; policy contrasts mean disabled minus inherited; cleaning means 6 minus 9 teams; fueling means 6+6 minus 4+4 units. Negative values indicate shorter simulated block turnaround. Welch 95% intervals use independent runs, with no paired seeds and no multiple-comparison adjustment. An interval crossing zero means this pilot does not resolve the direction under that comparison. An interval excluding zero is still conditional model evidence, not an empirical BER causal finding.

The additional exploratory timing-by-policy interaction is the literature-minus-original difference under inherited policy, minus that difference with curfew disabled. A negative estimate means the apparent literature timing benefit is larger under the inherited policy. This contrast was added while inspecting the pilot, and is not a preregistered confirmatory test.

{table(interaction_table)}

## Mean waiting times

{table(resource)}

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
'''
(OUT/'pilot_results.md').write_text(report,encoding='utf-8')
with zipfile.ZipFile(ROOT/'output/Controlled_Study_v21.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in OUT.rglob('*'):
  if p.is_file() and not p.name.startswith('smoke_') and not p.name.endswith('_progress.json'):z.write(p,p.relative_to(ROOT/'output'))
 for name in ['build_msc_ocpn.py','run_controlled_ocpn.mjs','run_controlled_study.py','summarize_controlled_study.py']:z.write(ROOT/'tools'/name,'tools/'+name)
print(json.dumps(checks));print(con[con.metric=='mean_block_min'][['date','contrast','difference_a_minus_b','ci95_low','ci95_high']].to_string(index=False))
