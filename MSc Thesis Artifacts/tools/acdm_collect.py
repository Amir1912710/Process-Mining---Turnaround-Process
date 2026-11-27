"""Save one BER A-CDM date snapshot, including departed flights, at the end of each day."""
from pathlib import Path
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
import argparse, csv, hashlib, io, json, os, shutil, urllib.parse, urllib.request
from acdm_probe import KEY_PATH, protect

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/acdm'
ENDPOINT='https://commercial-api.berlin-airport.de/api/v1/cdm-app/en/flights/ber'
UTC=timezone.utc

def now():return datetime.now(UTC)
def select_day(state,at):
    if state.get('collection_mode')=='end_of_day':
        target=(at.astimezone(ZoneInfo('Europe/Berlin')).date()-timedelta(days=1)).isoformat()
        if any(e['date']==target for e in state.get('completed_days',[])):return None
        return target
    return state['next_day']
def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    temp.replace(path)

def requested_rows(rows,day):
    # Preserve naive API timestamps. Their timezone has not been independently verified.
    return [r for r in rows if isinstance(r.get('std'),str) and r['std'][:10]==day]

def validate_rows(rows):
    if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows):
        raise ValueError('Invalid data array; refusing to save a completed day.')
    if any(not r.get('id') or not r.get('flight_id') or not isinstance(r.get('std'),str) for r in rows):
        raise ValueError('Required identity/timestamp missing; refusing to complete the day.')
    if len({str(r['id']) for r in rows})!=len(rows):
        raise ValueError('Pagination contains duplicate record IDs; this snapshot cannot be completed.')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--status',action='store_true');parser.add_argument('--dry-run',action='store_true');parser.add_argument('--repair-last-snapshot',action='store_true');args=parser.parse_args()
    state_path=DATA/'state.json'
    state=json.loads(state_path.read_text(encoding='utf8'))
    if args.status:
        print(json.dumps(state,ensure_ascii=False,indent=2));return 0
    daily=state.get('collection_mode')=='end_of_day'
    selected_day=select_day(state,now())
    if args.dry_run:
        print(json.dumps({'status':'dry_run','mode':state.get('collection_mode'),'timezone':'Europe/Berlin','target_day':selected_day,'network_requests':0,'already_collected':selected_day is None}));return 0
    if selected_day is None and not args.repair_last_snapshot:
        print(json.dumps({'status':'already_collected','message':'The previous Berlin calendar date is already saved. No API request made.'}));return 0
    repair_day=None
    if args.repair_last_snapshot:
        if not state.get('completed_days'):raise ValueError('No previously saved snapshot to repair.')
        repair_day=state['completed_days'][-1]['date']
        previous_manifest=DATA/'days'/repair_day/'manifest.json'
        previous=json.loads(previous_manifest.read_text(encoding='utf8'))
        if previous.get('filter_atot')==0:raise ValueError('Latest snapshot already uses the corrected filter.')
        # Manual correction of the same already-collected date only, never a backfill batch.
        backup=DATA/'superseded'/repair_day/'filterAtot1'
        if backup.exists():raise ValueError('Repair backup already exists; inspect before retrying.')
        backup.mkdir(parents=True)
        shutil.copytree(DATA/'days'/repair_day,backup/'day')
        shutil.copytree(DATA/'raw'/repair_day,backup/'raw')
    if state.get('status')=='blocked_historical_day' and not repair_day and not daily:
        print(json.dumps({'status':'blocked_historical_day','next_day':state['next_day'],'message':'Historical endpoint required. No further API request made.'}));return 3
    if state.get('last_attempt_utc') and not repair_day and not daily:
        elapsed=(now()-datetime.fromisoformat(state['last_attempt_utc'])).total_seconds()
        if elapsed<3600:
            print(json.dumps({'status':'hourly_limit','next_day':state['next_day'],'retry_after_seconds':int(3600-elapsed)+1}));return 0
    if state.get('retry_not_before_utc') and now()<datetime.fromisoformat(state['retry_not_before_utc']):
        print(json.dumps({'status':'rate_limited','retry_not_before_utc':state['retry_not_before_utc']}));return 0
    DATA.mkdir(parents=True,exist_ok=True)
    lock=DATA/'.collector.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        print(json.dumps({'status':'locked','message':'Another collection is running or needs lock inspection.'}));return 2
    day=repair_day or selected_day;day_date=date.fromisoformat(day)
    try:
        os.write(fd,str(os.getpid()).encode());os.close(fd)
        state['last_attempt_utc']=now().isoformat();state['status']='collecting';write_json(state_path,state)
        # A lower-bound query only: the server does not provide a verified upper-bound filter.
        # Start one day earlier in UTC so uncertain API timezone cannot exclude the target date.
        lower=datetime.combine(day_date-timedelta(days=1),time(),UTC)
        key=protect(KEY_PATH.read_bytes(),decrypt=True).decode()
        all_rows=[];raw_pages=[];total_pages=None;total_items=None
        for page in range(1,51):
            query=urllib.parse.urlencode({'page':page,'itemsPerPage':100,'filterAtot':0,'dateFrom':lower.strftime('%Y-%m-%d %H:%M:%S')})
            url=ENDPOINT+'?'+query
            request=urllib.request.Request(url,headers={'x-api-key':key,'Accept':'application/json','User-Agent':'Thesis-ACDM-Collector/1.0'})
            with urllib.request.urlopen(request,timeout=40) as response:raw=response.read()
            obj=json.loads(raw)
            if not isinstance(obj,dict) or not isinstance(obj.get('data'),list):raise ValueError('Unexpected API response structure.')
            pages=int(obj['totalPages']);items=int(obj['totalItems'])
            if not 0<=pages<=50:raise ValueError('Unexpected pagination size; refusing to continue.')
            if total_pages is None:total_pages,total_items=pages,items
            elif (pages,items)!=(total_pages,total_items):raise ValueError('Live pagination changed during collection; snapshot not completed.')
            if int(obj['page'])!=page:raise ValueError('API returned the wrong page.')
            raw_path=DATA/'raw'/day/f'page_{page:03d}.json';raw_path.parent.mkdir(parents=True,exist_ok=True);raw_path.write_bytes(raw)
            raw_pages.append({'page':page,'path':str(raw_path.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'url':url,'fetched_at_utc':now().isoformat()})
            all_rows.extend(obj['data'])
            if page>=total_pages:break
        validate_rows(all_rows)
        if len(all_rows)!=total_items:raise ValueError('Fetched row count differs from API totalItems.')
        rows=sorted(requested_rows(all_rows,day),key=lambda r:(r['std'],str(r['id'])))
        observed=sorted({r['std'][:10] for r in all_rows})
        manifest={'requested_day':day,'airport':'BER','source':ENDPOINT,'collection_kind':'api_snapshot','collection_mode':state.get('collection_mode','historical'),'schedule_timezone':'Europe/Berlin','filter_atot':0,'historical_archive_access_verified':False,'full_day_completeness':'unverified; all paginated records returned for the requested STD date are retained','collection_started_utc':state['last_attempt_utc'],'collection_finished_utc':now().isoformat(),'day_selection':'Exact calendar-date prefix of raw API std; timestamp timezone unverified','query_lower_bound_utc':lower.isoformat(),'api_total_items':total_items,'api_pages':total_pages,'observed_std_dates':observed,'requested_day_records':len(rows),'synthetic_records_added':0,'raw_pages':raw_pages}
        if not rows:
            manifest['status']='day_unavailable' if daily else 'unavailable_historical_day'
            write_json(DATA/'attempts'/f'{day}.json',manifest)
            message=f'API returned no records whose std date is {day}. Available dates: {observed}. No daily dataset created.'
            state.update(status='day_unavailable' if daily else 'blocked_historical_day',last_error=message)
            write_json(state_path,state)
            print(json.dumps({'status':state['status'],'requested_day':day,'observed_dates':observed,'records_saved':0,'message':state['last_error']},ensure_ascii=False));return 3
        destination=DATA/'days'/day
        write_json(destination/'flights.json',rows)
        fields=list(dict.fromkeys(k for r in rows for k in r))
        buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=fields);writer.writeheader();writer.writerows(rows)
        (destination/'flights.csv').write_text(buffer.getvalue(),encoding='utf-8-sig',newline='')
        manifest.update(status='collected_snapshot',std_min=rows[0]['std'],std_max=rows[-1]['std'])
        write_json(destination/'manifest.json',manifest)
        entry={'date':day,'rows':len(rows),'path':str(destination.relative_to(ROOT)),'collected_at_utc':manifest['collection_finished_utc']}
        state['completed_days']=[e for e in state['completed_days'] if e['date']!=day]+[entry]
        next_day=state['next_day'] if repair_day else (day_date+timedelta(days=1) if daily else day_date-timedelta(days=1)).isoformat()
        state.update(next_day=next_day,status='ready',last_success_utc=manifest['collection_finished_utc'],last_error=None)
        write_json(state_path,state)
        print(json.dumps({'status':'collected_snapshot','day':day,'rows':len(rows),'pages':total_pages,'next_day':state['next_day'],'total_collected_days':len(state['completed_days'])}));return 0
    except Exception as exc:
        # Record sanitized diagnostic text, never request headers/credential material.
        state.update(status='collection_failed' if daily else 'retry_next_hour',last_error=f'{type(exc).__name__}: {exc}')
        if getattr(exc,'code',None)==429:
            try:delay=max(3600,int(exc.headers.get('Retry-After','3600')))
            except (TypeError,ValueError):delay=3600
            state['retry_not_before_utc']=(now()+timedelta(seconds=delay)).isoformat()
        write_json(state_path,state)
        print(json.dumps({'status':state['status'],'requested_day':day,'error':state['last_error']}));return 2
    finally:lock.unlink(missing_ok=True)

if __name__=='__main__':raise SystemExit(main())
