"""Supplementary resource/case analysis with event and object deduplication."""
from pathlib import Path
import json,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'promenade'
log=json.loads((ROOT/'output/ocpn/BER_MSc_2026-11-01.ocel.json').read_text())
objects={o['id']:o for o in log['objects']}
assigned={typ:collections.defaultdict(set) for typ in ['CleaningTeam','Fueller']}
for e in log['events']:
    rel={r['objectId'] for r in e['relationships']}
    cases={i for i in rel if objects[i]['type']=='Turnaround'}
    for i in rel:
        typ=objects[i]['type']
        if typ in assigned:assigned[typ][i].update(cases)
fig,axs=plt.subplots(1,2,figsize=(12,5))
for ax,(typ,d) in zip(axs,assigned.items()):
    pairs=sorted(((k.split('_',1)[1],len(v)) for k,v in d.items()))
    ax.bar([k for k,v in pairs],[v for k,v in pairs],color='#16858a');ax.set(title=typ,ylabel='Distinct turnarounds served');ax.tick_params(axis='x',rotation=45);ax.grid(axis='y',alpha=.2)
fig.suptitle('Shared-resource workload in the November 1 simulation',fontsize=14)
fig.text(.02,.015,'SIMULATION RESULTS • Distinct turnaround/resource pairs; workload count is not time utilization.',fontsize=8,color='#555')
fig.tight_layout(rect=(0,.07,1,.94));fig.savefig(OUT/'06a_shared_resource_workload.png',dpi=220,bbox_inches='tight');plt.close(fig)
branch={'c-t-doors':'Cabin / boarding','r-t-load-end':'Baggage hold','r-t-fuel-end':'Fuel','r-t-lav-end':'Water / lavatory','r-t-water-skip':'Water / lavatory','c-t-cater-end':'Catering','c-t-cater-skip':'Catering','d-t-tsat':'Departure planning'}
rows=[];stats=[]
for variant,label in [('2026-11-01','Nov 1 / literature'),('2026-11-08','Nov 8 / literature'),('timing_baseline','Nov 1 / original timings')]:
    ev=json.loads((ROOT/f'output/ocpn/BER_MSc_{variant}_run_events.json').read_text());completion=collections.defaultdict(list)
    for e in ev:
        if e['transitionId'] not in branch:continue
        for tok in e['produced'].get('p-thread-done',[]):
            value=tok.get('value',tok);case=value.get('id')
            if case:completion[case].append((tok.get('timestamp',e['simulationTime']),branch[e['transitionId']]))
    counts=collections.Counter()
    for case,times in completion.items():
        assert len(times)==6,(case,len(times))
        latest=max(t for t,b in times);last={b for t,b in times if t==latest}
        for b in last:counts[b]+=1/len(last)
        rows.append({'scenario':label,'turnaround':case,'last_ready_branch':' + '.join(sorted(last)),'ready_at_ms':latest})
    stats.append((label,counts))
pd.DataFrame(rows).to_csv(OUT/'last_ready_branch_by_case.csv',index=False)
fig,ax=plt.subplots(figsize=(10,5.5));labels=[s for s,c in stats];bottom=[0.0]*3
for branchname in ['Cabin / boarding','Fuel','Baggage hold','Water / lavatory','Catering','Departure planning']:
    values=[c[branchname] for _,c in stats]
    if not sum(values):continue
    ax.bar(labels,values,bottom=bottom,label=branchname);bottom=[b+v for b,v in zip(bottom,values)]
ax.set(title='Which handling branch becomes ready last?',ylabel='Turnarounds (ties divided equally)');ax.legend(fontsize=9,loc='upper right');ax.grid(axis='y',alpha=.2)
fig.text(.02,.015,'SIMULATION RESULTS • Last branch ready at the handling join; this is not a causal bottleneck attribution.',fontsize=8,color='#555')
fig.tight_layout(rect=(0,.06,1,1));fig.savefig(OUT/'06b_last_ready_handling_branch.png',dpi=220,bbox_inches='tight');plt.close(fig)
print(json.dumps([(label,dict(c)) for label,c in stats],indent=2))
