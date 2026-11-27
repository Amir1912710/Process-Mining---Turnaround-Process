"""Literature and original timing on the held-out day 8 Nov (same settings as calibration validation)."""
import contextlib, io, json, numpy as np
from pathlib import Path
import calibrate_v3 as C
from build_msc_ocpn import build
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'output/validation_nov15_16'
B = dict(context='enriched', weather='observed', curfew='ber_local', schedule='std', leisure_profile='full')
acdm = C.observed(); jobs = []
for name, o in {'literature': dict(timing='literature'), 'original': dict(timing='baseline')}.items():
    with contextlib.redirect_stdout(io.StringIO()):
        m = build(date='2026-11-08', suffix=f'2026-11-08_{name}', out_dir=OUT / 'models', **B, **o)
    jobs.append(dict(date='2026-11-08', scenario=name, replication=1, model=str(m), output=str(OUT / 'runs' / f'2026-11-08_{name}')))
C.run_jobs(jobs, OUT / 'plan_nov8.json', workers=2)
res = {}
for j in jobs:
    o, s = C.tta_pairs(j, acdm)
    res[j['scenario']] = dict(loss=round(C.loss(o, s), 2), low_sim=np.round(np.percentile(s['low'], C.Q), 1).tolist(), full_sim=np.round(np.percentile(s['full'], C.Q), 1).tolist())
(OUT / 'nov8_reference_results.json').write_text(json.dumps(res, indent=2)); print(res)
