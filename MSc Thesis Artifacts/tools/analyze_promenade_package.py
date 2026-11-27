"""Reproducible supplementary calculations from the exact Promenade input exports."""
import csv,json,collections
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'promenade';OUT.mkdir(exist_ok=True)
SOURCE=ROOT/'output/ocpn'
VARIANTS={'2026-11-01':'Nov 1 / literature','2026-11-08':'Nov 8 / literature','timing_baseline':'Nov 1 / original timings'}
def cases_in(v):
    found=set()
    def walk(x):
        if isinstance(x,dict):
            if isinstance(x.get('studyCase'),str):found.add(x['studyCase'])
            for y in x.values():walk(y)
        elif isinstance(x,list):
            for y in x:walk(y)
    walk(v);return found
frames=[];details={}
for variant,label in VARIANTS.items():
    stem=SOURCE/('BER_MSc_'+variant)
    ev=json.loads(stem.with_name(stem.name+'_run_events.json').read_text())
    bycase=collections.defaultdict(lambda:collections.defaultdict(list))
    for e in ev:
        for case in cases_in([e['consumed'],e['produced']]):bycase[case][e['transitionId']].append(e['simulationTime'])
    inp=pd.read_csv(stem.with_name(stem.name+'_cases.csv'))
    rows=[]
    for _,c in inp.iterrows():
        events=bycase[c.study_case_id]
        def at(*keys):
            vals=[t for key in keys for t in events[key]]
            return min(vals) if vals else np.nan
        r={'variant':variant,'label':label,'case':c.study_case_id,'aircraft':c.model_aircraft_id,'model_type':c.model_type,'observed_proxy_min':c.ground_interval_proxy_min,'planned_arrival_ms':c.model_release_ms}
        points={'release':'s-t-file','inblock':'a-t-inblock','handling_start':'t-aght','handling_complete':'t-joined','ready':'d-t-ardt','offblock':'d-t-push-start','takeoff':'d-t-takeoff','clean_start':'c-t-clean-start','clean_end':'c-t-clean-end','fuel_start':'r-t-fuel-start','fuel_end':'r-t-fuel-end','tug_attach':'d-t-tug-attach','startup_approved':'d-t-asat'}
        r.update({name:at(key) for name,key in points.items()})
        r['deboard_end']=at('c-t-deb-bridge-end','c-t-deb-bus-end')
        r['board_start']=at('c-t-board-bridge','c-t-board-bus');r['board_end']=at('c-t-board-bridge-end','c-t-board-bus-end')
        r['fuel_dispatch']=at('r-t-fuel-hyd','r-t-fuel-tnk')
        r['remote']=bool(events['c-t-board-bus'])
        for name,end,start in [('sim_block_min','offblock','inblock'),('sim_proxy_min','takeoff','planned_arrival_ms'),('release_to_takeoff_min','takeoff','release'),('clean_access_service_min','clean_end','clean_start'),('fuel_service_min','fuel_end','fuel_start'),('boarding_access_service_min','board_end','board_start'),('clean_wait_min','clean_start','deboard_end'),('fuel_dispatch_wait_min','fuel_dispatch','handling_start'),('fuel_access_min','fuel_start','fuel_dispatch'),('tug_wait_min','tug_attach','ready'),('approval_to_offblock_min','offblock','startup_approved'),('clean_end_to_board_start_min','board_start','clean_end'),('arrival_release_delay_min','release','planned_arrival_ms'),('handling_min','handling_complete','handling_start')]:
            r[name]=(r[end]-r[start])/60000
        r['proxy_error_min']=r['sim_proxy_min']-r['observed_proxy_min']
        rows.append(r)
    df=pd.DataFrame(rows);frames.append(df)
    df.to_csv(OUT/(variant+'_case_metrics.csv'),index=False)
allrows=pd.concat(frames,ignore_index=True)
metrics=['sim_block_min','sim_proxy_min','observed_proxy_min','clean_access_service_min','fuel_service_min','boarding_access_service_min','clean_wait_min','fuel_dispatch_wait_min','tug_wait_min','approval_to_offblock_min','clean_end_to_board_start_min','arrival_release_delay_min','handling_min','proxy_error_min']
summary=[]
for label,df in allrows.groupby('label',sort=False):
    for m in metrics:
        v=df[m].dropna();summary.append({'scenario':label,'metric':m,'n':len(v),'mean':v.mean(),'median':v.median(),'p90':v.quantile(.9),'p95':v.quantile(.95),'max':v.max()})
pd.DataFrame(summary).to_csv(OUT/'summary_metrics.csv',index=False)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
colors=['#16858a','#6d68b0','#c47a39']
def finish(fig,name,caption):
    fig.text(.02,.015,'SIMULATION RESULTS • One stochastic run per scenario • '+caption,fontsize=8,color='#555')
    fig.tight_layout(rect=(0,.055,1,.97));fig.savefig(OUT/(name+'.png'),dpi=220,bbox_inches='tight');plt.close(fig)
fig,ax=plt.subplots(figsize=(10,5.4))
for df,col in zip(frames,colors):
    x=np.sort(df.sim_block_min);ax.plot(x,np.arange(1,len(x)+1)/len(x),label=df.label.iloc[0],color=col,lw=2)
