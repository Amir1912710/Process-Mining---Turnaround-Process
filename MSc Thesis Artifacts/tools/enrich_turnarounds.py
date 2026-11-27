"""Enrich the 10,940 OpenSky turnaround candidates with airline, carrier class, aircraft type and weather.

Output: data/ber_history/prepared/ber_turnarounds_enriched.csv

Carrier class: the low-cost / full-service labels the author recorded in the Feb-Apr 2026
A-CDM collection are used where the airline appears there; other airlines are classified by
business model (table AIRLINES below, documented in the thesis appendix). Leisure/charter
carriers form their own analysis class and use the low-cost service profile in the model.
Non-passenger operations (military, business aviation, cargo) are excluded from the scope.
"""
import csv, json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/ber_history/prepared/ber_ground_intervals_core_proxy.csv'
META = Path(r'C:/Users/amira/Documents/GitHub/Process-Mining---Turnaround-Process/DS Lab2/data/raw/opensky_aircraft_metadata.csv')
WEATHER = ROOT / 'data/weather/ber_hourly_2026.json'
OUT = ROOT / 'data/ber_history/prepared/ber_turnarounds_enriched.csv'

LOW = 'low-cost'; FULL = 'full-service'; LEIS = 'leisure'; EXCL = 'excluded'
AIRLINES = {
    # low-cost (user's Feb-Apr labels: Ryanair, easyJet, Eurowings, Pegasus, Wizz Air, Vueling, Norwegian)
    'RYR': ('Ryanair', LOW), 'RUK': ('Ryanair UK', LOW), 'MAY': ('Malta Air', LOW), 'EJU': ('easyJet Europe', LOW),
    'EZY': ('easyJet', LOW), 'EZS': ('easyJet Switzerland', LOW), 'EWG': ('Eurowings', LOW), 'PGT': ('Pegasus Airlines', LOW),
    'WZZ': ('Wizz Air', LOW), 'WMT': ('Wizz Air Malta', LOW), 'WUK': ('Wizz Air UK', LOW), 'VLG': ('Vueling', LOW),
    'NOZ': ('Norwegian', LOW), 'NSZ': ('Norwegian Sweden', LOW), 'NAX': ('Norwegian', LOW), 'TKJ': ('AJet', LOW),
    'TVF': ('Transavia France', LOW), 'TRA': ('Transavia', LOW), 'VOE': ('Volotea', LOW),
    # leisure / charter
    'SXS': ('SunExpress', LEIS), 'CFG': ('Condor', LEIS), 'SDR': ('Sundair', LEIS), 'CAI': ('Corendon Airlines', LEIS),
    'CXI': ('Corendon Europe', LEIS), 'FHY': ('Freebird Airlines', LEIS), 'MSC': ('Air Cairo', LEIS), 'BBG': ('Bluebird Airways', LEIS),
    'LBT': ('Nouvelair', LEIS), 'TVS': ('Smartwings', LEIS), 'ISR': ('Israir', LEIS), 'NIA': ('Nile Air', LEIS), 'ENT': ('Enter Air', LEIS),
    # full-service / network (user's labels: Lufthansa, Austrian, Swiss, KLM, BA, Turkish, Air France, SAS, Brussels,
    # Finnair, Iberia, LOT, Qatar, Aer Lingus)
    'DLH': ('Lufthansa', FULL), 'LHX': ('Lufthansa City Airlines', FULL), 'AUA': ('Austrian Airlines', FULL), 'SWR': ('Swiss', FULL),
    'SWU': ('Swiss (Helvetic)', FULL), 'KLM': ('KLM', FULL), 'BAW': ('British Airways', FULL), 'CFE': ('BA CityFlyer', FULL),
    'THY': ('Turkish Airlines', FULL), 'AFR': ('Air France', FULL), 'HOP': ('Air France Hop', FULL), 'SAS': ('SAS', FULL),
    'BEL': ('Brussels Airlines', FULL), 'FIN': ('Finnair', FULL), 'IBE': ('Iberia', FULL), 'TAP': ('TAP Air Portugal', FULL),
    'LOT': ('LOT Polish Airlines', FULL), 'AEE': ('Aegean Airlines', FULL), 'QTR': ('Qatar Airways', FULL), 'BTI': ('airBaltic', FULL),
    'EIN': ('Aer Lingus', FULL), 'LGL': ('Luxair', FULL), 'UAL': ('United Airlines', FULL), 'ICE': ('Icelandair', FULL),
    'RJA': ('Royal Jordanian', FULL), 'MSR': ('EgyptAir', FULL), 'ELY': ('El Al', FULL), 'DAL': ('Delta Air Lines', FULL),
    'CHH': ('Hainan Airlines', FULL), 'MEA': ('Middle East Airlines', FULL), 'CTN': ('Croatia Airlines', FULL),
    'AHY': ('Azerbaijan Airlines', FULL), 'LZB': ('Bulgaria Air', FULL), 'SEH': ('Sky Express', FULL), 'TSC': ('Air Transat', FULL),
    # excluded: military, business aviation, cargo/ACMI
    'GAF': ('German Air Force', EXCL), 'NJE': ('NetJets Europe', EXCL), 'VJT': ('VistaJet', EXCL), 'ASL': ('ASL Airlines', EXCL),
    'SRR': ('Star Air', EXCL), 'TAY': ('ASL Belgium', EXCL), 'SWT': ('Swiftair', EXCL), 'DCS': ('DC Aviation', EXCL),
    'ADN': ('Aerodienst', EXCL), 'LEJ': ('FSH Luftfahrt', EXCL), 'QGA': ('Windrose', EXCL), 'KMM': ('business', EXCL),
    'FHM': ('business', EXCL), 'GAC': ('business', EXCL), 'MGH': ('business', EXCL), 'BFD': ('business', EXCL),
    'MMF': ('business', EXCL), 'TWI': ('business', EXCL), 'JFA': ('business', EXCL), 'ATV': ('Avanti Air', EXCL),
}
BIZ_TYPES = {'GLEX', 'GL5T', 'GL7T', 'CL30', 'CL35', 'CL60', 'E55P', 'E50P', 'C56X', 'C68A', 'C525', 'C25A', 'C25B', 'C510', 'C680',
             'C700', 'F2TH', 'F900', 'FA7X', 'FA8X', 'G280', 'GLF4', 'GLF5', 'GLF6', 'LJ45', 'LJ60', 'PC12', 'PC24', 'BE40', 'H25B', 'SB91'}


