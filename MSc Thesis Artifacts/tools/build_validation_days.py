"""Build turnaround demand for the additional validation days 15 and 16 November 2026.

The frozen 41-day dataset (30 Sep - 9 Nov) is NOT modified. This script applies the same pairing rule
(adjacent OpenSky BER arrival -> departure of the same ICAO24) to the raw OpenSky lists of 15-16 Nov,
links departures to A-CDM via the existing unique callsign/time cross-check, and applies the same
enrichment (airline, carrier class, aircraft type, weather) as enrich_turnarounds.py.
OpenSky has no list for 14 Nov, so pairs whose arrival would precede 15 Nov 00:00 Berlin are not formed.
Output: data/ber_history/prepared/ber_turnarounds_validation_nov15_16.csv
"""
import csv, json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import pandas as pd
from enrich_turnarounds import AIRLINES, BIZ_TYPES, META, WEATHER, EXCL

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/ber_history/opensky'
ACDM = ROOT / 'output/acdm_primary_20261119/ACDM_Berlin_Primary_With_OpenSky_Check.csv'
OUT = ROOT / 'data/ber_history/prepared/ber_turnarounds_validation_nov15_16.csv'
BER = ZoneInfo('Europe/Berlin'); UTC = timezone.utc
DAYS = ['2026-11-15', '2026-11-16']
LO = datetime(2026, 11, 15, tzinfo=BER).timestamp(); HI = datetime(2026, 11, 17, tzinfo=BER).timestamp()


def iso(ts, tz=UTC): return datetime.fromtimestamp(ts, tz).isoformat()


def main():
    ev = []
    for d in DAYS:
        for direction in ('arrival', 'departure'):
            for f in json.loads((RAW / d / f'{direction}.json').read_text()):
                b = f['lastSeen'] if direction == 'arrival' else f['firstSeen']
                if not f.get('icao24') or b is None: continue
                ap = f.get('estArrivalAirport' if direction == 'arrival' else 'estDepartureAirport')
                ev.append(dict(icao24=f['icao24'].lower(), direction=direction, t=b, callsign=(f.get('callsign') or '').strip().upper(),
                               origin=f.get('estDepartureAirport') or '', dest=f.get('estArrivalAirport') or '', ok_airport=(ap == 'EDDB'),
                               key='|'.join(map(str, (f['icao24'].lower(), f['firstSeen'], f['lastSeen'], direction)))))
    ev = sorted({e['key']: e for e in ev}.values(), key=lambda e: (e['icao24'], e['t']))
    acdm = pd.read_csv(ACDM, low_memory=False)
    acdm = acdm[acdm.source_day.isin(DAYS) & acdm.crosscheck_opensky_flight_key.notna()]
    link = dict(zip(acdm.crosscheck_opensky_flight_key, acdm.record_key))
    A = acdm.set_index('record_key')
    rows = []
    by = {}
    for e in ev: by.setdefault(e['icao24'], []).append(e)
    for ac, seq in by.items():
        for i, d in enumerate(seq):
            if d['direction'] != 'departure' or i == 0 or seq[i - 1]['direction'] != 'arrival': continue
            a = seq[i - 1]
            el = (d['t'] - a['t']) / 60
            if not (LO <= a['t'] < HI) or el < 15 or el > 1440: continue
            if not (a['ok_airport'] and d['ok_airport']): continue
            if i >= 2 and seq[i - 2]['direction'] == 'arrival': continue
            rk = link.get(d['key'], '')
            r = A.loc[rk] if rk in A.index else None
            rows.append(dict(interval_id=f"BER|{a['key']}|{d['key']}", aircraft_icao24=ac, airport_icao='EDDB',
                             inbound_callsign=a['callsign'], outbound_callsign=d['callsign'], inbound_origin=a['origin'], outbound_destination=d['dest'],
                             inbound_last_seen_utc=iso(a['t']), outbound_first_seen_utc=iso(d['t']),
                             inbound_last_seen_berlin=iso(a['t'], BER), outbound_first_seen_berlin=iso(d['t'], BER),
                             departure_date_berlin=datetime.fromtimestamp(d['t'], BER).date().isoformat(), ground_interval_proxy_min=round(el, 6),
                             acdm_reference_key=rk, aircraft_type_from_candidate_acdm_reference=('' if r is None or pd.isna(r.aircraft_icao) else r.aircraft_icao),
                             airline_from_candidate_acdm_reference=('' if r is None or pd.isna(r.airline_icao) else r.airline_icao)))
    P = pd.DataFrame(rows)
    P['airline_icao'] = P.outbound_callsign.str.extract(r'^([A-Z]{3})\d')[0]
    P['airline_name'] = P.airline_icao.map(lambda c: AIRLINES.get(c, ('', ''))[0])
    P['carrier_class'] = P.airline_icao.map(lambda c: AIRLINES.get(c, ('', 'other'))[1])
    M = pd.read_csv(META, usecols=['icao24', 'typecode'], dtype=str).dropna(subset=['icao24'])
    M['icao24'] = M.icao24.str.lower(); M = M.drop_duplicates('icao24')
    P = P.merge(M.rename(columns={'typecode': 'type_opensky_meta'}), left_on='aircraft_icao24', right_on='icao24', how='left').drop(columns='icao24')
    t = P.aircraft_type_from_candidate_acdm_reference.fillna('').astype(str).str.upper().str.strip()
    P['aircraft_type'] = t.where(t != '', P.type_opensky_meta.fillna('').str.upper())
    P.loc[P.aircraft_type.isin(BIZ_TYPES), 'carrier_class'] = EXCL
    W = pd.DataFrame(json.loads(WEATHER.read_text())['hourly']); W['time'] = pd.to_datetime(W.time).dt.tz_localize('UTC')
    P['inb_hour'] = pd.to_datetime(P.inbound_last_seen_utc).dt.floor('h')
    P = P.merge(W.rename(columns={'time': 'inb_hour'}), on='inb_hour', how='left')
    P['in_scope'] = P.carrier_class != EXCL
    P.to_csv(OUT, index=False)
    print(len(P), 'pairs;', P.groupby(P.inbound_last_seen_berlin.str[:10]).size().to_dict(), 'linked', int((P.acdm_reference_key != '').sum()),
          P.carrier_class.value_counts().to_dict())


if __name__ == '__main__':
    main()