ax.set(xlabel='Simulated in-block → off-block (minutes)',ylabel='Cumulative share of turnarounds',title='Turnaround distributions under alternative timing assumptions');ax.legend();ax.grid(alpha=.2)
finish(fig,'01_simulated_turnaround_comparison','Descriptive comparison; no causal or significance claim.')
fig,axs=plt.subplots(1,3,figsize=(13,4.8))
for ax,metric,title in zip(axs,['clean_access_service_min','fuel_service_min','boarding_access_service_min'],['Cleaning + vehicle access','Refueling service','Boarding + remote bus access']):
    ax.boxplot([d[metric].dropna() for d in frames],tick_labels=['Nov 1\nliterature','Nov 8\nliterature','Nov 1\noriginal'],showfliers=False);ax.set(title=title,ylabel='Minutes');ax.grid(axis='y',alpha=.2)
fig.suptitle('Service-time changes are uneven across parallel handling activities',fontsize=14)
finish(fig,'02_service_duration_comparison','Outliers hidden only in boxplot display; retained in tables.')
fig,ax=plt.subplots(figsize=(10,5.5))
for i,(metric,name) in enumerate([('clean_wait_min','Cleaning resource wait*'),('fuel_dispatch_wait_min','Fuel dispatch wait'),('tug_wait_min','Pushback tug wait')]):
    ax.bar(np.arange(3)+(i-1)*.24,[d[metric].mean() for d in frames],width=.24,label=name)
ax.set(xticks=np.arange(3),xticklabels=[d.label.iloc[0] for d in frames],ylabel='Mean elapsed minutes',title='Resource waiting exposes targets for conditional RQ3 experiments');ax.legend();ax.grid(axis='y',alpha=.2)
finish(fig,'03_resource_waiting','*Cleaning wait measured from deplaning completion; excludes cleaning duration.')
fig,axs=plt.subplots(1,2,figsize=(12,5.2))
for df,col in zip(frames[:2],colors):
    axs[0].scatter(df.observed_proxy_min,df.sim_proxy_min,s=14,alpha=.55,label=df.label.iloc[0],color=col)
axs[0].plot([0,1440],[0,1440],'--',color='#777',lw=1);axs[0].set(xlabel='Observed airborne-boundary interval proxy (min)',ylabel='Simulated planned-arrival → takeoff (min)',title='Boundary proxy comparison');axs[0].legend(fontsize=9)
short=frames[0][frames[0].observed_proxy_min<=360]
axs[1].scatter(short.observed_proxy_min,short.sim_proxy_min,s=18,color=colors[0],alpha=.6);axs[1].plot([0,360],[0,360],'--',color='#777',lw=1);axs[1].set(xlabel='Observed proxy ≤ 6 h (min)',ylabel='Simulated proxy (min)',title='Nov 1: short ground-interval cohort')
finish(fig,'04_observed_proxy_vs_simulation','OpenSky proxies are not block times; disagreement does not identify internal services.')
fig,axs=plt.subplots(1,2,figsize=(12,5.2))
for df,col in zip(frames,colors):
    axs[0].hist(df.approval_to_offblock_min,bins=np.arange(0,361,15),histtype='step',lw=2,label=df.label.iloc[0],color=col)
axs[0].set(xlabel='Start-up approval → off-block (min)',ylabel='Turnarounds',title='Long tail can include an inherited curfew rule');axs[0].legend(fontsize=9)
axs[1].bar(np.arange(3)-.18,[(d.approval_to_offblock_min>30).sum() for d in frames],width=.36,label='Approval → off-block');axs[1].bar(np.arange(3)+.18,[(d.clean_end_to_board_start_min>30).sum() for d in frames],width=.36,label='Cleaning end → boarding start');axs[1].set(xticks=np.arange(3),xticklabels=[d.label.iloc[0] for d in frames],ylabel='Cases with interval > 30 minutes',title='Inspect inherited policy before BER interpretation');axs[1].tick_params(axis='x',labelsize=8);axs[1].legend(fontsize=8)
finish(fig,'05_inherited_policy_diagnostic','Model e106 and e191 retain curfew_delay; these are not verified BER night restrictions.')
fig,ax=plt.subplots(figsize=(10,5.5))
for df,col in zip(frames,colors):
    x=np.sort(df.arrival_release_delay_min);ax.plot(x,np.arange(1,len(x)+1)/len(x),label=df.label.iloc[0],lw=2,color=col)
ax.set(xlabel='Planned arrival input → actual simulated release (min)',ylabel='Cumulative share',title='Aircraft reuse can delay arrival release inside the model');ax.legend();ax.grid(alpha=.2)
finish(fig,'06_aircraft_identity_release_delay','Positive delay reflects simulated availability, not measured inbound flight delay.')
diagnostics=[]
for d in frames:
    diagnostics.append({'scenario':d.label.iloc[0],'n':len(d),'remote_cases':int(d.remote.sum()),'release_delayed_gt1min':int((d.arrival_release_delay_min>1).sum()),'approval_to_offblock_gt30min':int((d.approval_to_offblock_min>30).sum()),'clean_end_to_board_start_gt30min':int((d.clean_end_to_board_start_min>30).sum()),'proxy_mae_min':float(d.proxy_error_min.abs().mean()),'proxy_bias_min':float(d.proxy_error_min.mean())})
(OUT/'diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
print(json.dumps(diagnostics,indent=2))
print(pd.DataFrame(summary).query("metric in ['sim_block_min','clean_wait_min','fuel_dispatch_wait_min','tug_wait_min']").to_string(index=False))
