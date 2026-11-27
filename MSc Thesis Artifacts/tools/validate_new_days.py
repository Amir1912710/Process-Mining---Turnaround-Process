"""Held-out validation of the calibrated model on 15 and 16 November 2026 (not used for calibration)."""
import contextlib, io, json
from pathlib import Path
import numpy as np
import calibrate_v3 as C
from build_msc_ocpn import build

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/ber_history/prepared/ber_turnarounds_validation_nov15_16.csv'
OUT = ROOT / 'output/validation_nov15_16'; (OUT / 'models').mkdir(parents=True, exist_ok=True); (OUT / 'runs').mkdir(exist_ok=True)
B = dict(context='enriched', weather='observed', curfew='ber_local', schedule='std', leisure_profile='full', source=str(SRC))
CONF = {'calibrated': dict(timing='carrier', scale_low=1.3, scale_full=1.1), 'uncalibrated': dict(timing='carrier'),
        'literature': dict(timing='literature'), 'original': dict(timing='baseline')}
acdm = C.observed(); jobs = []
for d in ['2026-11-15', '2026-11-16']:
    for name, o in CONF.items():
        with contextlib.redirect_stdout(io.StringIO()):
            m = build(date=d, suffix=f'{d}_{name}', out_dir=OUT / 'models', **B, **o)
        jobs.append(dict(date=d, scenario=name, replication=1, model=str(m), output=str(OUT / 'runs' / f'{d}_{name}')))
C.run_jobs(jobs, OUT / 'plan.json', workers=8)
res = {}
for name in CONF:
    obs = {'low': [], 'full': []}; sim = {'low': [], 'full': []}
    for j in [x for x in jobs if x['scenario'] == name]:
        o, s = C.tta_pairs(j, acdm)
        for k in obs: obs[k] += o[k]; sim[k] += s[k]
    res[name] = dict(loss=round(C.loss(obs, sim), 2), n_low=len(obs['low']), n_full=len(obs['full']),
                     low_obs=np.round(np.percentile(obs['low'], C.Q), 1).tolist(), low_sim=np.round(np.percentile(sim['low'], C.Q), 1).tolist(),
                     full_obs=np.round(np.percentile(obs['full'], C.Q), 1).tolist(), full_sim=np.round(np.percentile(sim['full'], C.Q), 1).tolist())
(OUT / 'validation_results.json').write_text(json.dumps(res, indent=2)); print(json.dumps(res, indent=1))
