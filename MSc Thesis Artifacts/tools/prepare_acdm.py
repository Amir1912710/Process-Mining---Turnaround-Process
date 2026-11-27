"""Prepare finalized BER snapshots without changing source data or inventing milestones.

Run from any directory: python tools/prepare_acdm.py
Uses the standard library only; makes no network requests.
"""
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
import csv
import hashlib
import json
import statistics

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/acdm/days'
OUT = ROOT / 'data/acdm/prepared'
TIMES = ['std', 'eobt', 'ctot', 'tobt', 'tsat', 'atot', 'updated_at']
METRICS = {
    'tsat_minus_tobt_min': ('tsat', 'tobt'),
    'atot_minus_tsat_min': ('atot', 'tsat'),
    'atot_minus_tobt_min': ('atot', 'tobt'),
    'tobt_minus_std_min': ('tobt', 'std'),
    'atot_minus_ctot_min': ('atot', 'ctot'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows, columns):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='raise')
        writer.writeheader()
        writer.writerows(rows)


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    records, sources, original_columns = [], [], []
    for path in sorted(SOURCE.glob('*/flights.csv')):
        manifest_path = path.with_name('manifest.json')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('status') != 'collected_snapshot':
            raise ValueError(f'Unrecognized source status: {manifest_path}')
        with path.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames
            rows = list(reader)
        if not columns or not set(TIMES + ['id', 'flight_status']).issubset(columns):
            raise ValueError(f'Missing required source columns: {path}')
        if len(rows) != manifest['requested_day_records']:
            raise ValueError(f'Manifest count mismatch: {path}')
        # Check the corresponding JSON snapshot represents exactly the CSV content.
        json_path = path.with_suffix('.json')
        json_rows = json.loads(json_path.read_text(encoding='utf-8'))
        if not isinstance(json_rows, list):
            raise ValueError(f'Unexpected JSON snapshot structure: {json_path}')
        as_csv = lambda row: {k: '' if row.get(k) is None else str(row.get(k, '')) for k in columns}
        if [as_csv(row) for row in json_rows] != rows:
            raise ValueError(f'CSV/JSON content mismatch: {path}')
        for raw in manifest.get('raw_pages', []):
            if sha(ROOT / raw['path']) != raw['sha256']:
                raise ValueError(f'Raw response hash mismatch: {raw["path"]}')
        original_columns.extend(k for k in columns if k not in original_columns)
        sources.append({'date': path.parent.name, 'rows': len(rows),
                        'csv_sha256': sha(path), 'json_sha256': sha(json_path),
                        'manifest_sha256': sha(manifest_path),
                        'collection_finished_utc': manifest.get('collection_finished_utc'),
                        'full_day_completeness': manifest.get('full_day_completeness')})
        for number, raw in enumerate(rows, 2):
            records.append((raw, path.parent.name, str(path.relative_to(ROOT)), number))
    if not records:
        raise ValueError('No finalized snapshots found')

    # No automatic choice of a "latest" record if source identity is ambiguous.
    ids = Counter(raw['id'].strip() for raw, *_ in records)
    prepared, quality = [], []
    for raw, day, source, number in records:
        row = {k: raw.get(k, '') for k in original_columns}
        flags, parsed = [], {}
        for field in TIMES:
            value = raw[field].strip()
            try:
                parsed[field] = datetime.fromisoformat(value) if value else None
                if parsed[field] and parsed[field].tzinfo is not None:
                    flags.append(f'unexpected_timezone_{field}')
            except ValueError:
                parsed[field] = None
                flags.append(f'invalid_{field}')
            row[field + '_parsed'] = parsed[field].isoformat(sep=' ') if parsed[field] else ''
        if not raw['id'].strip():
            flags.append('missing_id')
        if ids[raw['id'].strip()] > 1:
            flags.append('duplicate_id_review')
        if not parsed['std']:
            flags.append('missing_or_invalid_std')
        elif parsed['std'].date().isoformat() != day:
            flags.append('std_date_mismatch')
        if raw.get('dep_airport_iata') != 'BER':
            flags.append('airport_mismatch')
        for field in ['tobt', 'tsat', 'atot', 'aircraft_reg', 'parking_pos', 'runway']:
            if not raw.get(field, '').strip():
                flags.append('missing_' + field)
        canceled = raw['flight_status'].strip() == 'XLD'
        if canceled:
            flags.append('canceled')
        if not canceled and not parsed['atot']:
            flags.append('no_actual_takeoff')
        for name, (later, earlier) in METRICS.items():
            a, b = parsed[later], parsed[earlier]
            value = None
            if a is not None and b is not None and a.tzinfo == b.tzinfo:
                value = (a - b).total_seconds() / 60
            row[name] = round(value, 6) if value is not None else ''
        for metric in ['tsat_minus_tobt_min', 'atot_minus_tsat_min', 'atot_minus_tobt_min']:
            if row[metric] != '' and row[metric] < 0:
                flags.append('negative_' + metric)
        if parsed['atot'] and parsed['updated_at'] and parsed['atot'].tzinfo == parsed['updated_at'].tzinfo:
            if parsed['updated_at'] < parsed['atot']:
                flags.append('updated_before_atot_review')
        structural = any(f in flags for f in ['missing_id', 'duplicate_id_review',
                         'missing_or_invalid_std', 'std_date_mismatch', 'airport_mismatch'])
        structural = structural or any(f.startswith('unexpected_timezone_') for f in flags)
        actual_ok = not structural and not canceled and parsed['atot'] is not None
        pair_ok = actual_ok and all(parsed[k] is not None for k in ['tobt', 'tsat'])
        coherent = pair_ok and all(row[k] >= 0 for k in
                                 ['tsat_minus_tobt_min', 'atot_minus_tsat_min', 'atot_minus_tobt_min'])
        row.update(source_day=day, source_file=source, source_row=number,
                   record_key=f'{day}:{raw["id"]}', timestamp_timezone='unverified_naive',
                   time_of_day_std_hour=parsed['std'].hour if parsed['std'] else '',
                   usable_actual_takeoff=bool(actual_ok),
                   usable_target_takeoff_pairs=bool(pair_ok),
                   usable_nonnegative_target_sequence=bool(coherent),
                   suggested_pilot_partition='held_out' if day == sources[-1]['date'] else 'calibration',
                   quality_flags=';'.join(flags))
        prepared.append(row)
        for flag in flags:
            quality.append({'record_key': row['record_key'], 'source_file': source,
                            'source_row': number, 'flag': flag})
    write_csv(OUT / 'ber_departures_prepared.csv', prepared, list(prepared[0]))
    write_csv(OUT / 'quality_flags.csv', quality, ['record_key', 'source_file', 'source_row', 'flag'])
    # Explicit cohorts rather than deleting anomalies from the master dataset.
    for name, key in [('actual_takeoffs', 'usable_actual_takeoff'),
                      ('target_takeoff_pairs', 'usable_target_takeoff_pairs'),
                      ('nonnegative_target_sequence', 'usable_nonnegative_target_sequence')]:
        write_csv(OUT / f'{name}.csv', [r for r in prepared if r[key]], list(prepared[0]))
    summary = {'sources': sources, 'input_records': len(records), 'prepared_records': len(prepared),
               'cohorts': {k: sum(r[k] for r in prepared) for k in
                          ['usable_actual_takeoff', 'usable_target_takeoff_pairs', 'usable_nonnegative_target_sequence']},
               'flags': dict(Counter(r['flag'] for r in quality)),
               'status_counts': dict(Counter(r['flight_status'] for r in prepared)),
               'missing': {k: sum(not r.get(k, '').strip() for r in prepared) for k in original_columns},
               'script_sha256': sha(Path(__file__)),
               'timezone': 'Unverified; no timezone assigned or conversion performed',
               'partition': 'Latest available source date held out; suggestion only, not fitted or evaluated',
               'metrics': {}}
    for metric in METRICS:
        values = [r[metric] for r in prepared if r[metric] != '']
        summary['metrics'][metric] = {'n': len(values), 'mean': statistics.mean(values) if values else None,
                                     'median': statistics.median(values) if values else None}
    (OUT / 'audit.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


if __name__ == '__main__':
    result = prepare()
    print(json.dumps({k: result[k] for k in ['input_records', 'prepared_records', 'cohorts', 'flags']}, indent=2))
