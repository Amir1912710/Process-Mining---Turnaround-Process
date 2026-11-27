"""Paired-by-day comparison of what-if scenarios against the calibrated base (41 operational days)."""
import json
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/whatif_v3'


def per_day():
    plan = json.loads((OUT / 'experiment_plan.json').read_text()); rows = []
    for j in plan['jobs']:
        p = Path(j['output'] + '_cases.json')
        if not p.exists(): continue
        c = pd.DataFrame(json.loads(p.read_text())); m = pd.read_csv(j['model'].replace('.ocpn', '_cases.csv'), low_memory=False)
        d = c.merge(m, left_on='case', right_on='study_case_id')
        d['ground'] = (d.takeoff_ms - d.release_ms) / 60000
        bound = d[d.model_std_ms > 0]
        late = ((bound.ready_ms - bound.model_std_ms) / 60000 > 5).mean() if len(bound) else np.nan
        rows.append(dict(day=j['date'], scenario=j['scenario'], n=len(d), block=d.block_min.mean(), ready=d.release_to_ready_min.mean(),
                         ready_low=d[d.model_carrier_type == 'low'].release_to_ready_min.mean(), ready_full=d[d.model_carrier_type == 'full'].release_to_ready_min.mean(),
                         ground=d.ground.mean(), late_vs_std=late, fuel_wait=d.fuel_wait_min.mean(), tug_wait=d.tug_wait_min.mean(),
                         remote_share=d.remote_stand.mean() if 'remote_stand' in d else np.nan, deiced=d.deiced.mean() if 'deiced' in d else np.nan,
                         cabin_last=(d.last_ready == 'Cabin / boarding').mean(), hold_last=d.last_ready.str.contains('Baggage').mean()))
    return pd.DataFrame(rows)


def main():
    D = per_day(); D.round(4).to_csv(OUT / 'per_day.csv', index=False)
    base = D[D.scenario == 'calibrated_base'].set_index('day')
    res = []
    for sc, g in D[D.scenario != 'calibrated_base'].groupby('scenario'):
        g = g.set_index('day').reindex(base.index)
        for m in ['block', 'ready', 'ready_low', 'ready_full', 'ground', 'late_vs_std', 'fuel_wait', 'tug_wait', 'cabin_last', 'hold_last']:
            diff = (g[m] - base[m]).dropna()
            if len(diff) < 3: continue
            mu = diff.mean(); h = stats.t.ppf(.975, len(diff) - 1) * diff.std(ddof=1) / np.sqrt(len(diff))
            res.append(dict(scenario=sc, metric=m, days=len(diff), base_mean=round(base[m].mean(), 3), diff=round(mu, 3), lo=round(mu - h, 3), hi=round(mu + h, 3)))
    R = pd.DataFrame(res); R.to_csv(OUT / 'paired_contrasts.csv', index=False)
    print(D.groupby('scenario')[['block', 'ready', 'ground', 'late_vs_std', 'fuel_wait', 'remote_share', 'deiced', 'cabin_last', 'hold_last']].mean().round(3).to_string())
    print(R[R.metric.isin(['block', 'ready', 'late_vs_std', 'fuel_wait', 'ready_low', 'ready_full'])].to_string(index=False))


if __name__ == '__main__':
    main()