def main():
    P = pd.read_csv(SRC, low_memory=False)
    P['airline_icao'] = P.outbound_callsign.fillna('').str.strip().str.extract(r'^([A-Z]{3})\d')[0]
    P['airline_name'] = P.airline_icao.map(lambda c: AIRLINES.get(c, ('', ''))[0])
    P['carrier_class'] = P.airline_icao.map(lambda c: AIRLINES.get(c, ('', 'other'))[1])
    M = pd.read_csv(META, usecols=['icao24', 'typecode'], dtype=str).dropna(subset=['icao24'])
    M['icao24'] = M.icao24.str.lower(); M = M.drop_duplicates('icao24')
    P = P.merge(M.rename(columns={'typecode': 'type_opensky_meta'}), left_on='aircraft_icao24', right_on='icao24', how='left').drop(columns='icao24')
    acdm_type = P.aircraft_type_from_candidate_acdm_reference.fillna('').str.upper().str.strip()
    P['aircraft_type'] = acdm_type.where(acdm_type != '', P.type_opensky_meta.fillna('').str.upper())
    P.loc[P.aircraft_type.isin(BIZ_TYPES), 'carrier_class'] = EXCL
    w = json.loads(WEATHER.read_text())['hourly']
    W = pd.DataFrame(w); W['time'] = pd.to_datetime(W.time).dt.tz_localize('UTC')
    P['inb_hour'] = pd.to_datetime(P.inbound_last_seen_utc).dt.floor('h')
    P = P.merge(W.rename(columns={'time': 'inb_hour'}), on='inb_hour', how='left')
    P['in_scope'] = ~P.carrier_class.isin([EXCL])
    P.to_csv(OUT, index=False)
    s = P.groupby('carrier_class').size()
    print(s.to_dict(), 'in scope', int(P.in_scope.sum()), 'type known', round((P.aircraft_type != '').mean(), 3))


if __name__ == '__main__':
    main()
