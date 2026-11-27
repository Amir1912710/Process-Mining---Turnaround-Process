"""v4 rerun with carrier-specific baggage times. Runs every step in order and logs progress."""
import contextlib, io, json, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; T = ROOT / 'tools'
PY = sys.executable

def step(name, cmd):
    t = time.time(); print(f'=== {name} START', flush=True)
    r = subprocess.run(cmd, cwd=T, capture_output=True, text=True)
    (ROOT / 'output' / f'v4_log_{name}.txt').write_text(r.stdout + '\n' + r.stderr, encoding='utf-8')
    print(f'=== {name} END rc={r.returncode} {round((time.time()-t)/60,1)} min', flush=True)
    print('\n'.join(r.stdout.strip().splitlines()[-6:]), flush=True)
    if r.returncode: print(r.stderr[-1500:], flush=True); sys.exit(1)

step('calibration', [PY, 'calibrate_v4.py'])
step('validation_1516', [PY, 'validate_new_days_v4.py'])
step('study_carrier', [PY, '-c', "import run_v3_study as S; S.main('study_v4',['carrier'],workers=7,extra={'carrier':{'baggage':'carrier'}})"])
step('analyze_study', [PY, 'analyze_v3.py', str(ROOT / 'output/study_v4')])
step('whatif', [PY, 'run_whatif_v4.py'])
step('analyze_whatif', [PY, 'analyze_whatif_v4.py'])
step('analyze_whatif_mech', [PY, 'analyze_v3.py', str(ROOT / 'output/whatif_v4')])
step('ocel', [PY, 'export_ocel_v4.py'])
step('process_mining', [PY, 'process_mining_v3.py', str(ROOT / 'output/process_mining_v4')] +
     [str(ROOT / f'output/ocel_v4/BER_MSc_2026-11-0{d}_calibrated.ocel.json') for d in (1, 5, 8)])
print('ALL DONE', flush=True)
