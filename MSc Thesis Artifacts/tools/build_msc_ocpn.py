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

ACDM_PRIMARY = ROOT / 'output/acdm_primary_20261119/ACDM_Berlin_Primary_With_OpenSky_Check.csv'

def load_std_lookup():
    """A-CDM scheduled departure (STD) per record key; naive values read as UTC (cross-check hypothesis)."""
    out={}
    for r in csv.DictReader(ACDM_PRIMARY.open(encoding='utf-8-sig')):
        if r.get('std_parsed'):
            out[r['record_key']]=datetime.fromisoformat(r['std_parsed']).replace(tzinfo=timezone.utc)
    return out

ENRICHED = ROOT / 'data/ber_history/prepared/ber_turnarounds_enriched.csv'
WEATHER = ROOT / 'data/weather/ber_hourly_2026.json'
EXTRA_SPECS = {  # seats / fuel capacity are nominal planning values (assumptions, not observations)
    'BCS3':('narrow',145,21805,'C'),'BCS1':('narrow',120,21805,'C'),'B737':('narrow',149,26020,'C'),'B39M':('narrow',193,25820,'C'),
    'E170':('regional',76,11625,'C'),'E175':('regional',88,11625,'C'),'E295':('regional',132,13690,'C'),'DH8D':('regional',78,6526,'C'),
    'AT76':('regional',70,6370,'C'),'AT75':('regional',70,6370,'C'),'CRJ9':('regional',90,10900,'C'),
    'A332':('wide',250,139090,'E'),'A339':('wide',300,139090,'E'),'B788':('wide',242,126206,'E'),'B772':('wide',314,171170,'E'),
    'B77W':('wide',396,181280,'E'),'B763':('wide',218,91380,'E'),'B764':('wide',245,91380,'E'),'A35K':('wide',350,156000,'E'),
}

