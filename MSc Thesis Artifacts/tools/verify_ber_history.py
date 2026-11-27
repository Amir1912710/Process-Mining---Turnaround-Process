"""Independent integrity checks of the exported BER dataset and its source links."""
from pathlib import Path
from datetime import datetime, date
from collections import Counter
import csv
import json

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data/ber_history/prepared'


def read(name):
    with (P/name).open(encoding='utf-8',newline='') as handle:
        return list(csv.DictReader(handle))


def verify():
    movements=read('ber_movements_opensky.csv')
    pairs=read('ber_ground_intervals_proxy.csv')
    core=read('ber_ground_intervals_core_proxy.csv')
    refs=read('acdm_crosscheck_candidates.csv')
    coverage=read('daily_coverage.csv')
    assert len({r['flight_key'] for r in movements})==len(movements)
    assert len({r['interval_id'] for r in pairs})==len(pairs)
    assert len({r['outbound_flight_key'] for r in pairs})==len(pairs)
    cached={}
    for row in pairs:
        records=[]
        for column in ['inbound_source_file','outbound_source_file']:
            path=row[column]
            if path not in cached:
                cached[path]=json.loads((ROOT/path).read_text(encoding='utf-8'))
            records.append(cached[path])
        a=datetime.fromisoformat(row['inbound_last_seen_utc'])
        b=datetime.fromisoformat(row['outbound_first_seen_utc'])
        assert abs((b-a).total_seconds()/60-float(row['ground_interval_proxy_min']))<1e-6
        assert any(r['icao24']==row['aircraft_icao24'] and r['lastSeen']==int(a.timestamp())
                   and r['estArrivalAirport']=='EDDB' for r in records[0])
        assert any(r['icao24']==row['aircraft_icao24'] and r['firstSeen']==int(b.timestamp())
                   and r['estDepartureAirport']=='EDDB' for r in records[1])
        assert not any(row[k] for k in ['actual_landing_time','actual_inblock_time','actual_offblock_time','actual_takeoff_time'])
    assert {r['interval_id'] for r in core}=={r['interval_id'] for r in pairs if r['eligible_core_proxy_cohort']=='True'}
    assert all(not r['review_flags'] for r in core)
    unique=[r for r in refs if r['status']=='unique_callsign_time_candidate_not_identity_verification']
    assert len({r['opensky_flight_key'] for r in unique})==len(unique)
    assert all(abs(float(r['delta_proxy_minus_acdm_min']))<=30 for r in unique)
    audit=json.loads((P/'audit.json').read_text())
    assert audit['candidate_proxy_intervals']==len(pairs)
    assert audit['core_proxy_intervals']==len(core)
    assert len(coverage)==(date.fromisoformat(audit['requested_end'])-date.fromisoformat(audit['requested_start'])).days+1
    assert len(pairs)+len(read('unpaired_departures.csv'))==sum(r['direction']=='departure' for r in movements)
    assert all(audit['requested_start']<=r['berlin_date']<=audit['requested_end'] for r in movements)
    result={'verified_pairs':len(pairs),'verified_core_pairs':len(core),'unique_reference_candidates':len(unique),
            'checks':'source aircraft/airport/time links, interval arithmetic, no invented actual timestamps, cohort membership, reference uniqueness, coverage and departure reconciliation'}
    (P/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    verify()
