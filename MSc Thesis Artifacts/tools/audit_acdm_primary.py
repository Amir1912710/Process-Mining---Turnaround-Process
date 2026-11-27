"""A-CDM owns every primary row; OpenSky supplies independent departure cross-checks."""
from pathlib import Path
import sys,csv,json,hashlib,statistics,importlib.util
from collections import Counter,defaultdict
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/acdm_primary_20261119';OUT.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('prepare_acdm_snapshot',ROOT/'tools/prepare_acdm.py')
prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
prep.OUT=OUT/'prepared';audit=prep.prepare()
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,rows):
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
rows=read(prep.OUT/'ber_departures_prepared.csv')
events={}
for r in read(ROOT/'data/ber_history/prepared/ber_movements_opensky.csv'):
 if r['direction']=='departure':events[r['flight_key']]={'key':r['flight_key'],'callsign':r['callsign'],'icao24':r['icao24'],'epoch':float(r['boundary_epoch']),'source_file':r['source_file']}
for day in ['2026-11-15','2026-11-16']:
 folder=ROOT/'data/ber_history/opensky'/day
 m=json.loads((folder/'departure_manifest.json').read_text())
 assert m['status']=='collected'
 raw=(folder/'departure.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==m['sha256']
 for f in json.loads(raw):
  if f.get('estDepartureAirport')!='EDDB' or not f.get('icao24') or f.get('firstSeen') is None:continue
  key='|'.join(map(str,[f['icao24'].lower(),f['firstSeen'],f['lastSeen'],'departure']))
  events[key]={'key':key,'callsign':(f.get('callsign') or '').strip().upper(),'icao24':f['icao24'].lower(),'epoch':f['firstSeen'],'source_file':str((folder/'departure.json').relative_to(ROOT))}
bycallsign=defaultdict(list)
for e in events.values():
 if e['callsign']:bycallsign[e['callsign']].append(e)
cross=[]
for r in rows:
 d={'record_key':r['record_key'],'source_day':r['source_day'],'callsign':r['callsign'],'acdm_atot_naive':r['atot'],'status':'no_eligible_actual_takeoff','candidate_count':0,'opensky_flight_key':'','opensky_icao24':'','opensky_first_seen_utc':'','opensky_source_file':'','timezone_hypothesis':'','delta_proxy_minus_atot_min':''}
 if r['usable_actual_takeoff']=='True':
  d['status']='no_correspondence_within_30min';poss=[]
  atot=datetime.fromisoformat(r['atot'])
  for hyp,zone in [('ACDM_is_UTC',timezone.utc),('ACDM_is_Europe_Berlin',ZoneInfo('Europe/Berlin'))]:
   target=atot.replace(tzinfo=zone).timestamp()
   for e in bycallsign[r['callsign'].strip().upper()]:
    delta=(e['epoch']-target)/60
    if abs(delta)<=30:poss.append((e,hyp,delta))
  d['candidate_count']=len(poss)
  if len(poss)==1:
   e,hyp,delta=poss[0];d.update(status='unique_candidate_pending_reuse_check',opensky_flight_key=e['key'],opensky_icao24=e['icao24'],opensky_first_seen_utc=datetime.fromtimestamp(e['epoch'],timezone.utc).isoformat(),opensky_source_file=e['source_file'],timezone_hypothesis=hyp,delta_proxy_minus_atot_min=round(delta,6))
  elif poss:d['status']='ambiguous_callsign_time_candidates'
 cross.append(d)
groups=defaultdict(list)
for d in cross:
 if d['opensky_flight_key']:groups[d['opensky_flight_key']].append(d)
for group in groups.values():
 for d in group:d['status']='unique_callsign_time_candidate_not_identity_verification' if len(group)==1 else 'multiple_acdm_rows_for_opensky_flight_review'
write(OUT/'opensky_departure_crosscheck.csv',cross)
crossby={r['record_key']:r for r in cross}
combined=[]
for r in rows:
 d=dict(r)
 for k,v in crossby[r['record_key']].items():
  if k not in ['record_key','source_day','callsign','acdm_atot_naive']:d['crosscheck_'+k]=v
 combined.append(d)
write(OUT/'ACDM_Berlin_Primary_With_OpenSky_Check.csv',combined)
def stats(vals):
 return {'n':len(vals),'mean':statistics.mean(vals) if vals else None,'median':statistics.median(vals) if vals else None,'min':min(vals) if vals else None,'max':max(vals) if vals else None}
valid=[r for r in cross if r['status']=='unique_callsign_time_candidate_not_identity_verification']
delta=[float(r['delta_proxy_minus_atot_min']) for r in valid]
daily=[]
for source in audit['sources']:
 day=source['date'];rs=[r for r in rows if r['source_day']==day];cr=[r for r in valid if r['source_day']==day]
 daily.append({'date':day,'records':len(rs),'eligible_atot':sum(r['usable_actual_takeoff']=='True' for r in rs),'complete_target_triples':sum(r['usable_target_takeoff_pairs']=='True' for r in rs),'unique_opensky_candidates':len(cr),'median_signed_proxy_delta_min':statistics.median(float(r['delta_proxy_minus_atot_min']) for r in cr) if cr else None})
metrics={}
for k in prep.METRICS:
 vals=[float(r[k]) for r in rows if r['usable_target_takeoff_pairs']=='True' and r[k]!=''];metrics[k]=stats(vals)
summary={'as_of':'2026-11-19','primary_source':'BER A-CDM application finalized daily snapshots','primary_unit':'one BER departure record, not an arrival-departure turnaround pair','primary_records':len(rows),'primary_cohorts':audit['cohorts'],'status_counts':audit['status_counts'],'days':daily,'crosscheck_status':dict(Counter(r['status'] for r in cross)),'timezone_hypotheses':dict(Counter(r['timezone_hypothesis'] for r in valid)),'unique_candidate_delta_min':stats(delta),'unique_candidate_absolute_delta_min':stats([abs(x) for x in delta]),'unique_matches_within_minutes':{str(t):sum(abs(x)<=t for x in delta) for t in [1,5,15,30]},'target_metrics_complete_triples':metrics,'missing':audit['missing'],'auxiliary_opensky_core_pairs':10940,'auxiliary_pairs_with_acdm_candidate':826,'acdm_measured_full_turnaround_pairs':0,'cautions':['Unique callsign/time correspondence does not independently verify aircraft identity.','OpenSky firstSeen is an observation proxy, not independently measured exact ATOT.','Delta statistics are conditional on matches within30 minutes.','Timezone hypothesis is empirical correspondence, not provider documentation.','No source AIBT/AOBT or service start/end timestamps are available.','No claim of continuous full-day coverage or improved predictive accuracy.']}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
write(OUT/'daily_summary.csv',daily)
(OUT/'README.md').write_text('''# A-CDM primary study update, 19 November 2026

Every row of ACDM_Berlin_Primary_With_OpenSky_Check.csv originates in a finalized BER A-CDM snapshot. OpenSky supplies only prefixed departure cross-check columns in this table. Missing/ambiguous matches remain explicit and never create A-CDM records. Summary counts and matching limitations are in summary.json.

The primary unit is a departure record. These observations cannot be represented as complete landing-to-next-takeoff or AIBT–AOBT pairs because the source lacks arrival/block milestones. TOBT/TSAT are target values and their differences from ATOT are not measured queue or service durations. Raw timestamps retain their unverified naive timezone.

The previous10,940 aircraft-pair dataset originates in OpenSky. Only826 core pairs have candidate A-CDM reference links. It is a separate auxiliary reconstruction and cannot become A-CDM data by renaming columns. Previous OCPN/Promenade outputs and60 replications are an exploratory pilot using that reconstruction. They are not new A-CDM-only calibrated results.

This version does not overwrite earlier source/prepared files or experimental outputs. Technical checks verify source JSON/CSV consistency, manifest counts and raw hashes. OpenSky cross-check tests UTC/Berlin hypotheses within30minutes, retains ambiguity, prohibits reused unique matches and reports agreement conditional on the retained candidates.
''',encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['primary_records','primary_cohorts','status_counts','days','crosscheck_status','unique_candidate_delta_min','unique_candidate_absolute_delta_min','unique_matches_within_minutes']},indent=2))
