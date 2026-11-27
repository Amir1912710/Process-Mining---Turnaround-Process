"""Delay drivers and early detection on observed BER data (RQ2/RQ3 support).

A. Feb-Apr 2026 manual A-CDM turnarounds (n=2,067): predict outbound departure delay > 15 min
   at the moment the inbound aircraft lands (features known at landing). Train 21 Feb-4 Mar, test 17-24 Apr.
B. Nov 2026 linked A-CDM/OpenSky turnarounds (n=610): predict a late TOBT (> STD + 5 min) at landing;
   leave-one-day-out evaluation.
C. Daily disruption screening on the 10,940 OpenSky turnarounds (30 Sep - 9 Nov): robust z-scores of daily
   traffic and ground-time indicators, joined with observed weather, to flag candidate disruption days.
Outputs in output/early_warning/.
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss, precision_score, recall_score
from sklearn.inspection import permutation_importance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/early_warning'; OUT.mkdir(parents=True, exist_ok=True)
FEBAPR = Path(r'C:/Users/amira/Documents/GitHub/Process-Mining---Turnaround-Process/DS Lab2/final/cleaned_dataset.csv')
ACDM = ROOT / 'output/acdm_primary_20261119/ACDM_Berlin_Primary_With_OpenSky_Check.csv'
PAIRS = ROOT / 'data/ber_history/prepared/ber_turnarounds_enriched.csv'
WX = ROOT / 'data/weather/ber_hourly_2026.json'
RNG = 20261120


def weather():
    w = pd.DataFrame(json.loads(WX.read_text())['hourly']); w['time'] = pd.to_datetime(w.time).dt.tz_localize('UTC')
    w['wx_snow'] = (w.snowfall > 0).astype(int); w['wx_wet'] = (w.precipitation >= 0.1).astype(int)
    w['wx_freezing'] = (w.temperature_2m <= 1).astype(int)
    return w.rename(columns={'temperature_2m': 'wx_temp', 'precipitation': 'wx_precip', 'wind_gusts_10m': 'wx_gust',
                             'wind_speed_10m': 'wx_wind', 'cloud_cover': 'wx_cloud'})[['time', 'wx_temp', 'wx_precip', 'wx_gust', 'wx_wind', 'wx_cloud', 'wx_snow', 'wx_wet', 'wx_freezing']]


def evaluate(name, Xtr, ytr, Xte, yte, feats):
    res = {}
    for label, model in [('logistic', make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight='balanced'))),
                         ('gradient_boosting', HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300, random_state=RNG))]:
        model.fit(Xtr, ytr); p = model.predict_proba(Xte)[:, 1]
        thr = np.quantile(p, 1 - yte.mean())   # flag as many as the base rate
        pred = (p >= thr).astype(int)
        imp = permutation_importance(model, Xte, yte, scoring='roc_auc', n_repeats=20, random_state=RNG)
        res[label] = dict(auc=round(roc_auc_score(yte, p), 3), brier=round(brier_score_loss(yte, p), 3),
                          precision_at_base_rate=round(precision_score(yte, pred), 3), recall_at_base_rate=round(recall_score(yte, pred), 3),
                          importance={f: round(v, 4) for f, v in sorted(zip(feats, imp.importances_mean), key=lambda x: -x[1])})
    res['base_rate_test'] = round(float(yte.mean()), 3); res['n_train'] = int(len(ytr)); res['n_test'] = int(len(yte))
    print(name, json.dumps({k: (v if k.startswith(('base', 'n_')) else {kk: vv for kk, vv in v.items() if kk != 'importance'}) for k, v in res.items()}))
    return res


def part_a(w):
    d = pd.read_csv(FEBAPR)
    for c in ['LandingTime', 'LandingActualTime', 'DepartureTime', 'DepartureActualTime']:
        d[c] = pd.to_datetime(d[c]).dt.tz_localize('Europe/Berlin', ambiguous='NaT', nonexistent='shift_forward')
    d['inb'] = (d.LandingActualTime - d.LandingTime).dt.total_seconds() / 60
    d['outb'] = (d.DepartureActualTime - d.DepartureTime).dt.total_seconds() / 60
    d['sta'] = (d.DepartureTime - d.LandingTime).dt.total_seconds() / 60
    d['ata'] = (d.DepartureActualTime - d.LandingActualTime).dt.total_seconds() / 60
    d = d[~((d.ata <= 15) | (d.outb.abs() > 300) | (d.inb.abs() > 300))].copy()
    d['remaining_buffer'] = (d.DepartureTime - d.LandingActualTime).dt.total_seconds() / 60
    d['low_cost'] = (d.type == 'low-cost').astype(int)
    d['hour'] = d.LandingActualTime.dt.hour; d['weekday'] = d.LandingActualTime.dt.weekday
    d['gate_area'] = d.Gate.astype(str).str[0].map({'A': 0, 'B': 1, 'C': 2, 'D': 3}).fillna(4)
    d = d.sort_values('LandingActualTime')
    t = d.LandingActualTime.values.astype('datetime64[s]').astype(np.int64)
    d['arrivals_pm60'] = [int((np.abs(t - x) <= 3600).sum() - 1) for x in t]
    d['hour_utc'] = d.LandingActualTime.dt.tz_convert('UTC').dt.floor('h')
    d = d.merge(w, left_on='hour_utc', right_on='time', how='left')
    d['late15'] = (d.outb > 15).astype(int)
    d['lead_time_min'] = d.remaining_buffer
    feats = ['inb', 'sta', 'remaining_buffer', 'low_cost', 'hour', 'weekday', 'gate_area', 'arrivals_pm60',
             'wx_temp', 'wx_precip', 'wx_gust', 'wx_wind', 'wx_cloud', 'wx_freezing']
    tr = d[d.LandingTime < pd.Timestamp('2026-04-01', tz='Europe/Berlin')]; te = d[d.LandingTime >= pd.Timestamp('2026-04-01', tz='Europe/Berlin')]
    res = evaluate('A Feb-Apr late>15', tr[feats], tr.late15, te[feats], te.late15, feats)
    res['median_lead_time_min'] = round(float(te.lead_time_min.median()), 1)
    # descriptive weather effect: outbound delay by weather condition
    d['condition'] = np.select([d.wx_precip >= 0.1, d.wx_gust >= 50], ['precipitation', 'gusts>=50 km/h'], 'dry/calm')
    res['delay_by_condition'] = d.groupby('condition').agg(n=('outb', 'size'), median_outbound=('outb', 'median'), late15=('late15', 'mean')).round(3).reset_index().to_dict('records')
    res['delay_by_class'] = d.groupby('type').agg(n=('outb', 'size'), median_inbound=('inb', 'median'), median_outbound=('outb', 'median'), late15=('late15', 'mean')).round(3).reset_index().to_dict('records')
    return res


def part_b(w):
    P = pd.read_csv(PAIRS, low_memory=False)
    A = pd.read_csv(ACDM, low_memory=False)
    m = P.dropna(subset=['acdm_reference_key']).merge(A, left_on='acdm_reference_key', right_on='record_key', how='inner', suffixes=('', '_acdm'))
    m = m[(m.usable_target_takeoff_pairs == True) & (m.ground_interval_proxy_min < 360) & m.in_scope].copy()
    land = pd.to_datetime(m.inbound_last_seen_utc)
    std = pd.to_datetime(m.std_parsed).dt.tz_localize('UTC')
    m['buffer'] = (std - land).dt.total_seconds() / 60
    m['low_cost'] = m.carrier_class.isin(['low-cost', 'leisure']).astype(int)
    m['hour'] = land.dt.hour; m['narrow'] = m.aircraft_type.fillna('').str.match(r'^(A3[12]|A2|B73|B3|BCS)').astype(int)
    t = land.values.astype('datetime64[s]').astype(np.int64)
    m['arrivals_pm60'] = [int((np.abs(t - x) <= 3600).sum() - 1) for x in t]
    m['late_tobt'] = (m.tobt_minus_std_min > 5).astype(int)
    feats = ['buffer', 'low_cost', 'hour', 'narrow', 'arrivals_pm60', 'temperature_2m', 'precipitation', 'wind_gusts_10m']
    m = m.dropna(subset=feats)
    res = {}; aucs = []
    for day in sorted(m.source_day.unique()):
        tr, te = m[m.source_day != day], m[m.source_day == day]
        r = evaluate(f'B Nov late TOBT, test {day}', tr[feats], tr.late_tobt, te[feats], te.late_tobt, feats)
        res[day] = r; aucs.append(r['gradient_boosting']['auc'])
    res['mean_auc_gb'] = round(float(np.mean(aucs)), 3)
    return res


def part_c(w):
    P = pd.read_csv(PAIRS, low_memory=False)
    P = P[P.in_scope].copy(); P['day'] = P.departure_date_berlin
    short = P[P.ground_interval_proxy_min < 360]
    daily = P.groupby('day').size().rename('turnarounds').to_frame()
    daily['median_ground_short'] = short.groupby('day').ground_interval_proxy_min.median()
    daily['share_long_stay'] = (P.ground_interval_proxy_min >= 360).groupby(P.day).mean()
    for cls in ['low-cost', 'full-service']:
        daily[f'median_ground_{cls}'] = short[short.carrier_class == cls].groupby('day').ground_interval_proxy_min.median()
    w2 = w.copy(); w2['day'] = w2.time.dt.tz_convert('Europe/Berlin').dt.strftime('%Y-%m-%d')
    wd = w2.groupby('day').agg(temp_mean=('wx_temp', 'mean'), precip_sum=('wx_precip', 'sum'), gust_max=('wx_gust', 'max'), snow_hours=('wx_snow', 'sum'))
    daily = daily.join(wd, how='left')
    for c in ['turnarounds', 'median_ground_short']:
        med = daily[c].median(); mad = (daily[c] - med).abs().median() * 1.4826
        daily[f'z_{c}'] = ((daily[c] - med) / mad).round(2)
    daily['flag'] = (daily.z_turnarounds.abs() >= 2.5) | (daily.z_median_ground_short.abs() >= 2.5)
    daily.round(2).to_csv(OUT / 'daily_screening.csv')
    corr = daily[['median_ground_short', 'precip_sum', 'gust_max', 'temp_mean']].corr(method='spearman').round(2)
    print('C flagged days:', daily[daily.flag].index.tolist())
    return dict(flagged=daily[daily.flag].reset_index().round(2).to_dict('records'), spearman=corr.to_dict(), n_days=int(len(daily)))


if __name__ == '__main__':
    w = weather()
    out = dict(A=part_a(w), B=part_b(w), C=part_c(w))
    (OUT / 'results.json').write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out['A']['delay_by_condition'], indent=1)); print(json.dumps(out['A']['delay_by_class'], indent=1))
    print('A importance GB:', out['A']['gradient_boosting']['importance'])
    print('C:', json.dumps(out['C']['flagged'], default=str)[:2000])
