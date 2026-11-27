"""Build, run and export the calibrated v4 models of 1, 5 and 8 November as OCEL 2.0 (same settings as whatif_v4 base)."""
import contextlib, io, json, subprocess
from pathlib import Path
from build_msc_ocpn import build
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'output/ocel_v4'; OUT.mkdir(parents=True, exist_ok=True)
SL, SF = json.loads((ROOT / 'output/calibration_v4/calibration_results.json').read_text())['best']
BASE = dict(context='enriched', weather='observed', curfew='ber_local', schedule='std', timing='carrier',
            leisure_profile='full', scale_low=SL, scale_full=SF, baggage='carrier')
for d in ('2026-11-01', '2026-11-05', '2026-11-08'):
    with contextlib.redirect_stdout(io.StringIO()):
        m = build(date=d, suffix=f'{d}_calibrated', out_dir=OUT, **BASE)
    for cmd in (['node', 'tools/run_msc_ocpn.mjs', str(m), '60000'], ['node', 'tools/export_msc_ocel.mjs', str(m)]):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode: raise RuntimeError(' '.join(cmd) + '\n' + r.stderr[-1500:])
    print(d, 'ok', m.name, flush=True)