# Carrier-specific narrow-body service times (minutes), cpnsim argument order: weibull(scale, shape), gamma(scale, shape),
# normal(mean, variance). Full-service: Schultz et al. (2012) and Asadi (2024); low-cost: Luo et al. (2024, Schiphol),
# both as parameterised in Tkacenko (2026). Low-cost cleaning is a crew/small-team tidy without the 5-min fixed part.
CARRIER_FUNCS = {
'clean_sec': '''fn clean_sec(body, carrier_type) {
    if body == "narrow" {
        let m = if carrier_type == "low" { weibull(6.76, 2.16) } else { 5.0 + weibull(6.76, 2.16) };
        return (m * 60.0 * svc_scale(carrier_type)).to_int();
    }
    let base = if body == "regional" { 300 } else if body == "wide" { 1200 } else { 1800 };
    let spread = if carrier_type == "low" { discrete(60, 300) } else { discrete(420, 900) };
    base + spread
}''',
'cater_sec': '''fn cater_sec(body, sector_min, carrier_type) {
    if body == "narrow" {
        let m = if carrier_type == "low" { normal(7.0, 7.84) } else { weibull(17.37, 2.18) };
        if m < 1.0 { m = 1.0; }
        return (m * 60.0 * svc_scale(carrier_type)).to_int();
    }
    let base = if body == "regional" { 240 } else if body == "wide" { 1080 } else { 1500 };
    let extra = if sector_min > 300 { discrete(600, 1200) } else { discrete(60, 300) };
    base + extra
}''',
'board_sec': '''fn board_sec(body, pax, contact, carrier_type) {
    if body == "narrow" {
        let m = if carrier_type == "low" { gamma(0.63, 30.7) - 10.61 } else { gamma(1.45, 11.0) };
        if m < 2.0 { m = 2.0; }
        return (m * 60.0 * svc_scale(carrier_type)).to_int();
    }
    let rate = if body == "regional" { 11.0 } else if body == "wide" { 22.0 } else { 30.0 };
    if !contact { rate = rate * 1.2; }
    ((4.0 + pax.to_float() / rate) * 60.0).to_int()
}''',
'deboard_sec': '''fn deboard_sec(body, pax, contact, carrier_type) {
    if body == "narrow" {
        let m = if carrier_type == "low" { gamma(0.21, 49.83) - 5.29 } else { gamma(1.46, 2.71) };
        if m < 1.0 { m = 1.0; }
        return (m * 60.0 * svc_scale(carrier_type)).to_int();
    }
    let rate = if body == "regional" { 15.0 } else if body == "wide" { 35.0 } else { 50.0 };
    if !contact { rate = rate * 1.35; }
    ((2.0 + pax.to_float() / rate) * 60.0).to_int()
}''',
'fuel_sec': '''fn fuel_sec(litres, rate_lpm, body, carrier_type) {
    if body == "narrow" {
        let m = if carrier_type == "low" { gamma(1.1, 21.32) - 11.75 } else { 2.0 + gamma(9.12, 1.64) };
        if m < 3.0 { m = 3.0; }
        return (m * 60.0 * svc_scale(carrier_type)).to_int();
    }
    let acc = accept_lpm(body);
    let rate = if rate_lpm < acc { rate_lpm } else { acc };
    ((4.0 + litres.to_float() / rate.to_float() + 3.0) * 60.0).to_int()
}''',
}
CARRIER_ARCS = {
    'e82': 'delay_sec(deboard_sec(tr.arr.aircraft.body, tr.arr.pax, true, tr.arr.carrierType))',
    'e85': 'delay_sec(drive_sec_between(bus.x, bus.y, tr.stand.x, tr.stand.y) + deboard_sec(tr.arr.aircraft.body, tr.arr.pax, false, tr.arr.carrierType) + bus_sec(tr.arr.pax, bus.cap))',
    'e111': 'delay_sec(drive_sec_between(cat.x, cat.y, tr.stand.x, tr.stand.y) + cater_sec(tr.dep.aircraft.body, tr.dep.sectorMin, tr.dep.carrierType))',
    'e126': 'delay_sec(board_sec(tr.dep.aircraft.body, tr.dep.pax, true, tr.dep.carrierType))',
    'e129': 'delay_sec(drive_sec_between(bus.x, bus.y, tr.stand.x, tr.stand.y) + bus_sec(tr.dep.pax, bus.cap) + board_sec(tr.dep.aircraft.body, tr.dep.pax, false, tr.dep.carrierType))',
    'e164': 'delay_sec(fuel_sec(tr.upliftL, fu.rateLpm, tr.dep.aircraft.body, tr.dep.carrierType))',
}
# v4 (2026-11-27): carrier-specific narrow-body baggage unloading/loading, as parameterised in Tkacenko (2026)
# (cpns/durations.py): full-service from Asadi (2024), low-cost from Luo et al. (2024, Schiphol).
# Python gammavariate(shape, scale) -> cpnsim gamma(scale, shape). Wide-bodies keep the baseline hold_sec.
BAGGAGE_FUNC = '''fn bag_sec(hold, pax, ulds, loading, body, carrier_type) {
    if body == "narrow" {
        let m = if loading {
            if carrier_type == "low" { gamma(3.85, 0.83) + 1.95 } else { gamma(1.24, 12.49) }
        } else {
            if carrier_type == "low" { gamma(1.9, 2.61) + 0.99 } else { gamma(1.24, 8.95) }
        };
        if m < 1.0 { m = 1.0; }
        return (m * 60.0 * svc_scale(carrier_type)).to_int();
    }
    hold_sec(hold, pax, ulds, loading)
}'''
BAGGAGE_ARCS = {
    'e140': 'delay_sec(drive_sec_between(ldr.x, ldr.y, tr.stand.x, tr.stand.y) + bag_sec(tr.hold, tr.arr.pax, tr.nUlds, false, tr.arr.aircraft.body, tr.arr.carrierType))',
    'e150': 'delay_sec(drive_sec_between(ldr.x, ldr.y, tr.stand.x, tr.stand.y) + bag_sec(tr.hold, tr.dep.pax, tr.nDepUlds, true, tr.dep.aircraft.body, tr.dep.carrierType))',
}


def det_load_factor(dt, carrier_type):
    """Deterministic part of the baseline's load_factor() (business model, month, weekday, hour)."""
    base = 0.905 if carrier_type == 'low' else 0.820
    seasonal = [0.0, -0.065, -0.075, -0.030, 0.000, 0.015, 0.038, 0.055, 0.050, 0.025, 0.000, -0.045, -0.015]
    weekday = [0.020, -0.020, -0.035, -0.035, -0.005, 0.035, 0.010]  # index 0 = Sunday
    h = dt.hour
    daily = 0.030 if h < 8 else 0.005 if h < 11 else -0.030 if h < 16 else 0.010 if h < 20 else 0.030
    return min(0.99, max(0.42, base + seasonal[dt.month] + weekday[(dt.weekday() + 1) % 7] + daily))


