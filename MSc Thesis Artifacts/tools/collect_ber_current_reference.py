"""One manual current BER A-CDM reference snapshot; no schedule/state changes."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.parse import urlencode
import json,hashlib
import shutil
from acdm_probe import protect,KEY_PATH

ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    folder=ROOT/'data/ber_history/acdm_current_reference'
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/'manifest.json').exists():
        archive=folder/'previous_versions'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        archive.mkdir(parents=True)
        for previous in list(folder.glob('page_*.json'))+[folder/'manifest.json']:
            shutil.copy2(previous,archive/previous.name)
    key=protect(KEY_PATH.read_bytes(),decrypt=True).decode()
    pages=[];records=[]
    page=1;total_pages=1
    while page<=total_pages:
        url='https://commercial-api.berlin-airport.de/api/v1/cdm-app/en/flights/ber?'+urlencode(
            {'page':page,'itemsPerPage':100,'filterAtot':0})
        req=Request(url,headers={'x-api-key':key,'Accept':'application/json'})
        with urlopen(req,timeout=30) as response:body=response.read()
        obj=json.loads(body)
        total_pages=int(obj['totalPages'])
        if not 1<=total_pages<=30:raise ValueError('Unexpected pagination')
        if int(obj['page'])!=page:raise ValueError('Pagination mismatch')
        path=folder/f'page_{page:03d}.json';path.write_bytes(body)
        pages.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(body).hexdigest(),
                      'fetched_at_utc':datetime.now(timezone.utc).isoformat()})
        records.extend(obj['data']);page+=1
    if len({str(r['id']) for r in records})!=len(records):raise ValueError('Duplicate IDs across current pages')
    manifest={'purpose':'current reference snapshot; not complete daily archive',
              'pages':pages,'rows':len(records),'rows_with_atot':sum(bool(r.get('atot')) for r in records),
              'finished_utc':datetime.now(timezone.utc).isoformat()}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({k:manifest[k] for k in ['rows','rows_with_atot','finished_utc']}))
