"""v2.2 study: BER local-time night ban at pushback + schedule-bound departures.

Design frozen before execution (2026-11-20). Two dates, five scenarios, ten independent
replications per cell. Uses the unchanged v2.1 runner (with added per-case timestamps).
"""
import argparse, concurrent.futures, contextlib, hashlib, io, json, subprocess
from pathlib import Path
from build_msc_ocpn import build, BASE

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/controlled_study_v22'
SCENARIOS = [
    ('lit_berlocal_free', dict(timing='literature', curfew='ber_local', schedule='none')),
    ('lit_berlocal_std', dict(timing='literature', curfew='ber_local', schedule='std')),
    ('orig_berlocal_std', dict(timing='baseline', curfew='ber_local', schedule='std')),
    ('lit_berlocal_std_fuel6plus6', dict(timing='literature', curfew='ber_local', schedule='std', hydrant_dispensers=6, fuel_tankers=6)),
    ('lit_berlocal_std_clean6', dict(timing='literature', curfew='ber_local', schedule='std', cleaning_teams=6)),
]


def main(reps=10, workers=3, smoke=False):
    OUT.mkdir(parents=True, exist_ok=True); (OUT / 'runs').mkdir(exist_ok=True); (OUT / 'models').mkdir(exist_ok=True)
    base_sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
    assert base_sha.startswith('b83e78fbdaa2289c'), 'baseline model changed'
    plan = {'design': 'v2.2 frozen 2026-11-20 before execution: BER 00:00-05:00 local night ban at pushback only; '
                      'schedule binding to A-CDM STD for linked cases; ten independent replications per cell.',
            'dates': ['2026-11-01', '2026-11-08'], 'replications': reps, 'max_steps': 30000,
            'randomization': 'Runtime RNG; seeds not exposed; independent unpaired replications.',
            'baseline_sha256': base_sha, 'jobs': []}
    if smoke:
        plan['dates'] = ['2026-11-01']
    for date in plan['dates']:
        for name, options in (SCENARIOS[:2] if smoke else SCENARIOS):
            with contextlib.redirect_stdout(io.StringIO()):
                model = build(date=date, limit=8 if smoke else None, suffix=date + '_' + name, out_dir=OUT / 'models', **options)
            for r in range(1, reps + 1):
                plan['jobs'].append(dict(date=date, scenario=name, replication=r, model=str(model),
                                         output=str(OUT / 'runs' / f'{"smoke_" if smoke else ""}{date}_{name}_r{r:02d}')))
    planfile = OUT / ('smoke_plan.json' if smoke else 'experiment_plan.json')
    planfile.write_text(json.dumps(plan, indent=2))
    print('Frozen design:', len(plan['jobs']), 'replications;', planfile, flush=True)

    def run(i):
        job = plan['jobs'][i]
        res = subprocess.run(['node', str(ROOT / 'tools/run_controlled_ocpn.mjs'), str(planfile), str(i)],
                             cwd=ROOT, capture_output=True, text=True)
        if res.returncode:
            raise RuntimeError(f'{job}: {res.stderr[-2000:]}')
        return json.loads(res.stdout.splitlines()[-1])

    done = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(run, i) for i in range(len(plan['jobs']))]
        for f in concurrent.futures.as_completed(futs):
            s = f.result(); done.append(s)
            (OUT / 'progress.json').write_text(json.dumps({'completed': len(done), 'total': len(futs)}, indent=2))
            print(json.dumps({'completed': len(done), 'total': len(futs), 'date': s['date'], 'scenario': s['scenario'],
                              'rep': s['replication'], 'mean_block': round(s['mean_block_min'], 2),
                              'seconds': round(s['elapsed_seconds'], 1)}), flush=True)
    (OUT / ('smoke_results.json' if smoke else 'replication_results.json')).write_text(json.dumps(done, indent=2))
    print('All replications completed and passed integrity checks.', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--reps', type=int, default=10); p.add_argument('--workers', type=int, default=3)
    p.add_argument('--smoke', action='store_true'); a = p.parse_args(); main(a.reps, a.workers, a.smoke)
