"""RQ1 calibration of the carrier-specific service times against observed A-CDM targets.

For linked turnarounds (A-CDM departure linked to an OpenSky arrival of the same aircraft) the observed
target turnaround time TTA = TOBT - landing proxy is compared with the simulated arrival-to-ready time
(release -> Aircraft Ready) of the same case. Two multipliers (low-cost incl. leisure, full-service) scale the
narrow-body service times. Grid search on calibration days (1 and 5 Nov), validation on the held-out day (8 Nov).
Loss: mean absolute difference of the 25th/50th/75th percentiles, averaged over both carrier classes.
"""
import concurrent.futures, contextlib, csv, io, itertools, json, subprocess, sys
from pathlib import Path
import numpy as np
from build_msc_ocpn import build, ENRICHED

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/calibration_v3'; (OUT / 'runs').mkdir(parents=True, exist_ok=True); (OUT / 'models').mkdir(exist_ok=True)
ACDM = ROOT / 'output/acdm_primary_20261119/ACDM_Berlin_Primary_With_OpenSky_Check.csv'
COMMON = dict(context='enriched', weather='observed', curfew='ber_local', schedule='std', timing='carrier')
GRID = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
CAL_DAYS, VAL_DAYS = ['2026-11-01', '2026-11-05'], ['2026-11-08']
Q = [25, 50, 75]


def observed():
    acdm = {r['record_key']: r for r in csv.DictReader(ACDM.open(encoding='utf-8-sig'))}
    return acdm


def run_jobs(jobs, planfile, workers=7):
    planfile.write_text(json.dumps({'max_steps': 60000, 'jobs': jobs}, indent=2))
    def run(i):
        r = subprocess.run(['node', str(ROOT / 'tools/run_controlled_ocpn.mjs'), str(planfile), str(i)], cwd=ROOT, capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr[-1000:])
        return i
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for n, _ in enumerate(pool.map(run, range(len(jobs))), 1):
            if n % 10 == 0: print('done', n, 'of', len(jobs), flush=True)


def tta_pairs(job, acdm):
    """Return {class: (observed TTA list, simulated release->ready list)} for linked cases of one run."""
    cases = {c['case']: c for c in json.loads(Path(job['output'] + '_cases.json').read_text())}
    obs, sim = {'low': [], 'full': []}, {'low': [], 'full': []}
    for r in csv.DictReader(Path(job['model'].replace('.ocpn', '_cases.csv')).open(encoding='utf-8-sig')):
        a = acdm.get(r.get('acdm_reference_key') or '')
        if not a or a.get('usable_target_takeoff_pairs') != 'True' or float(r['ground_interval_proxy_min']) >= 360: continue
        c = cases.get(r['study_case_id'])
        if not c: continue
        rel = int(r['model_release_ms']) / 60000; std = int(r['model_std_ms']) / 60000
        if not std: continue
        tobt = std + float(a['tobt_minus_std_min'])
        k = r['model_carrier_type']
        obs[k].append(tobt - rel); sim[k].append(c['release_to_ready_min'])
    return obs, sim


def loss(obs, sim):
    ls = []
    for k in ('low', 'full'):
        if len(obs[k]) >= 10:
            ls.append(np.mean(np.abs(np.percentile(sim[k], Q) - np.percentile(obs[k], Q))))
    return float(np.mean(ls))


def main():
    acdm = observed(); jobs = []
    for d in CAL_DAYS:
        for sl, sf in itertools.product(GRID, GRID):
            name = f'{d}_low{sl}_full{sf}'
            with contextlib.redirect_stdout(io.StringIO()):
                m = build(date=d, suffix=name, out_dir=OUT / 'models', scale_low=sl, scale_full=sf, **COMMON)
            jobs.append(dict(date=d, scenario=f'low{sl}_full{sf}', sl=sl, sf=sf, replication=1, model=str(m), output=str(OUT / 'runs' / name)))
    run_jobs(jobs, OUT / 'grid_plan.json')
    grid = {}
    for j in jobs:
        o, s = tta_pairs(j, acdm); key = (j['sl'], j['sf'])
        g = grid.setdefault(key, {'obs': {'low': [], 'full': []}, 'sim': {'low': [], 'full': []}})
        for k in ('low', 'full'): g['obs'][k] += o[k]; g['sim'][k] += s[k]
    table = sorted(((loss(g['obs'], g['sim']), k) for k, g in grid.items()))
    best = table[0][1]; print('best', best, 'loss', round(table[0][0], 2), 'uncalibrated (1,1)', round(loss(grid[(1.0, 1.0)]['obs'], grid[(1.0, 1.0)]['sim']), 2))
    # validation on held-out day: uncalibrated vs calibrated, plus literature/original references from study_v3 if present
    vjobs = []
    for d in VAL_DAYS:
        for sl, sf in [(1.0, 1.0), best]:
            name = f'{d}_low{sl}_full{sf}_val'
            with contextlib.redirect_stdout(io.StringIO()):
                m = build(date=d, suffix=name, out_dir=OUT / 'models', scale_low=sl, scale_full=sf, **COMMON)
            vjobs.append(dict(date=d, scenario=f'val_low{sl}_full{sf}', sl=sl, sf=sf, replication=1, model=str(m), output=str(OUT / 'runs' / name)))
    run_jobs(vjobs, OUT / 'validation_plan.json')
    val = {}
    for j in vjobs:
        o, s = tta_pairs(j, acdm)
        val[j['scenario']] = {'loss': round(loss(o, s), 2), **{f'{k}_n': len(o[k]) for k in o},
                              **{f'{k}_obs_q': np.round(np.percentile(o[k], Q), 1).tolist() for k in o},
                              **{f'{k}_sim_q': np.round(np.percentile(s[k], Q), 1).tolist() for k in o}}
    res = {'grid': [{'scale_low': k[0], 'scale_full': k[1], 'loss': round(l, 3)} for l, k in table], 'best': best, 'validation': val}
    (OUT / 'calibration_results.json').write_text(json.dumps(res, indent=2))
    print(json.dumps(val, indent=1))


if __name__ == '__main__':
    main()
