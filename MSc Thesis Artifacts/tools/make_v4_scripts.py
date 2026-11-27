"""Create v4 copies of the v3 study scripts: same design, plus carrier-specific baggage times (baggage='carrier')."""
from pathlib import Path
T = Path(__file__).resolve().parent

def make(src, dst, reps):
    s = (T / src).read_text(encoding='utf-8')
    for a, b in reps:
        assert a in s, (src, a)
        s = s.replace(a, b)
    (T / dst).write_text(s, encoding='utf-8')
    print('wrote', dst)

make('calibrate_v3.py', 'calibrate_v4.py', [
    ("output/calibration_v3", "output/calibration_v4"),
    ("schedule='std', timing='carrier')", "schedule='std', timing='carrier', leisure_profile='full', baggage='carrier')"),
    ("GRID = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]", "GRID = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]\nGRID_LOW = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]"),
    ("itertools.product(GRID, GRID)", "itertools.product(GRID_LOW, GRID)"),
])
make('validate_new_days.py', 'validate_new_days_v4.py', [
    ("import calibrate_v3 as C", "import calibrate_v4 as C"),
    ("output/validation_nov15_16'", "output/validation_nov15_16_v4'"),
    ("CONF = {'calibrated': dict(timing='carrier', scale_low=1.3, scale_full=1.1), 'uncalibrated': dict(timing='carrier'),\n        'literature': dict(timing='literature'), 'original': dict(timing='baseline')}",
     "_cal = json.loads((ROOT / 'output/calibration_v4/calibration_results.json').read_text())['best']\nCONF = {'calibrated': dict(timing='carrier', baggage='carrier', scale_low=_cal[0], scale_full=_cal[1]), 'uncalibrated': dict(timing='carrier', baggage='carrier')}"),
])
make('run_whatif_v3.py', 'run_whatif_v4.py', [
    ("output/whatif_v3'", "output/whatif_v4'"),
    ("output/calibration_v3/calibration_results.json", "output/calibration_v4/calibration_results.json"),
    ("scale_low=SL, scale_full=SF)", "scale_low=SL, scale_full=SF, baggage='carrier')"),
])
make('analyze_whatif_v3.py', 'analyze_whatif_v4.py', [
    ("output/whatif_v3'", "output/whatif_v4'"),
])
