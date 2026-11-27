"""Build provenance-preserving OpenSky BER intervals and A-CDM correspondence candidates.

Flight-list boundaries remain labeled proxies. No schedules, block times, aircraft
registrations or missing days are synthesized.
"""
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict, Counter
import csv
import hashlib
import json
import statistics

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/ber_history'
RAW = BASE / 'opensky'
OUT = BASE / 'prepared'
UTC = timezone.utc
BERLIN = ZoneInfo('Europe/Berlin')
START, END = date(2026, 10, 1), datetime.now(BERLIN).date()


def iso(timestamp, zone=UTC):
    return datetime.fromtimestamp(timestamp, zone).isoformat()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, rows, columns):
    with (OUT / name).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    events, manifests, seen, rejected = [], {}, {}, []
    for path in sorted(RAW.glob('*/*_manifest.json')):
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifests[(path.parent.name, manifest['direction'])] = manifest
        if manifest['status'] != 'collected':
            continue
        raw_path = path.with_name(manifest['direction']+'.json')
        if digest(raw_path) != manifest['sha256']:
            raise ValueError(f'Raw data changed: {raw_path}')
        data = json.loads(raw_path.read_text())
        if len(data) != manifest['rows']:
            raise ValueError('Manifest row mismatch')
        for flight in data:
            direction = manifest['direction']
            boundary = flight.get('lastSeen') if direction == 'arrival' else flight.get('firstSeen')
            if not flight.get('icao24') or not isinstance(boundary, (int, float)):
                rejected.append({'source_file':str(raw_path.relative_to(ROOT)),
                                 'direction':direction, 'reason':'missing_identity_or_relevant_boundary',
                                 'record_json':json.dumps(flight,sort_keys=True)})
                continue
            key = (flight['icao24'].lower(), flight['firstSeen'], flight['lastSeen'], direction)
            if key in seen:
                if seen[key] != flight:
                    raise ValueError('Conflicting duplicate flight; review before choosing a version')
                continue
            seen[key] = flight
            flags = []
            airport_field = 'estArrivalAirport' if direction == 'arrival' else 'estDepartureAirport'
            if flight.get(airport_field) != 'EDDB':
                flags.append('airport_mismatch')
            if flight['firstSeen'] is None or flight['lastSeen'] is None:
                flags.append('missing_opposite_flight_boundary')
            elif flight['lastSeen'] < flight['firstSeen']:
                flags.append('negative_flight_duration')
            event = {'flight_key': '|'.join(map(str, key)), 'icao24': key[0],
                     'direction': direction, 'callsign': (flight.get('callsign') or '').strip().upper(),
                     'first_seen_epoch': flight['firstSeen'], 'last_seen_epoch': flight['lastSeen'],
                     'first_seen_utc': iso(flight['firstSeen']) if flight['firstSeen'] is not None else '',
                     'last_seen_utc': iso(flight['lastSeen']) if flight['lastSeen'] is not None else '',
                     'boundary_epoch': boundary, 'boundary_utc': iso(boundary),
                     'boundary_berlin': iso(boundary, BERLIN),
                     'berlin_date': datetime.fromtimestamp(boundary, BERLIN).date().isoformat(),
                     'estimated_origin': flight.get('estDepartureAirport') or '',
                     'estimated_destination': flight.get('estArrivalAirport') or '',
                     'airport_horizontal_distance_m': flight.get('estArrivalAirportHorizDistance' if direction=='arrival' else 'estDepartureAirportHorizDistance'),
                     'airport_vertical_distance_m': flight.get('estArrivalAirportVertDistance' if direction=='arrival' else 'estDepartureAirportVertDistance'),
                     'other_airport_candidates': flight.get('arrivalAirportCandidatesCount' if direction=='arrival' else 'departureAirportCandidatesCount'),
                     'source_file': str(raw_path.relative_to(ROOT)), 'source_sha256': manifest['sha256'],
                     'quality_flags': ';'.join(flags)}
            events.append(event)
    events.sort(key=lambda r: (r['icao24'], r['boundary_epoch'], r['direction']))
    coverage=[]
    for offset in range((END-START).days+1):
        day=START+timedelta(days=offset)
        row={'date_berlin':str(day)}
        for direction in ['arrival','departure']:
            m=manifests.get((str(day),direction),{})
            row[direction+'_status']=m.get('status','not_collected')
            row[direction+'_rows_returned']=m.get('rows','')
            row[direction+'_unique_boundary_rows']=sum(e['direction']==direction and e['berlin_date']==str(day) for e in events)
        row['coverage_review']=('missing_or_unavailable_query' if any(row[k+'_status']!='collected' for k in ['arrival','departure'])
                                else 'sparse_return_under_100_movements_per_direction' if any(row[k+'_unique_boundary_rows']<100 for k in ['arrival','departure'])
                                else 'no_low_count_flag_not_proof_of_completeness')
        coverage.append(row)
    groups=defaultdict(list)
    for event in events:
        groups[event['icao24']].append(event)
    pairs=[]
    paired_departures=set()
    for aircraft, sequence in groups.items():
        for i,event in enumerate(sequence):
            if event['direction']!='departure' or not START<=date.fromisoformat(event['berlin_date'])<=END:
                continue
            if i==0 or sequence[i-1]['direction']!='arrival':
                continue
            arrival=sequence[i-1]
            elapsed=(event['boundary_epoch']-arrival['boundary_epoch'])/60
            flags=[]
            if elapsed<=0:
                flags.append('nonpositive_interval')
            if i>=2 and sequence[i-2]['direction']=='arrival':
                flags.append('consecutive_arrivals_coverage_or_identity_review')
            if arrival['quality_flags'] or event['quality_flags']:
                flags.append('source_record_flag')
            if elapsed>1440:
                flags.append('over_24h_parking_or_missing_rotation_review')
            if elapsed<15:
                flags.append('under_15min_review')
            first_day=date.fromisoformat(arrival['berlin_date']);last_day=date.fromisoformat(event['berlin_date'])
            for d in range((last_day-first_day).days+1):
                for direction in ['arrival','departure']:
                    if manifests.get((str(first_day+timedelta(days=d)),direction),{}).get('status')!='collected':
                        flags.append('incomplete_day_coverage');break
                    if manifests.get((str(first_day+timedelta(days=d)),direction),{}).get('rows',0)<100:
                        flags.append('sparse_day_coverage_review')
            flags=list(dict.fromkeys(flags))
            pairs.append({'interval_id':'BER|'+arrival['flight_key']+'|'+event['flight_key'],
                          'aircraft_icao24':aircraft, 'airport_icao':'EDDB',
                          'inbound_callsign':arrival['callsign'],'outbound_callsign':event['callsign'],
                          'inbound_origin':arrival['estimated_origin'],'outbound_destination':event['estimated_destination'],
                          'inbound_last_seen_utc':arrival['boundary_utc'],'outbound_first_seen_utc':event['boundary_utc'],
                          'inbound_last_seen_berlin':arrival['boundary_berlin'],'outbound_first_seen_berlin':event['boundary_berlin'],
                          'departure_date_berlin':event['berlin_date'],'ground_interval_proxy_min':round(elapsed,6),
                          'descriptive_duration_band':('under_15min' if elapsed<15 else '15min_to_6h' if elapsed<=360
                                                       else '6h_to_24h' if elapsed<=1440 else 'over_24h'),
                          'actual_landing_time':'','actual_inblock_time':'','actual_offblock_time':'','actual_takeoff_time':'',
                          'timing_basis':'OpenSky observed flight-boundary proxy',
                          'pairing_basis':'adjacent observed BER arrival/departure with same ICAO24',
                          'review_flags':';'.join(flags),'eligible_core_proxy_cohort':not flags,
                          'inbound_airport_distance_m':arrival['airport_horizontal_distance_m'],
                          'outbound_airport_distance_m':event['airport_horizontal_distance_m'],
                          'inbound_other_airport_candidates':arrival['other_airport_candidates'],
                          'outbound_other_airport_candidates':event['other_airport_candidates'],
                          'inbound_source_file':arrival['source_file'],'outbound_source_file':event['source_file'],
                          'outbound_flight_key':event['flight_key']})
            paired_departures.add(event['flight_key'])
    # Reference correspondence is deliberately separate from inferred aircraft pairing.
    # Both timezone hypotheses are retained; proximity is not proof of timezone.
    references=[]
    ref_path=ROOT/'data/acdm/prepared/ber_departures_prepared.csv'
    with ref_path.open(encoding='utf-8-sig',newline='') as handle:acdm=list(csv.DictReader(handle))
    primary_count=len(acdm)
    primary_ids={r['id'] for r in acdm}
    for row in acdm:row['reference_scope']='finalized_daily_snapshot'
    observations=defaultdict(list)
    for path in sorted(list((ROOT/'data/acdm/raw').glob('*/*.json'))+
                       list((BASE/'acdm_current_reference').rglob('page_*.json'))):
        doc=json.loads(path.read_text(encoding='utf-8'))
        for raw in doc.get('data',[]):
            if raw.get('atot') and START.isoformat()<=str(raw.get('std',''))[:10]<=END.isoformat():
                observations[str(raw['id'])].append((raw,str(path.relative_to(ROOT))))
    observed=[]
    for identity,versions in observations.items():
        versions.sort(key=lambda item:(item[0].get('updated_at') or '',item[1]))
        raw,path=versions[-1]
        ref={key:'' if value is None else str(value) for key,value in raw.items()}
        atot_variants={r.get('atot') for r,_ in versions}
        observed.append({'source_record_id':identity,'std_source_naive':raw['std'],
                         'callsign':raw.get('callsign') or '', 'registration':raw.get('aircraft_reg') or '',
                         'actual_takeoff_source_naive':raw['atot'],'flight_number':raw.get('flight_number_trim') or '',
                         'reference_scope':'finalized_daily_snapshot' if identity in primary_ids else 'supplemental_observation_partial_day',
                         'source_file':path,'observation_occurrences':len(versions),
                         'distinct_atot_values':len(atot_variants),'timestamp_timezone':'unverified_naive'})
        if identity not in primary_ids and len(atot_variants)==1:
            ref.update(record_key='supplemental:'+identity,reference_scope='supplemental_observation_partial_day')
            acdm.append(ref)
    write('ber_acdm_observed_takeoffs.csv',observed,list(observed[0]) if observed else
          ['source_record_id','std_source_naive','callsign','registration','actual_takeoff_source_naive'])
    by_callsign=defaultdict(list)
    for event in events:
        if event['direction']=='departure' and event['callsign']:
            by_callsign[event['callsign']].append(event)
    for ref in acdm:
        row={'acdm_record_key':ref['record_key'],'aircraft_registration_reference':ref['aircraft_reg'],
             'reference_scope':ref['reference_scope'],
             'aircraft_type_reference':ref['aircraft_icao'],'airline_reference':ref['airline_icao'],
             'stand_reference':ref['parking_pos'],'runway_reference':ref['runway'],
             'tobt_reference_naive':ref['tobt'],'tsat_reference_naive':ref['tsat'],
             'callsign':ref['callsign'],'acdm_atot_naive':ref['atot'],
             'status':'no_actual_takeoff' if not ref['atot'] else 'no_correspondence_within_30min',
             'opensky_flight_key':'','opensky_icao24':'','opensky_first_seen_utc':'',
             'timezone_hypothesis':'','delta_proxy_minus_acdm_min':'','candidate_count':0}
        if ref['atot']:
            parsed=datetime.fromisoformat(ref['atot']);candidates=[]
            for hypothesis,zone in [('ACDM_is_UTC',UTC),('ACDM_is_Europe_Berlin',BERLIN)]:
                target=parsed.replace(tzinfo=zone).timestamp()
                for event in by_callsign[ref['callsign'].strip().upper()]:
                    delta=(event['boundary_epoch']-target)/60
                    if abs(delta)<=30:
                        candidates.append((event,hypothesis,delta))
            row['candidate_count']=len(candidates)
            if len(candidates)==1:
                event,hypothesis,delta=candidates[0]
                row.update(status='unique_callsign_time_candidate_not_identity_verification',
                           opensky_flight_key=event['flight_key'],opensky_icao24=event['icao24'],
                           opensky_first_seen_utc=event['boundary_utc'],timezone_hypothesis=hypothesis,
                           delta_proxy_minus_acdm_min=round(delta,6))
            elif candidates:
                row['status']='ambiguous_callsign_time_candidates'
        references.append(row)
    reference_groups=defaultdict(list)
    for row in references:
        if row['opensky_flight_key']:
            reference_groups[row['opensky_flight_key']].append(row)
    for group in reference_groups.values():
        if len(group)>1:
            for row in group:
                row['status']='multiple_acdm_rows_for_opensky_flight_review'
    unique_reference={key:group[0] for key,group in reference_groups.items()
                      if len(group)==1 and group[0]['status']=='unique_callsign_time_candidate_not_identity_verification'}
    for row in pairs:
        ref=unique_reference.get(row['outbound_flight_key'],{})
        row.update(acdm_reference_key=ref.get('acdm_record_key',''),
                   registration_from_candidate_acdm_reference=ref.get('aircraft_registration_reference',''),
                   aircraft_type_from_candidate_acdm_reference=ref.get('aircraft_type_reference',''),
                   airline_from_candidate_acdm_reference=ref.get('airline_reference',''),
                   stand_from_candidate_acdm_reference=ref.get('stand_reference',''),
                   runway_from_candidate_acdm_reference=ref.get('runway_reference',''),
                   tobt_from_candidate_acdm_reference_naive=ref.get('tobt_reference_naive',''),
                   tsat_from_candidate_acdm_reference_naive=ref.get('tsat_reference_naive',''),
                   acdm_actual_takeoff_naive=ref.get('acdm_atot_naive',''),
                   acdm_timezone_hypothesis=ref.get('timezone_hypothesis',''),
                   opensky_departure_minus_acdm_min=ref.get('delta_proxy_minus_acdm_min',''),
                   acdm_match_basis='unique callsign/time candidate; identity not independently verified' if ref else '')
    requested_events=[e for e in events if START<=date.fromisoformat(e['berlin_date'])<=END]
    if events:write('ber_movements_opensky.csv',requested_events,list(events[0]))
    write('movement_records_for_review.csv',rejected,['source_file','direction','reason','record_json'])
    if pairs:
        write('ber_ground_intervals_proxy.csv',pairs,list(pairs[0]))
        write('ber_ground_intervals_core_proxy.csv',[r for r in pairs if r['eligible_core_proxy_cohort']],list(pairs[0]))
    write('daily_coverage.csv',coverage,list(coverage[0]))
    write('acdm_crosscheck_candidates.csv',references,list(references[0]))
    unmatched=[e for e in events if e['direction']=='departure' and START<=date.fromisoformat(e['berlin_date'])<=END
               and e['flight_key'] not in paired_departures]
    if events:write('unpaired_departures.csv',unmatched,list(events[0]))
    summary={'requested_start':str(START),'requested_end':str(END),'date_basis':'Europe/Berlin',
             'unique_movement_records':len(requested_events),
             'movement_counts':dict(Counter(e['direction'] for e in requested_events)),
             'support_boundary_movement_records':len(events)-len(requested_events),
             'unusable_movement_records':len(rejected),
             'candidate_proxy_intervals':len(pairs),'core_proxy_intervals':sum(r['eligible_core_proxy_cohort'] for r in pairs),
             'unpaired_departures':len(unmatched),'exact_landing_to_takeoff_intervals':0,
             'acdm_finalized_reference_records':primary_count,
             'acdm_reference_records_including_supplemental':len(references),
             'acdm_observed_takeoff_records':len(observed),
             'acdm_finalized_crosscheck_status':dict(Counter(r['status'] for r in references if r['reference_scope']=='finalized_daily_snapshot')),
             'acdm_crosscheck_status':dict(Counter(r['status'] for r in references)),
             'acdm_unique_candidate_timezone_hypotheses':dict(Counter(r['timezone_hypothesis'] for r in unique_reference.values())),
             'intervals_with_candidate_acdm_reference':sum(bool(r['acdm_reference_key']) for r in pairs),
             'acdm_unique_candidate_median_delta_min':statistics.median(
                 [r['delta_proxy_minus_acdm_min'] for r in unique_reference.values()]) if unique_reference else None,
             'pair_review_flags':dict(Counter(flag for r in pairs for flag in r['review_flags'].split(';') if flag)),
             'dates_with_both_queries_successful':sum(all(r[k+'_status']=='collected' for k in ['arrival','departure']) for r in coverage),
             'dates_without_low_count_or_missing_query_flags':sum(r['coverage_review']=='no_low_count_flag_not_proof_of_completeness' for r in coverage),
             'build_script_sha256':digest(Path(__file__)),
             'warning':'Core means no listed pairing review flags, not ground-truth landing/block times or verified full coverage.'}
    (OUT/'audit.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    build()
