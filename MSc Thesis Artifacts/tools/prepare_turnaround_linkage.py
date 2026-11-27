"""Build an honest arrival-linkage worklist from collected BER departures.

No arrivals are inferred. Run after prepare_acdm.py. A pending row is not a
complete turnaround, and repeated departures of one registration are not paired
as a landing-to-takeoff interval.
"""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
PREPARED = ROOT / 'data/acdm/prepared'


def main():
    source = PREPARED / 'ber_departures_prepared.csv'
    with source.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    output = []
    for row in rows:
        registration = ''.join(c for c in row['aircraft_reg'].upper() if c.isalnum())
        reason = 'arrival_observation_missing'
        if not registration:
            reason += ';aircraft_registration_missing'
        if not row['atot']:
            reason += ';actual_takeoff_missing'
        if row['flight_status'] == 'XLD':
            reason += ';departure_canceled'
        output.append({
            'departure_record_key': row['record_key'],
            'airport': 'BER',
            'aircraft_registration_source': row['aircraft_reg'],
            'aircraft_registration_match_key': registration,
            'inbound_record_id': '',
            'inbound_flight_number': '',
            'actual_landing_time': '',
            'actual_inblock_time': '',
            'outbound_record_id': row['id'],
            'outbound_flight_id': row['flight_id'],
            'outbound_flight_number': row['flight_number_trim'],
            'destination': row['dest_iata'],
            'scheduled_departure_source': row['std'],
            'target_offblock_time': row['tobt'],
            'target_startup_time': row['tsat'],
            'actual_offblock_time': '',
            'actual_takeoff_time': row['atot'],
            'landing_to_takeoff_min': '',
            'inblock_to_offblock_min': '',
            'is_complete_turnaround': False,
            'linkage_status': reason,
            'timestamp_timezone': row['timestamp_timezone'],
            'departure_source_file': row['source_file'],
            'departure_source_row': row['source_row'],
        })
    dest = PREPARED / 'turnaround_linkage_pending.csv'
    with dest.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    audit = {
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'source_departures': len(rows),
        'complete_landing_to_takeoff_turnarounds': 0,
        'complete_inblock_to_offblock_turnarounds': 0,
        'missing_registration': sum(not r['aircraft_registration_match_key'] for r in output),
        'with_registration_and_actual_takeoff': sum(bool(r['aircraft_registration_match_key'] and r['actual_takeoff_time'])
                                                   and 'departure_canceled' not in r['linkage_status'] for r in output),
        'linkage_status_counts': dict(Counter(r['linkage_status'] for r in output)),
        'arrival_fields_imputed': 0,
        'matching_rule': 'No arrival source exists in collected A-CDM pages; no joins performed.',
    }
    (PREPARED / 'turnaround_linkage_audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
