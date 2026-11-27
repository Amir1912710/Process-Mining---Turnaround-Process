"""v3 study: carrier-specific service times on the full 10k-turnaround demand (single trace-driven run per day).

Design (frozen 2026-11-20 before execution):
  * demand: all in-scope OpenSky candidate turnarounds, one model per arrival day (30 Sep - 9 Nov 2026)
  * every scenario uses observed BER weather, BER local-time night ban at pushback, schedule binding to
    A-CDM STD where a departure is linked, carrier-dependent passenger loads
  * scenarios differ only in the service-time functions: original (baseline), literature (carrier-agnostic),
    carrier (low-cost vs full-service)
  * one run per day and scenario (trace-driven, no Monte Carlo replication); run-to-run variability is
    reported separately from the v2.2 replications
"""
import argparse, concurrent.futures, contextlib, csv, hashlib, io, json, subprocess
from pathlib import Path
from build_msc_ocpn import build, BASE, ENRICHED

ROOT = Path(__file__).resolve().parents[1]
COMMON = dict(context='enriched', weather='observed', curfew='ber_local', schedule='std', leisure_profile='low')
SCENARIOS = {
    'original': dict(timing='baseline'),
    'literature': dict(timing='literature'),
    'carrier': dict(timing='carrier'),
}


def dates():
    ds = sorted({r['inbound_last_seen_berlin'][:10] for r in csv.DictReader(ENRICHED.open(encoding='utf-8-sig')) if r['in_scope'] == 'True'})
    return ds


def main(out, scenarios, workers=6, smoke=False, extra=None):
    OUT = ROOT / 'output' / out
    (OUT / 'runs').mkdir(parents=True, exist_ok=True); (OUT / 'models').mkdir(exist_ok=True)
    base_sha = hashlib.sha256(BASE.read_bytes()).hexdigest(); assert base_sha.startswith('b83e78fbdaa2289c')
    ds = ['2026-11-01'] if smoke else dates()
    plan = {'design': __doc__, 'dates': ds, 'max_steps': 60000, 'baseline_sha256': base_sha, 'jobs': []}
    for date in ds:
        for name in scenarios:
            opts = dict(COMMON, **SCENARIOS.get(name, {}), **(extra or {}).get(name, {}))
            with contextlib.redirect_stdout(io.StringIO()):
                model = build(date=date, limit=12 if smoke else None, suffix=f'{date}_{name}', out_dir=OUT / 'models', **opts)
            plan['jobs'].append(dict(date=date, scenario=name, replication=1, model=str(model), output=str(OUT / 'runs' / f'{date}_{name}')))
    planfile = OUT / ('smoke_plan.json' if smoke else 'experiment_plan.json'); planfile.write_text(json.dumps(plan, indent=2))
    print('jobs', len(plan['jobs']), flush=True)

    def run(i):
        r = subprocess.run(['node', str(ROOT / 'tools/run_controlled_ocpn.mjs'), str(planfile), str(i)], cwd=ROOT, capture_output=True, text=True)
        if r.returncode: return {'error': r.stderr[-1500:], **plan['jobs'][i]}
        return json.loads(r.stdout.splitlines()[-1])

    done = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for f in concurrent.futures.as_completed([pool.submit(run, i) for i in range(len(plan['jobs']))]):
            s = f.result(); done.append(s)
            print(json.dumps({'n': len(done), 'of': len(plan['jobs']), 'date': s['date'], 'scenario': s['scenario'],
                              'error': s.get('error', '')[:200], 'mean_block': round(s.get('mean_block_min', -1), 2)}), flush=True)
    (OUT / ('smoke_results.json' if smoke else 'run_results.json')).write_text(json.dumps(done, indent=2))
    print('errors', sum('error' in d for d in done), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', default='study_v3'); p.add_argument('--workers', type=int, default=6)
    p.add_argument('--smoke', action='store_true'); p.add_argument('--scenarios', default='original,literature,carrier')
    a = p.parse_args(); main(a.out, a.scenarios.split(','), a.workers, a.smoke)
