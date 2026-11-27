"""Probe authenticated OpenSky history; never print credentials or access tokens."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
import json
from acdm_probe import protect

ROOT = Path(__file__).resolve().parents[1]
AUTH = 'https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token'


def get_token():
    p = ROOT / '.secrets/opensky-credentials.dpapi'
    c = json.loads(protect(p.read_bytes(), decrypt=True))
    body = urlencode({'grant_type': 'client_credentials',
                      'client_id': c.get('clientId', c.get('client_id')),
                      'client_secret': c.get('clientSecret', c.get('client_secret'))}).encode()
    req = Request(AUTH, data=body, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urlopen(req, timeout=40) as response:
            return json.load(response)['access_token']
    except HTTPError as e:
        raise RuntimeError(f'OpenSky authentication failed: HTTP {e.code}') from None


def main():
    out = ROOT / 'data/ber_history/access_checks'
    out.mkdir(parents=True, exist_ok=True)
    token = get_token()
    for day in ['2026-10-01', '2026-11-08']:
        a = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())
        query = urlencode({'airport': 'EDDB', 'begin': a, 'end': a + 86400})
        url = 'https://opensky-network.org/api/flights/arrival?' + query
        req = Request(url, headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'})
        try:
            with urlopen(req, timeout=45) as response:
                body, status = response.read(), response.status
                headers = {k: v for k, v in response.headers.items() if k.lower().startswith('x-rate')}
        except HTTPError as e:
            status, body, headers = e.code, e.read(), {}
        path = out / (day + '_authenticated_arrivals.json')
        path.write_bytes(body)
        meta = {'date': day, 'url': url, 'status': status, 'bytes': len(body), 'rate_headers': headers}
        if status == 200:
            data = json.loads(body)
            meta['rows'] = len(data)
        else:
            meta['message'] = body.decode(errors='replace')[:160]
        (out / (day + '_authenticated_status.json')).write_text(json.dumps(meta, indent=2), encoding='utf-8')
        print(json.dumps(meta))
        if status in [401, 403, 429]:
            break


if __name__ == '__main__':
    main()
