"""RQ3 what-if study on the calibrated carrier-specific model, all 41 days, one trace-driven run per day.

Scenarios share demand, weather, policy and calibrated service times; each changes one lever.
Comparison unit: the operational day (paired differences across 41 days, Student-t intervals).
"""
import concurrent.futures, contextlib, csv, io, json, subprocess, sys
from pathlib import Path
from build_msc_ocpn import build, ENRICHED

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/whatif_v4'
cal = json.loads((ROOT / 'output/calibration_v4/calibration_results.json').read_text())
SL, SF = cal['best']
BASE = dict(context='enriched', weather='observed', curfew='ber_local', schedule='std', timing='carrier', leisure_profile='full', scale_low=SL, scale_full=SF, baggage='carrier')
SCEN = {
    'calibrated_base': {},
    'fuel_6plus6': dict(hydrant_dispensers=6, fuel_tankers=6),
    'buses_12': dict(buses=12),
    'loaders_24': dict(loaders=24),
    'boarding_minus15': dict(board_scale=0.85),
    'lcc_remote_stands': dict(stand_policy='lcc_remote'),
}


def main(workers=7, only=None):
    (OUT / 'runs').mkdir(parents=True, exist_ok=True); (OUT / 'models').mkdir(exist_ok=True)
    days = sorted({r['inbound_last_seen_berlin'][:10] for r in csv.DictReader(ENRICHED.open(encoding='utf-8-sig')) if r['in_scope'] == 'True'})
    jobs = []
    for d in days:
        for name, opt in SCEN.items():
            if only and name not in only: continue
            with contextlib.redirect_stdout(io.StringIO()):
                m = build(date=d, suffix=f'{d}_{name}', out_dir=OUT / 'models', **BASE, **opt)
            jobs.append(dict(date=d, scenario=name, replication=1, model=str(m), output=str(OUT / 'runs' / f'{d}_{name}')))
    plan = OUT / 'experiment_plan.json'
    plan.write_text(json.dumps({'design': __doc__, 'calibration': {'scale_low': SL, 'scale_full': SF}, 'max_steps': 60000, 'jobs': jobs}, indent=2))
    print('jobs', len(jobs), 'calibration', SL, SF, flush=True)

    def run(i):
        r = subprocess.run(['node', str(ROOT / 'tools/run_controlled_ocpn.mjs'), str(plan), str(i)], cwd=ROOT, capture_output=True, text=True)
        return {'error': r.stderr[-800:], **jobs[i]} if r.returncode else json.loads(r.stdout.splitlines()[-1])

    done = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for f in concurrent.futures.as_completed([pool.submit(run, i) for i in range(len(jobs))]):
            s = f.result(); done.append(s)
            print(json.dumps({'n': len(done), 'of': len(jobs), 'scenario': s['scenario'], 'date': s['date'], 'error': s.get('error', '')[:150]}), flush=True)
    (OUT / 'run_results.json').write_text(json.dumps(done, indent=2))
    print('errors', sum('error' in d for d in done), flush=True)


if __name__ == '__main__':
    main()
