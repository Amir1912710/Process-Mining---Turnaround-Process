"""Analysis of trace-driven v3 runs (all 41 days) against observed BER behaviour.

Usage: python analyze_v3.py <study_dir> [<study_dir> ...]   (e.g. study_v3, study_v3_calibrated)
Writes <study_dir>/analysis.json and CSV tables.
"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ACDM = ROOT / 'output/acdm_primary_20261119/ACDM_Berlin_Primary_With_OpenSky_Check.csv'
WX = ROOT / 'data/weather/ber_hourly_2026.json'
BINS = [-1e9, 30, 45, 60, 90, 1e9]; BLAB = ['<=30', '30-45', '45-60', '60-90', '>90']


def load(study):
    plan = json.loads((study / 'experiment_plan.json').read_text())
    acdm = pd.read_csv(ACDM, low_memory=False).set_index('record_key')
    rows = []
    for j in plan['jobs']:
        p = Path(j['output'] + '_cases.json')
        if not p.exists(): continue
        cases = pd.DataFrame(json.loads(p.read_text()))
        man = pd.read_csv(j['model'].replace('.ocpn', '_cases.csv'), low_memory=False)
        df = cases.merge(man, left_on='case', right_on='study_case_id')
        df['scenario'] = j['scenario']; df['day'] = j['date']
        rows.append(df)
    d = pd.concat(rows, ignore_index=True)
    d['sim_ground'] = (d.takeoff_ms - d.release_ms) / 60000
    lk = d.acdm_reference_key.isin(acdm.index)
    a = acdm.reindex(d.acdm_reference_key)
    d['obs_tobt_shift'] = np.where(lk, a.tobt_minus_std_min.values, np.nan)
    d['obs_usable'] = np.where(lk, a.usable_target_takeoff_pairs.values == True, False)
    d['std_min'] = d.model_std_ms / 60000; d['rel_min'] = d.model_release_ms / 60000
    d['buffer'] = np.where(d.model_std_ms > 0, d.std_min - d.rel_min, np.nan)
    d['obs_tta'] = d.buffer + d.obs_tobt_shift
    d['sim_shift'] = np.where(d.model_std_ms > 0, np.maximum(0, d.ready_ms / 60000 - d.std_min), np.nan)
    d['cls'] = d.carrier_class
    return d


def q(x, ps=(5, 25, 50, 75)):
    x = pd.Series(x).dropna()
    return [round(float(np.percentile(x, p)), 1) for p in ps] if len(x) else []


def analyze(study):
    d = load(study); res = {'n_cases_per_scenario': d.groupby('scenario').size().to_dict()}
    short = d[d.ground_interval_proxy_min < 360]
    linked = d[d.obs_usable & (d.ground_interval_proxy_min < 360) & d.buffer.notna()]
    # 1. arrival-to-ready vs observed target turnaround (linked), by class and scenario
    tab = []
    for (sc, cl), g in linked.groupby(['scenario', 'cls']):
        if len(g) < 15: continue
        o, s = q(g.obs_tta), q(g.release_to_ready_min)
        tab.append(dict(scenario=sc, cls=cl, n=len(g), obs_p5_25_50_75=o, sim_p5_25_50_75=s, mae_quantiles=round(float(np.mean(np.abs(np.array(o) - np.array(s)))), 2)))
    res['tta_vs_ready'] = tab
    # 2. delay-transfer curve P1 (simulated with schedule binding vs observed)
    p1 = []
    for sc, g in linked.groupby('scenario'):
        g = g.assign(bin=pd.cut(g.buffer, BINS, labels=BLAB))
        for b, h in g.groupby('bin', observed=True):
            p1.append(dict(scenario=sc, bin=str(b), n=len(h), observed=round(float((h.obs_tobt_shift > 5).mean()), 3), simulated=round(float((h.sim_shift > 5).mean()), 3)))
    res['p1'] = p1
    # 3. ground interval (short stays) floors by class
    gt = []
    for (sc, cl), g in short.groupby(['scenario', 'cls']):
        gt.append(dict(scenario=sc, cls=cl, n=len(g), obs_ground_q=q(g.ground_interval_proxy_min), sim_ground_q=q(g.sim_ground),
                       sim_block_q=q(g.block_min), sim_ready_q=q(g.release_to_ready_min)))
    res['ground'] = gt
    # 4. process mechanism by class: last-ready branch shares and resource waits
    mech = []
    for (sc, cl), g in d.groupby(['scenario', 'cls']):
        lr = g.last_ready.value_counts(normalize=True).round(3).to_dict()
        mech.append(dict(scenario=sc, cls=cl, n=len(g), mean_block=round(g.block_min.mean(), 2), median_block=round(g.block_min.median(), 2),
                         fuel_wait=round(g.fuel_wait_min.mean(), 2), clean_wait=round(g.clean_wait_min.mean(), 2), tug_wait=round(g.tug_wait_min.mean(), 2),
                         last_ready=lr))
    res['mechanism'] = mech
    # 5. daily panel vs observed weather
    w = pd.DataFrame(json.loads(WX.read_text())['hourly']); w['time'] = pd.to_datetime(w.time).dt.tz_localize('UTC')
    w['day'] = w.time.dt.tz_convert('Europe/Berlin').dt.strftime('%Y-%m-%d')
    wd = w.groupby('day').agg(temp_min=('temperature_2m', 'min'), precip=('precipitation', 'sum'), gust_max=('wind_gusts_10m', 'max'))
    daily = d.groupby(['scenario', 'day']).agg(cases=('case', 'size'), mean_block=('block_min', 'mean'), fuel_wait=('fuel_wait_min', 'mean'),
                                                approval_to_offblock=('approval_to_offblock_min', 'mean')).reset_index().merge(wd, on='day', how='left')
    daily.round(3).to_csv(study / 'daily_panel.csv', index=False)
    res['daily_corr'] = {sc: g[['mean_block', 'fuel_wait', 'cases', 'temp_min', 'precip', 'gust_max']].corr(method='spearman').round(2)['mean_block'].to_dict()
                         for sc, g in daily.groupby('scenario')}
    (study / 'analysis.json').write_text(json.dumps(res, indent=2, default=str))
    pd.DataFrame(tab).to_csv(study / 'tta_vs_ready.csv', index=False); pd.DataFrame(p1).to_csv(study / 'p1_curve.csv', index=False)
    pd.DataFrame(mech).to_csv(study / 'mechanism.csv', index=False); pd.DataFrame(gt).to_csv(study / 'ground.csv', index=False)
    return res


if __name__ == '__main__':
    for s in sys.argv[1:]:
        r = analyze(ROOT / 'output' / s)
        print('==', s, json.dumps({k: r[k] for k in ['n_cases_per_scenario', 'tta_vs_ready', 'p1', 'mechanism']}, indent=1, default=str))
