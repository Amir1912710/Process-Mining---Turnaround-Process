"""Freeze a bounded pilot design, build versioned models, run independent replications."""
import argparse,concurrent.futures,contextlib,io,json,subprocess,time,hashlib
from pathlib import Path
from build_msc_ocpn import build
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/controlled_study_v21'
SCENARIOS=[
 ('literature_inherited',dict(timing='literature',curfew='inherited')),
 ('original_inherited',dict(timing='baseline',curfew='inherited')),
 ('literature_no_curfew',dict(timing='literature',curfew='none')),
 ('original_no_curfew',dict(timing='baseline',curfew='none')),
 ('cleaning_6_no_curfew',dict(timing='literature',curfew='none',cleaning_teams=6)),
 ('fuel_6plus6_no_curfew',dict(timing='literature',curfew='none',hydrant_dispensers=6,fuel_tankers=6)),
]
def main(reps=5,workers=2,smoke=False):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'runs').mkdir(exist_ok=True)
 plan={'design':'Pilot fixed before new simulation results; two dates, six scenarios, five independent replications per cell. No parameter fitting.','dates':['2026-11-01','2026-11-08'],'replications':reps,'max_steps':18000,'randomization':'Runtime RNG; seeds not exposed; independent unpaired replications, not common random numbers.','interpretation':'Disabled curfew is a policy sensitivity, not verified BER law. Capacities and passenger loads are assumed.','jobs':[]}
 if smoke:plan['dates']=['2026-11-01']
 for date in plan['dates']:
  for name,options in SCENARIOS:
   with contextlib.redirect_stdout(io.StringIO()):
    model=build(date=date,limit=3 if smoke else None,suffix=date+'_'+name,out_dir=OUT/'models',**options)
   for r in range(1,reps+1):plan['jobs'].append(dict(date=date,scenario=name,replication=r,model=str(model),output=str(OUT/'runs'/f'{date}_{name}_r{r:02d}')))
 planfile=OUT/('smoke_plan.json' if smoke else 'experiment_plan.json');planfile.write_text(json.dumps(plan,indent=2))
 print('Frozen design:',len(plan['jobs']),'replications;',planfile,flush=True)
 def run(index):
  job=plan['jobs'][index]; result=subprocess.run(['node',str(ROOT/'tools/run_controlled_ocpn.mjs'),str(planfile),str(index)],cwd=ROOT,capture_output=True,text=True)
  if result.returncode:raise RuntimeError(f'{job}: {result.stderr[-2000:]}')
  return json.loads(result.stdout.splitlines()[-1])
 completed=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
  futures=[pool.submit(run,i) for i in range(len(plan['jobs']))]
  for fut in concurrent.futures.as_completed(futures):
   s=fut.result();completed.append(s)
   (OUT/'progress.json').write_text(json.dumps({'completed':len(completed),'total':len(futures),'last':s},indent=2))
   print(json.dumps({'completed':len(completed),'total':len(futures),'date':s['date'],'scenario':s['scenario'],'rep':s['replication'],'mean_block':round(s['mean_block_min'],2),'seconds':round(s['elapsed_seconds'],1)}),flush=True)
 (OUT/('smoke_results.json' if smoke else 'replication_results.json')).write_text(json.dumps(completed,indent=2))
 print('All replications completed and passed integrity checks.',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--reps',type=int,default=5);p.add_argument('--workers',type=int,default=2);p.add_argument('--smoke',action='store_true');a=p.parse_args();main(a.reps,a.workers,a.smoke)
