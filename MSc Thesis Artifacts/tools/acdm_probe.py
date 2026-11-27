"""One read-only A-CDM request; credentials are encrypted for this Windows user."""
from pathlib import Path
from datetime import datetime, date, time, timedelta, timezone
import argparse, collections, ctypes, json, urllib.request, urllib.parse
from ctypes import wintypes

ROOT=Path(__file__).resolve().parents[1]
KEY_PATH=ROOT/'.secrets/acdm-api-key.dpapi'

class Blob(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]

def protect(data, decrypt=False):
    buf=(ctypes.c_ubyte*len(data)).from_buffer_copy(data)
    inp=Blob(len(data),buf); output=Blob()
    crypt=ctypes.windll.crypt32
    if decrypt:
        ok=crypt.CryptUnprotectData(ctypes.byref(inp),None,None,None,None,0,ctypes.byref(output))
    else:
        ok=crypt.CryptProtectData(ctypes.byref(inp),'A-CDM collector',None,None,None,0,ctypes.byref(output))
    if not ok: raise ctypes.WinError()
    try:return ctypes.string_at(output.data,output.size)
    finally:ctypes.windll.kernel32.LocalFree(output.data)

def main():
    p=argparse.ArgumentParser();p.add_argument('--store-key-hex');p.add_argument('--date');p.add_argument('--filter-atot',type=int,choices=[0,1],default=0);p.add_argument('--all-pages',action='store_true');args=p.parse_args()
    if args.store_key_hex:
        KEY_PATH.parent.mkdir(parents=True,exist_ok=True)
        KEY_PATH.write_bytes(protect(bytes.fromhex(args.store_key_hex)))
        print('Existing API credential stored with Windows user encryption.');return
    day=date.fromisoformat(args.date)
    # Requested historic date is Berlin time. 2026-11-01 is UTC+1.
    start=datetime.combine(day,time(),timezone(timedelta(hours=1))).astimezone(timezone.utc)
    query=urllib.parse.urlencode({'page':1,'itemsPerPage':100,'filterAtot':args.filter_atot,'dateFrom':start.strftime('%Y-%m-%d %H:%M:%S')})
    url='https://commercial-api.berlin-airport.de/api/v1/cdm-app/en/flights/ber?'+query
    key=protect(KEY_PATH.read_bytes(),decrypt=True).decode()
    request=urllib.request.Request(url,headers={'x-api-key':key,'Accept':'application/json','User-Agent':'Thesis-ACDM-Collector/1.0'})
    with urllib.request.urlopen(request,timeout=40) as response:
        raw=response.read();status=response.status
    obj=json.loads(raw);path=ROOT/f'tmp/acdm_probe_atot{args.filter_atot}.json';path.write_bytes(raw)
    rows=obj.get('data',[])
    if args.all_pages:
        all_rows=list(rows)
        total_pages=int(obj['totalPages'])
        if not 1<=total_pages<=50:raise ValueError('Unexpected pagination size')
        folder=ROOT/f'tmp/acdm_probe_{args.date}_atot{args.filter_atot}';folder.mkdir(parents=True,exist_ok=True)
        (folder/'page_001.json').write_bytes(raw)
        for page in range(2,total_pages+1):
            query=urllib.parse.urlencode({'page':page,'itemsPerPage':100,'filterAtot':args.filter_atot,'dateFrom':start.strftime('%Y-%m-%d %H:%M:%S')})
            page_request=urllib.request.Request('https://commercial-api.berlin-airport.de/api/v1/cdm-app/en/flights/ber?'+query,headers={'x-api-key':key,'Accept':'application/json','User-Agent':'Thesis-ACDM-Collector/1.0'})
            with urllib.request.urlopen(page_request,timeout=40) as response:page_raw=response.read()
            page_obj=json.loads(page_raw)
            if (page_obj['totalPages'],page_obj['totalItems'],page_obj['page'])!=(obj['totalPages'],obj['totalItems'],page):raise ValueError('Pagination changed while checking')
            all_rows.extend(page_obj['data']);(folder/f'page_{page:03d}.json').write_bytes(page_raw)
        if len(all_rows)!=int(obj['totalItems']):raise ValueError('Pagination row count mismatch')
        dates=collections.Counter(r['std'][:10] for r in all_rows)
        print(json.dumps({'status':status,'requested_day':args.date,'pages_checked':total_pages,'total_rows_checked':len(all_rows),'rows_for_requested_day':dates.get(args.date,0),'returned_std_dates':dict(sorted(dates.items()))},ensure_ascii=False));return
    print(json.dumps({'status':status,'requested_day':str(day),'meta':{k:v for k,v in obj.items() if k!='data'},'rows_on_page':len(rows),'sample':rows[:1],'std_range_on_page':sorted(str(r.get('std')) for r in rows)[::max(1,len(rows)-1)]},ensure_ascii=False,default=str))

if __name__=='__main__':main()
