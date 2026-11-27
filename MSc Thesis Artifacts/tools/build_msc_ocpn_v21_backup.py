"""Build a finite BER-demand derivative without modifying Koren's baseline."""
import argparse, collections, copy, csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(r'C:\Users\amira\Desktop\ELTE\Thesis\airport-extended.ocpn')
SOURCE = ROOT / 'data/ber_history/prepared/ber_ground_intervals_core_proxy.csv'
OUT = ROOT / 'output/ocpn'

def rhai(v):
    if isinstance(v, dict): return '#{' + ','.join(json.dumps(k)+':'+rhai(x) for k,x in v.items()) + '}'
    if isinstance(v, list): return '['+','.join(map(rhai,v))+']'
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'))

def build(date=None, limit=None, suffix=None, load_factor=.85, cleaning_teams=9, service_scale=1.0, timing='literature', curfew='inherited', hydrant_dispensers=4, fuel_tankers=4, out_dir=None):
    rows=list(csv.DictReader(SOURCE.open(encoding='utf-8-sig')))
    rows=sorted((r for r in rows if not date or r['inbound_last_seen_berlin'][:10]==date),key=lambda r:r['inbound_last_seen_utc'])
    if limit: rows=rows[:limit]
    assert rows
    p=json.loads(BASE.read_text(encoding='utf-8'))
    places={x['id']:x for n in p['petriNets'] for x in n['places']}
    trans={x['id']:x for n in p['petriNets'] for x in n['transitions']}
    arcs={x['id']:x for n in p['petriNets'] for x in n['arcs']}
    funcs={x['name']:x for x in p['functions']}
    epoch=datetime.fromisoformat(rows[0]['inbound_last_seen_utc']).replace(hour=0,minute=0,second=0,microsecond=0)
    flights=[]; fleet={}; manifest=[]
    # Seats/capacity are scenario values, never claimed to be observations.
    specs={'A319':('narrow',156,24210,'C'),'A320':('narrow',180,24210,'C'),'A20N':('narrow',180,26730,'C'),'A321':('narrow',220,30030,'C'),'A21N':('narrow',220,32940,'C'),'B738':('narrow',189,26020,'C'),'B38M':('narrow',189,25820,'C'),'B739':('narrow',215,26020,'C'),'E190':('regional',100,12971,'C'),'E195':('regional',120,12971,'C'),'A333':('wide',300,139090,'E'),'B789':('wide',290,126206,'E'),'A359':('wide',325,141000,'E')}
    for i,r in enumerate(rows,1):
        ident=r['aircraft_icao24']; observed=r['aircraft_type_from_candidate_acdm_reference'].strip().upper()
        typ=observed if observed in specs else 'A320'
        body,seats,cap,letter=specs[typ]
        ac={'id':'ICAO24-'+ident,'typeCode':typ,'codeLetter':letter,'body':body,'seats':seats,'fuelCapL':cap,'airline':r['airline_from_candidate_acdm_reference'] or 'UNKNOWN'}
        # Use one stable configuration per physical aircraft within a build.
        if ident not in fleet: fleet[ident]=ac
        ac=fleet[ident]
        case='BER-'+str(i).zfill(5)
        fl={'id':'ARR-'+case,'callsign':r['inbound_callsign'] or 'UNKNOWN','airline':ac['airline'],'carrierType':'unknown','direction':'ARR','schengen':False,'station':r['inbound_origin'] or 'UNKNOWN','pax':round(ac['seats']*load_factor),'prm':0,'sectorMin':120,'aircraft':ac,'studyCase':case,'pairedCallsign':r['outbound_callsign'] or 'UNKNOWN','pairedDestination':r['outbound_destination'] or 'UNKNOWN','inputBasis':'OpenSky airborne-boundary proxy','contextBasis':'type candidate if supported; seats/load/PRM/sector assumed; border segregation disabled'}
        ms=round((datetime.fromisoformat(r['inbound_last_seen_utc'])-epoch).total_seconds()*1000)
        flights.append((fl,ms))
        manifest.append(dict(r,study_case_id=case,model_arrival_flight_id=fl['id'],model_departure_flight_id='DEP-'+case,model_aircraft_id=ac['id'],model_release_ms=ms,model_type=ac['typeCode'],type_supported_candidate=bool(observed in specs),model_passengers=fl['pax'],model_carrier_profile='unknown'))
    def mark(pid,vals,expression=None):
        places[pid]['initialMarking']=expression if expression is not None else json.dumps(vals,separators=(',',':'))
        places[pid]['marking']=vals
    mark('p-fleet',list(fleet.values()))
    for pid in ('s-fleet','d-fleet'): mark(pid,[],'')
    assert cleaning_teams>0 and 0<load_factor<=1 and service_scale>0
    mark('c-clean',[dict(id='CLN-'+str(i+1),size=4,x=640,y=400) for i in range(cleaning_teams)])
    assert hydrant_dispensers>0 and fuel_tankers>0
    originals=places['r-fuellers']['marking']
    fuel_resources=[]
    for kind,count,prefix in [('hydrant',hydrant_dispensers,'HYD'),('tanker',fuel_tankers,'TNK')]:
        template=next(x for x in originals if x['kind']==kind)
        fuel_resources.extend(dict(template,id=prefix+'-'+str(i+1)) for i in range(count))
    mark('r-fuellers',fuel_resources)
    mark('s-clock',[], '['+','.join('timed('+rhai(fl)+','+str(ms)+')' for fl,ms in flights)+']')
    places['s-clock'].update(name='Observed BER\nArrival Demand',colorSet='Flight')
    mark('s-seq',[]); places['s-seq']['name']='Unused legacy\nCounter'
    trans['s-t-file'].update(name='Release Observed\nArrival Proxy',guard='fl.aircraft.id == ac.id',codeSegment='// Finite observed demand; aircraft identity is held until simulated departure.\nfl.aircraft = ac;',includeInOcel=True)
    arcs['e47']['inscription']='fl'
    for n in p['petriNets']:
        n['arcs']=[a for a in n['arcs'] if a['id'] not in ('e48','e50','e51')]
    # No synthetic outstation flight or curfew is inserted before an observed arrival.
    arcs['e54']['delay']=''; arcs['e56']['delay']=''; arcs['e65']['delay']=''
    trans['a-t-dep-out'].update(name='Arrival Input\nTransfer',includeInOcel=False)
    trans['a-t-tma'].update(name='Arrival Queue\nEntry',includeInOcel=False)
    trans['a-t-final']['name']='Acquire Arrival\nRunway'
    trans['a-t-land']['name']='Simulated Landing\n(proxy-fed)'
    trans['a-t-final']['codeSegment']=trans['a-t-final']['codeSegment'].replace('let dep = make_flight(fl.id.sub_string(4), "DEP", fl.aircraft, fl.schengen, dep_lh);','let dep = fl;\ndep.id = "DEP-" + fl.studyCase;\ndep.direction = "DEP";\ndep.callsign = fl.pairedCallsign;\ndep.station = fl.pairedDestination;')
    # Observed departure outcomes are deliberately absent from executable tokens.
    arcs['e223']['delay']=''
    trans['d-t-tobt']['name']='Departure Planning\nStart (assumed)'
    trans['d-t-tsat']['name']='Departure Planning\nComplete (assumed)'
    places['d-tsatq']['name']='Planning\nin Progress'
    if curfew=='none':
        # Policy sensitivity only. This does not encode verified BER night operations.
        funcs['curfew_delay']['code']='fn curfew_delay(base) { base }'
    funcs['stand_fits']['code']='''fn stand_fits(st, ac, schengen) {
    // Route/Schengen status is missing for many cases: do not fabricate a classification.
    // Study scenario disables border segregation; physical code compatibility remains.
    let sr = code_rank(st.maxCode);
    let ar = code_rank(ac.codeLetter);
    sr >= ar && sr <= ar + 1
}'''
    original_times={name:funcs[name]['code'] for name in ('clean_sec','fuel_sec','board_sec')}
    # Literature applies to single-aisle aircraft; legacy size models retained elsewhere.
    funcs['clean_sec']['code']='''fn clean_sec(body, carrier_type) {
    // Schultz et al., ICAS 2012, Table 1: shifted Weibull, minutes.
    // cpnsim takes weibull(scale, shape). No measured LCC/FSC coefficient.
    if body == "narrow" { return ((5.0 + weibull(6.76, 2.16)) * 60.0).to_int(); }
    let base = if body == "regional" { 300 } else if body == "wide" { 1200 } else { 1800 };
    base + discrete(420, 900)
}'''
    funcs['fuel_sec']['code']='''fn fuel_sec(litres, rate_lpm, body) {
    // ICAS 2012: 2 + Gamma(shape=1.64, scale=9.12), minutes.
    // cpnsim CPN Tools order is gamma(scale, shape), NOT shape, scale.
    // A transfer assumption; not fitted to BER, uplift or measured pump flow.
    if body == "narrow" { return ((2.0 + gamma(9.12, 1.64)) * 60.0).to_int(); }
    let acc = accept_lpm(body);
    let rate = if rate_lpm < acc { rate_lpm } else { acc };
    ((7.0 + litres.to_float() / rate.to_float()) * 60.0).to_int()
}'''
    funcs['board_sec']['code']='''fn board_sec(body, pax, contact) {
    // Schultz 2018, Aerospace 5(1),8: mean single-aisle reference in minutes.
    // This deterministic mean is NOT a fitted stochastic boarding distribution.
    // Bus access time is added separately by the existing remote-stand branch.
    if body == "narrow" { return ((2.3 + 0.075 * pax.to_float()) * 60.0).to_int(); }
    let rate = if body == "regional" { 11.0 } else if body == "wide" { 22.0 } else { 30.0 };
    ((4.0 + pax.to_float() / rate) * 60.0).to_int()
}'''
    if timing=='baseline':
        for name,code in original_times.items(): funcs[name]['code']=code
    # Sensitivity multiplier is an explicit scenario assumption, not an estimated effect.
    for aid in ('e103','e126','e129','e164'):
        delay=arcs[aid]['delay']
        for call in ('clean_sec(tr.arr.aircraft.body, tr.arr.carrierType)','board_sec(tr.dep.aircraft.body, tr.dep.pax, true)','board_sec(tr.dep.aircraft.body, tr.dep.pax, false)','fuel_sec(tr.upliftL, fu.rateLpm, tr.dep.aircraft.body)'):
            if call in delay: delay=delay.replace(call,'('+call+'.to_float() * '+str(service_scale)+').to_int()')
        arcs[aid]['delay']=delay
    for cs in p['colorSets']:
        if cs['name']=='Flight': cs['definition']=cs['definition'].replace(' * aircraft: Aircraft timed;', ' * aircraft: Aircraft * studyCase: STRING * pairedCallsign: STRING * pairedDestination: STRING * inputBasis: STRING * contextBasis: STRING timed;')
    # Retain topology/capacities as explicit inherited assumptions, rather than invent BER assets.
    p['ocpnName']='BER MSc - Empirical Arrival Demand - '+(date or 'All Core Proxies')
    p['metadata'].update(name=p['ocpnName'],version='2.0-study-draft',description='MSc derivative of Istvan Koren\'s Airport Ground Handling (Extended). Finite BER same-aircraft paired demand; literature-informed single-aisle service times. NOT a validated digital twin. Layout, resource capacities, weather and remaining process times are inherited fictional assumptions. Six parallel handling threads. Input timestamps are airborne boundary proxies, not ALDT/AIBT. Departure observations are external evaluation targets, never simulator timing inputs. See README and build_manifest.json.',authors=p['metadata']['authors']+['Amir (MSc study adaptation)'])
    p['metadata']['description']=p['metadata']['description'].replace('build_manifest.json','the companion *_manifest.json')
    if timing=='baseline':p['metadata']['description']=p['metadata']['description'].replace('literature-informed single-aisle service times','original baseline service-time functions retained for a same-demand comparison')
    if curfew!='inherited' or out_dir:
        p['metadata']['version']='2.1-controlled-study'
        p['metadata']['description']+=' Curfew scenario: '+curfew+'. Disabled curfew is an assumption sensitivity, not verified BER policy.'
    p['petriNets'][0]['name']='BER Study (inherited resource layout)'
    p['simulationEpoch']=epoch.isoformat()
    p['simulationSettings'].update(simulationEpoch=epoch.isoformat(),animationDelayMs=0,stepsPerRun=1000,endTimeMs=max(ms for _,ms in flights)+24*3600000)
    for mon in p['monitors']:
        if mon['id']=='mon-stands': mon['name']='Available stands (inherited capacity)'
        if mon['id']=='mon-temp': mon['name']='Synthetic temperature (not BER observations)'
    for name,start,end in [('Cleaning including vehicle travel','c-t-clean-start','c-t-clean-end'),('Fuel service','r-t-fuel-start','r-t-fuel-end'),('Boarding at bridge','c-t-board-bridge','c-t-board-bridge-end'),('Boarding with bus access','c-t-board-bus','c-t-board-bus-end')]:
        p['monitors'].append({'id':'msc-'+start,'name':name,'type':'interval-duration','enabled':True,'placeIds':[],'transitionIds':[start,end],'config':{'startTransitionId':start,'endTransitionId':end,'correlationKey':'id'}})
    destination=Path(out_dir) if out_dir else OUT
    destination.mkdir(parents=True,exist_ok=True)
    stem='BER_MSc_'+(suffix or date or 'all_core')
    target=destination/(stem+'.ocpn'); target.write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')
    with (destination/(stem+'_cases.csv')).open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(manifest[0]));writer.writeheader();writer.writerows(manifest)
    info={'model':target.name,'cases':len(rows),'aircraft':len(fleet),'epoch':epoch.isoformat(),'baseline_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'model_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'date_filter':date,'arrival_dates':[rows[0]['inbound_last_seen_berlin'][:10],rows[-1]['inbound_last_seen_berlin'][:10]],'supported_type_candidates':sum(x['type_supported_candidate'] for x in manifest),'assumed_load_factor':load_factor,'assumed_prm':0,'border_segregation':'disabled because route context incomplete','assumed_sector_minutes':120,'carrier_profile':'unknown; no budget/full-service multiplier','departure_outcomes_in_execution':False,'cleaning_teams':cleaning_teams,'service_scale':service_scale,'timing_model':timing,'random_seed_control':'not exposed by WASM runtime; repeat runs required'}
    info.update(curfew_scenario=curfew,hydrant_dispensers=hydrant_dispensers,fuel_tankers=fuel_tankers)
    (destination/(stem+'_manifest.json')).write_text(json.dumps(info,indent=2),encoding='utf-8')
    print(json.dumps(info))
    return target

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--date');a.add_argument('--limit',type=int);a.add_argument('--suffix');a.add_argument('--load-factor',type=float,default=.85);a.add_argument('--cleaning-teams',type=int,default=9);a.add_argument('--service-scale',type=float,default=1.0);a.add_argument('--timing',choices=['literature','baseline'],default='literature');a.add_argument('--curfew',choices=['inherited','none'],default='inherited');a.add_argument('--hydrant-dispensers',type=int,default=4);a.add_argument('--fuel-tankers',type=int,default=4);a.add_argument('--out-dir');args=a.parse_args();build(**vars(args))
