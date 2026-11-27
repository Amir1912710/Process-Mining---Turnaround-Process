"""Collect EDDB airport flight lists with provenance, caching and conservative retries.

OAuth credentials are read from Windows DPAPI storage. No token is written to disk.
Dates are Berlin calendar dates, including DST. Current-day flight lists await
OpenSky's nightly processing; the requested end date remains in coverage reporting.
"""
from pathlib import Path
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
import argparse
import hashlib
import json
import time as clock
import shutil
from opensky_access_check import get_token

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/ber_history/opensky'
BERLIN = ZoneInfo('Europe/Berlin')
UTC = timezone.utc


def utc_now():
    return datetime.now(UTC).isoformat()


def bounds(day):
    return (int(datetime.combine(day, time(), BERLIN).timestamp()),
            int(datetime.combine(day + timedelta(days=1), time(), BERLIN).timestamp()))


def collect(start, end, max_requests=100, refresh=False):
    BASE.mkdir(parents=True, exist_ok=True)
    today = datetime.now(BERLIN).date()
    token, token_time = None, 0
    requests = 0
    for offset in range((end-start).days + 1):
        day = start + timedelta(days=offset)
        folder = BASE / day.isoformat()
        folder.mkdir(exist_ok=True)
        for direction in ['arrival', 'departure']:
            status_path = folder / (direction + '_manifest.json')
            raw_path = folder / (direction + '.json')
            if status_path.exists():
                prior = json.loads(status_path.read_text(encoding='utf-8'))
                if prior.get('status') == 'collected' and raw_path.exists() and not refresh:
                    if hashlib.sha256(raw_path.read_bytes()).hexdigest() != prior['sha256']:
                        raise ValueError(f'Cached raw hash mismatch: {raw_path}')
                    continue
                if prior.get('retry_not_before_utc'):
                    if datetime.now(UTC) < datetime.fromisoformat(prior['retry_not_before_utc']):
                        print(json.dumps({'status': 'backoff_active', 'date': str(day)}), flush=True)
                        return
            begin, finish = bounds(day)
            url = 'https://opensky-network.org/api/flights/' + direction + '?' + urlencode(
                {'airport': 'EDDB', 'begin': begin, 'end': finish})
            meta = {'date_berlin': str(day), 'direction': direction, 'airport': 'EDDB',
                    'query_begin_utc': datetime.fromtimestamp(begin, UTC).isoformat(),
                    'query_end_utc': datetime.fromtimestamp(finish, UTC).isoformat(),
                    'url': url, 'attempted_utc': utc_now(),
                    'timestamp_semantics': 'firstSeen/lastSeen inferred flight boundaries; not actual block times'}
            if day >= today:
                meta['status'] = 'awaiting_nightly_processing'
                status_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')
                continue
            if requests >= max_requests:
                return
            if token is None or clock.monotonic()-token_time > 1500:
                token, token_time = get_token(), clock.monotonic()
            req = Request(url, headers={'Authorization': 'Bearer ' + token,
                                        'Accept': 'application/json', 'User-Agent': 'BER-thesis-research/1.0'})
            requests += 1
            try:
                with urlopen(req, timeout=40) as response:
                    body, status = response.read(), response.status
                    meta['rate_headers'] = {k: v for k, v in response.headers.items()
                                            if k.lower().startswith('x-rate') or k.lower()=='retry-after'}
                data = json.loads(body)
                if not isinstance(data, list) or any(not isinstance(r, dict) for r in data):
                    raise ValueError('API did not return a list of flight records')
                required = {'icao24', 'firstSeen', 'lastSeen'}
                if any(not required.issubset(r) for r in data):
                    raise ValueError('Flight records lack required identity/time fields')
                if raw_path.exists() and status_path.exists():
                    archive=folder/'previous_versions'/datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')
                    archive.mkdir(parents=True)
                    shutil.copy2(raw_path,archive/raw_path.name)
                    shutil.copy2(status_path,archive/status_path.name)
                raw_path.write_bytes(body)
                meta.update(status='collected', http_status=status, rows=len(data),
                            sha256=hashlib.sha256(body).hexdigest(), finished_utc=utc_now())
            except HTTPError as error:
                meta.update(status='http_error', http_status=error.code)
                text = error.read().decode(errors='replace')
                # Store only known short failure categories; avoid arbitrary echoed auth data.
                meta['error_category'] = ('historical_access_denied' if 'historical flights' in text
                                          else 'rate_limited' if error.code == 429 else f'http_{error.code}')
                retry = error.headers.get('Retry-After')
                if error.code == 429:
                    try:
                        retry_seconds = max(int(retry), 60)
                    except (ValueError, TypeError):
                        retry_seconds = 3600
                    meta['retry_not_before_utc'] = (datetime.now(UTC)+timedelta(seconds=retry_seconds)).isoformat()
                status_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')
                print(json.dumps({'date': str(day), 'direction': direction,
                                  'status': meta['status'], 'http_status': error.code}), flush=True)
                if error.code in [401, 403, 429]:
                    return
                continue
            except (URLError, TimeoutError) as error:
                meta.update(status='network_error', error_type=type(error).__name__)
                status_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')
                print(json.dumps({'date': str(day), 'direction': direction, 'status': 'network_error'}), flush=True)
                return
            status_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')
            print(json.dumps({'date': str(day), 'direction': direction,
                              'status': meta['status'], 'rows': meta.get('rows')}), flush=True)
            clock.sleep(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--start', type=date.fromisoformat, default=date(2026, 10, 1))
    p.add_argument('--end', type=date.fromisoformat, default=datetime.now(BERLIN).date())
    p.add_argument('--max-requests', type=int, default=100)
    p.add_argument('--refresh', action='store_true', help='Refresh selected days, preserving earlier successful responses')
    a = p.parse_args()
    if a.end < a.start:
        p.error('end precedes start')
    collect(a.start, a.end, a.max_requests,a.refresh)
