"""Analyze v2.2 replications against observed BER properties.

Outputs (output/controlled_study_v22/):
  v22_scenarios.csv      replication-level means with t-intervals per date/scenario
  v22_contrasts.csv      Welch intervals for planned contrasts
  v22_p1_curve.csv       simulated vs observed delay-transfer curve (P1) by buffer bin
  v22_ground.csv         ground-interval and takeoff agreement vs v2.0 free-running reference
  v22_summary.md         readable summary
"""
import csv, json, math
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/controlled_study_v22'
ACDM = ROOT / 'output/acdm_primary_20261119/ACDM_Berlin_Primary_With_OpenSky_Check.csv'
BINS = [(-1e9, 30, '<=30'), (30, 45, '30-45'), (45, 60, '45-60'), (60, 90, '60-90'), (90, 1e9, '>90')]


def tci(x):
    x = np.asarray(x, float); m = x.mean()
    h = stats.t.ppf(.975, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x))
    return m, m - h, m + h


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b.mean() - a.mean(); va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1)); h = stats.t.ppf(.975, df) * math.sqrt(va + vb)
    return d, d - h, d + h


def binname(b):
    for lo, hi, n in BINS:
        if lo < b <= hi: return n


def main():
    plan = json.loads((OUT / 'experiment_plan.json').read_text())
    acdm = {r['record_key']: r for r in csv.DictReader(ACDM.open(encoding='utf-8-sig'))}
    obs = {}   # (date, case) -> observed quantities in minutes since epoch
    for date in plan['dates']:
        for scen in {j['scenario'] for j in plan['jobs']}:
            f = OUT / 'models' / f'BER_MSc_{date}_{scen}_cases.csv'
            for r in csv.DictReader(f.open(encoding='utf-8-sig')):
                a = acdm.get(r.get('acdm_reference_key') or '')
                rel = int(r['model_release_ms']) / 60000
                o = dict(release=rel, proxy=float(r['ground_interval_proxy_min']), std=None)
                if a and a.get('usable_target_takeoff_pairs') == 'True':
                    std = int(r['model_std_ms']) / 60000 if int(r.get('model_std_ms') or 0) else None
                    if std is None: continue
                    o.update(std=std, tobt_shift=float(a['tobt_minus_std_min']),
                             atot=std + (float(a['atot_minus_tobt_min']) + float(a['tobt_minus_std_min'])))
                obs[(date, r['study_case_id'])] = o
            break  # case lists identical across scenarios for a date

    reps = defaultdict(list); p1 = defaultdict(lambda: defaultdict(list)); ground = defaultdict(list)
    for j in plan['jobs']:
        s = json.loads(Path(j['output'] + '_summary.json').read_text())
        cases = json.loads(Path(j['output'] + '_cases.json').read_text())
        key = (j['date'], j['scenario']); reps[key].append(s)
        share = defaultdict(list); err_g = []; err_t = []
        for c in cases:
            o = obs.get((j['date'], c['case']))
            if not o: continue
            if o['proxy'] < 360:
                err_g.append(((c['takeoff_ms'] - c['release_ms']) / 60000) - o['proxy'])
            if o['std'] is not None:
                B = o['std'] - o['release']
                sim_shift = max(0.0, c['ready_ms'] / 60000 - o['std'])
                share[binname(B)].append(sim_shift > 5)
                if o['proxy'] < 360: err_t.append(c['takeoff_ms'] / 60000 - o['atot'])
        for b, v in share.items(): p1[key][b].append(np.mean(v))
        ground[key].append((np.mean(err_g), np.mean(np.abs(err_g)), np.median(err_g), np.mean(err_t), np.mean(np.abs(err_t))))

    # observed P1 per date (same linked cases)
    obs_p1 = defaultdict(lambda: defaultdict(list))
    for (date, case), o in obs.items():
        if o['std'] is not None: obs_p1[date][binname(o['std'] - o['release'])].append(o['tobt_shift'] > 5)

    rows = []
    for (date, scen), ss in sorted(reps.items()):
        r = dict(date=date, scenario=scen, n=len(ss))
        for m in ['mean_block_min', 'median_block_min', 'mean_fuel_wait_min', 'cabin_last_share']:
            mu, lo, hi = tci([s[m] for s in ss]); r[m] = f'{mu:.2f} [{lo:.2f}, {hi:.2f}]'
        rows.append(r)
    w = csv.DictWriter((OUT / 'v22_scenarios.csv').open('w', newline=''), fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    contrasts = []
    pairs = [('lit_berlocal_free', 'lit_berlocal_std', 'schedule binding'),
             ('orig_berlocal_std', 'lit_berlocal_std', 'literature minus original timing'),
             ('lit_berlocal_std', 'lit_berlocal_std_fuel6plus6', 'fuel 8 -> 12 units'),
             ('lit_berlocal_std', 'lit_berlocal_std_clean6', 'cleaning 9 -> 6 teams')]
    for date in plan['dates']:
        for a, b, label in pairs:
            for m in ['mean_block_min', 'mean_fuel_wait_min']:
                d, lo, hi = welch([s[m] for s in reps[(date, a)]], [s[m] for s in reps[(date, b)]])
                contrasts.append(dict(date=date, contrast=label, metric=m, diff=round(d, 3), lo=round(lo, 3), hi=round(hi, 3)))
    w = csv.DictWriter((OUT / 'v22_contrasts.csv').open('w', newline=''), fieldnames=list(contrasts[0])); w.writeheader(); w.writerows(contrasts)

    p1rows = []
    for date in plan['dates']:
        for _, _, b in BINS:
            ob = obs_p1[date][b]
            r = dict(date=date, bin=b, n_obs=len(ob), observed=round(float(np.mean(ob)), 3) if ob else '')
            for scen in ['lit_berlocal_std', 'orig_berlocal_std']:
                v = p1[(date, scen)][b]
                if v: mu, lo, hi = tci(v) if len(v) > 1 else (v[0], v[0], v[0]); r[scen] = f'{mu:.3f} [{lo:.3f}, {hi:.3f}]'
            p1rows.append(r)
    w = csv.DictWriter((OUT / 'v22_p1_curve.csv').open('w', newline=''), fieldnames=list(p1rows[0])); w.writeheader(); w.writerows(p1rows)

    grows = []
    for (date, scen), g in sorted(ground.items()):
        g = np.array(g)
        grows.append(dict(date=date, scenario=scen, ground_bias=round(g[:, 0].mean(), 2), ground_mae=round(g[:, 1].mean(), 2),
                          ground_median_err=round(g[:, 2].mean(), 2), takeoff_bias=round(g[:, 3].mean(), 2), takeoff_mae=round(g[:, 4].mean(), 2)))
    w = csv.DictWriter((OUT / 'v22_ground.csv').open('w', newline=''), fieldnames=list(grows[0])); w.writeheader(); w.writerows(grows)

    md = ['# v2.2 results', '', '## Scenarios'] + [json.dumps(r) for r in rows] + ['', '## Contrasts'] + [json.dumps(r) for r in contrasts] + \
         ['', '## P1 curve'] + [json.dumps(r) for r in p1rows] + ['', '## Ground interval (<6 h) and takeoff error vs observed'] + [json.dumps(r) for r in grows]
    (OUT / 'v22_summary.md').write_text('\n'.join(md))
    print('\n'.join(md))


if __name__ == '__main__':
    main()