def build(date=None, limit=None, suffix=None, load_factor=.85, cleaning_teams=9, service_scale=1.0, timing='literature', curfew='inherited', hydrant_dispensers=4, fuel_tankers=4, out_dir=None, schedule='none', utc_offset_hours=1, context='basic', weather='synthetic', scale_low=1.0, scale_full=1.0, leisure_profile='full', stand_policy='any', buses=None, loaders=None, board_scale=1.0, source=None, baggage='baseline'):
    # v2.2 options (defaults reproduce v2.0/v2.1 builds exactly):
    #   curfew='ber_local'  -> 00:00-05:00 LOCAL night ban, applied only at pushback clearance (e191)
    #   schedule='std'      -> aircraft may not request start-up before its A-CDM STD (linked cases only)
    # v3 options:
    #   context='enriched'  -> scope/airline/carrier class/aircraft type from ber_turnarounds_enriched.csv,
    #                          passenger load from the baseline's carrier-dependent load-factor profile
    #   timing='carrier'    -> carrier-specific narrow-body service times (CARRIER_FUNCS)
    #   weather='observed'  -> temperature and precipitation from observed BER hourly weather (Open-Meteo)
    #   scale_low/scale_full-> calibration multipliers on carrier-specific narrow-body service times
    assert curfew in ('inherited','none','ber_local') and schedule in ('none','std')
    assert timing in ('literature','baseline','carrier') and context in ('basic','enriched') and weather in ('synthetic','observed')
    std_lookup=load_std_lookup() if schedule=='std' else {}
    src = Path(source) if source else (ENRICHED if context=='enriched' else SOURCE)
    rows=list(csv.DictReader(src.open(encoding='utf-8-sig')))
    if context=='enriched': rows=[r for r in rows if r['in_scope']=='True']
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
    if context=='enriched': specs.update(EXTRA_SPECS)
    for i,r in enumerate(rows,1):
        ident=r['aircraft_icao24']
        observed=(r['aircraft_type'] if context=='enriched' else r['aircraft_type_from_candidate_acdm_reference']).strip().upper()
        typ=observed if observed in specs else 'A320'
        body,seats,cap,letter=specs[typ]
        airline=(r['airline_name'] or r['airline_icao'] or 'UNKNOWN') if context=='enriched' else (r['airline_from_candidate_acdm_reference'] or 'UNKNOWN')
        ac={'id':'ICAO24-'+ident,'typeCode':typ,'codeLetter':letter,'body':body,'seats':seats,'fuelCapL':cap,'airline':airline}
        # Use one stable configuration per physical aircraft within a build.
        if ident not in fleet: fleet[ident]=ac
        ac=fleet[ident]
        case='BER-'+str(i).zfill(5)
        if context=='enriched':
            ctype='low' if r['carrier_class']=='low-cost' or (leisure_profile=='low' and r['carrier_class']=='leisure') else 'full'
            pax=round(ac['seats']*det_load_factor(datetime.fromisoformat(r['outbound_first_seen_berlin']),ctype))
        else:
            ctype='unknown'; pax=round(ac['seats']*load_factor)
        fl={'id':'ARR-'+case,'callsign':r['inbound_callsign'] or 'UNKNOWN','airline':ac['airline'],'carrierType':ctype,'direction':'ARR','schengen':False,'station':r['inbound_origin'] or 'UNKNOWN','pax':pax,'prm':0,'sectorMin':120,'aircraft':ac,'studyCase':case,'pairedCallsign':r['outbound_callsign'] or 'UNKNOWN','pairedDestination':r['outbound_destination'] or 'UNKNOWN','inputBasis':'OpenSky airborne-boundary proxy','contextBasis':'type candidate if supported; seats/load/PRM/sector assumed; border segregation disabled'}
        ms=round((datetime.fromisoformat(r['inbound_last_seen_utc'])-epoch).total_seconds()*1000)
        std=std_lookup.get(r.get('acdm_reference_key') or '')
        std_ms=round((std-epoch).total_seconds()*1000) if std else 0
        if schedule=='std': fl['stdMs']=std_ms
        flights.append((fl,ms))
        manifest.append(dict(r,model_carrier_type=ctype,model_std_ms=std_ms,schedule_bound=bool(std_ms),study_case_id=case,model_arrival_flight_id=fl['id'],model_departure_flight_id='DEP-'+case,model_aircraft_id=ac['id'],model_release_ms=ms,model_type=ac['typeCode'],type_supported_candidate=bool(observed in specs),model_passengers=fl['pax'],model_carrier_profile='unknown'))
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
    if curfew=='ber_local':
        # BER core night restriction 00:00-05:00 LOCAL time (airport guidance). The runtime clock is UTC,
        # so the local hour is computed with a fixed offset (CET, valid for the November study dates).
        # Shoulder windows and exception quotas are not modelled. The ban acts only on the movement
        # boundary (pushback clearance, e191); cabin work (e106) is no longer embargoed.
        off=int(utc_offset_hours*3600000)
        funcs['in_night_ban']['code']=f'''fn in_night_ban(t) {{
    // BER core night window, local time = UTC + {utc_offset_hours} h (CET).
    hour_of_day(t + {off}) < 5
}}'''
        funcs['curfew_delay']['code']=f'''fn curfew_delay(base) {{
    let due = current_time() + base;
    if !in_night_ban(due) {{ return base; }}
    let loc = due + {off};
    let midnight_loc = loc - hour_of_day(loc) * 3600000 - minute_of_hour(loc) * 60000 - second_of_minute(loc) * 1000;
    // Reopen at 05:00 local, spread over the first 30 minutes.
    let open = midnight_loc + 5 * 3600000 + discrete(0, 1800) * 1000 - {off};
    open - current_time()
}}'''
        arcs['e106']['delay']=''
    if schedule=='std':
        # Schedule-bound departure: an aircraft that is ready early waits on stand until its STD
        # before requesting start-up. STD is a timetable input, not an observed outcome.
        p['functions'].append({'id':'fn-sched_wait','name':'sched_wait','code':'''fn sched_wait(std) {
    if std <= 0 { return 0; }
    let w = std - current_time();
    if w > 0 { w } else { 0 }
}'''})
        funcs['sched_wait']=p['functions'][-1]
        arcs['e187']['delay']='sched_wait(tr.dep.stdMs)'
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
    if timing=='carrier':
        for name,code in CARRIER_FUNCS.items(): funcs[name]['code']=code
        p['functions'].append({'id':'fn-svc_scale','name':'svc_scale','code':f'fn svc_scale(carrier_type) {{ if carrier_type == "low" {{ {float(scale_low)} }} else {{ {float(scale_full)} }} }}'})
        for aid,expr in CARRIER_ARCS.items(): arcs[aid]['delay']=expr
        if baggage=='carrier':
            p['functions'].append({'id':'fn-bag_sec','name':'bag_sec','code':BAGGAGE_FUNC})
            for aid,expr in BAGGAGE_ARCS.items():
                assert 'hold_sec(' in arcs[aid]['delay'], aid
                arcs[aid]['delay']=expr
    assert baggage in ('baseline','carrier')
    if timing=='carrier' and board_scale!=1.0:
        # Process change: faster boarding (e.g. improved boarding procedure), narrow-body only.
        funcs['board_sec']['code']=funcs['board_sec']['code'].replace('svc_scale(carrier_type)).to_int();','svc_scale(carrier_type) * '+str(float(board_scale))+').to_int();',1)
    if stand_policy=='lcc_remote':
        # Allocation strategy: low-cost turnarounds on remote stands, all others on contact stands.
        trans['a-t-stand-contact']['guard']='st.contact && stand_fits(st, fl.aircraft, fl.schengen) && fl.carrierType != "low"'
        trans['a-t-stand-remote']['guard']='!st.contact && stand_fits(st, fl.aircraft, fl.schengen) && fl.carrierType == "low"'
    for pid,count in (('c-buses',buses),('r-loaders',loaders)):
        if count:
            orig=places[pid]['marking']; pre=orig[0]['id'].rsplit('-',1)[0]
            mark(pid,[dict(orig[i % len(orig)],id=pre+'-'+str(i+1)) for i in range(count)])
    if weather=='observed':
        # Replace the synthetic weather generator by observed hourly BER weather (Open-Meteo archive, UTC).
        wx=json.loads(WEATHER.read_text())['hourly']
        t0=datetime.fromisoformat(wx['time'][0]).replace(tzinfo=timezone.utc)
        start=int((epoch-t0).total_seconds()//3600)-24
        span=24*6
        last=len(wx['time'])-1; ix=lambda k: min(start+k,last)  # hold the last observed hour beyond the archive end
        temps=[wx['temperature_2m'][ix(k)] for k in range(span)]
        wet=[1 if ((wx['precipitation'][ix(k)] or 0)>=0.1 or (wx['snowfall'][ix(k)] or 0)>0) else 0 for k in range(span)]
        funcs['temp_c']['code']='fn temp_c(t) {\n    // Observed BER 2 m temperature (Open-Meteo archive), hourly, starting 24 h before the epoch.\n    let tc = ['+','.join(f'{x:.1f}' for x in temps)+'];\n    let i = t / 3600000 + 24;\n    if i < 0 { i = 0; }\n    if i >= tc.len() { i = tc.len() - 1; }\n    tc[i]\n}'
        funcs['precip_at']['code']='fn precip_at(t) {\n    // Observed BER precipitation >= 0.1 mm/h or snowfall (Open-Meteo archive).\n    let pw = ['+','.join(map(str,wet))+'];\n    let i = t / 3600000 + 24;\n    if i < 0 { i = 0; }\n    if i >= pw.len() { i = pw.len() - 1; }\n    pw[i] == 1\n}'
    # Sensitivity multiplier is an explicit scenario assumption, not an estimated effect.
    for aid in ('e103','e126','e129','e164'):
        delay=arcs[aid]['delay']
        for call in ('clean_sec(tr.arr.aircraft.body, tr.arr.carrierType)','board_sec(tr.dep.aircraft.body, tr.dep.pax, true)','board_sec(tr.dep.aircraft.body, tr.dep.pax, false)','fuel_sec(tr.upliftL, fu.rateLpm, tr.dep.aircraft.body)'):
            if call in delay: delay=delay.replace(call,'('+call+'.to_float() * '+str(service_scale)+').to_int()')
        arcs[aid]['delay']=delay
    for cs in p['colorSets']:
        if cs['name']=='Flight': cs['definition']=cs['definition'].replace(' * aircraft: Aircraft timed;', ' * aircraft: Aircraft * studyCase: STRING * pairedCallsign: STRING * pairedDestination: STRING * inputBasis: STRING * contextBasis: STRING'+(' * stdMs: INT' if schedule=='std' else '')+' timed;')
    # Retain topology/capacities as explicit inherited assumptions, rather than invent BER assets.
    p['ocpnName']='BER MSc - Empirical Arrival Demand - '+(date or 'All Core Proxies')
    p['metadata'].update(name=p['ocpnName'],version='2.0-study-draft',description='MSc derivative of Istvan Koren\'s Airport Ground Handling (Extended). Finite BER same-aircraft paired demand; literature-informed single-aisle service times. NOT a validated digital twin. Layout, resource capacities, weather and remaining process times are inherited fictional assumptions. Six parallel handling threads. Input timestamps are airborne boundary proxies, not ALDT/AIBT. Departure observations are external evaluation targets, never simulator timing inputs. See README and build_manifest.json.',authors=p['metadata']['authors']+['Amir (MSc study adaptation)'])
    p['metadata']['description']=p['metadata']['description'].replace('build_manifest.json','the companion *_manifest.json')
    if timing=='baseline':p['metadata']['description']=p['metadata']['description'].replace('literature-informed single-aisle service times','original baseline service-time functions retained for a same-demand comparison')
    if curfew=='ber_local' or schedule=='std':
        p['metadata']['version']='2.2-ber-policy-schedule'
        p['metadata']['description']+=' v2.2: BER 00:00-05:00 local-time night ban at pushback clearance only; schedule binding='+schedule+' (STD from linked A-CDM records).'
    elif curfew!='inherited' or out_dir:
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
    info.update(baggage_timing=baggage if timing=='carrier' else 'baseline')
    info.update(stand_policy=stand_policy,buses=buses,loaders=loaders,board_scale=board_scale,leisure_profile=leisure_profile,context=context,weather=weather,scale_low=scale_low,scale_full=scale_full,carrier_types={k:sum(1 for m in manifest if m['model_carrier_type']==k) for k in ('low','full','unknown')})
    info.update(schedule_binding=schedule,schedule_bound_cases=sum(1 for m in manifest if m['schedule_bound']),utc_offset_hours=utc_offset_hours if curfew=='ber_local' else None)
    (destination/(stem+'_manifest.json')).write_text(json.dumps(info,indent=2),encoding='utf-8')
    print(json.dumps(info))
    return target

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--date');a.add_argument('--limit',type=int);a.add_argument('--suffix');a.add_argument('--load-factor',type=float,default=.85);a.add_argument('--cleaning-teams',type=int,default=9);a.add_argument('--service-scale',type=float,default=1.0);a.add_argument('--timing',choices=['literature','baseline'],default='literature');a.add_argument('--curfew',choices=['inherited','none','ber_local'],default='inherited');a.add_argument('--schedule',choices=['none','std'],default='none');a.add_argument('--hydrant-dispensers',type=int,default=4);a.add_argument('--fuel-tankers',type=int,default=4);a.add_argument('--out-dir');args=a.parse_args();build(**vars(args))
