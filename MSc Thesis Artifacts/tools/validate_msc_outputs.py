"""Integrity checks for model, completed simulation and typed OCEL export."""
import csv,json,hashlib
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ocpn'
reports=[]
for model in sorted(OUT.glob('BER_MSc_*.ocpn')):
    if model.stem=='BER_MSc_smoke': continue # superseded development smoke
    p=json.loads(model.read_text(encoding='utf-8'))
    nodes=[x for n in p['petriNets'] for key in ('places','transitions') for x in n[key]]
    ids=[x['id'] for x in nodes];assert len(ids)==len(set(ids))
    for net in p['petriNets']:
        for arc in net['arcs']:assert arc['source'] in ids and arc['target'] in ids
    manifest=json.loads(model.with_name(model.stem+'_manifest.json').read_text())
    assert hashlib.sha256(model.read_bytes()).hexdigest()==manifest['model_sha256']
    cases=list(csv.DictReader(model.with_name(model.stem+'_cases.csv').open(encoding='utf-8-sig')))
    assert len(cases)==manifest['cases']
    assert len({r['interval_id'] for r in cases})==len(cases)
    summary_path=model.with_name(model.stem+'_run_summary.json')
    report={'model':model.name,'cases':len(cases),'structure':'pass','execution':'not run'}
    if summary_path.exists():
        s=json.loads(summary_path.read_text())
        if s['firings']:
            assert s['departed']==len(cases) and s['pendingDemand']==0
            assert s['availableAircraft']==manifest['aircraft'] and not s['enabledTransitions']
            for pid in ('p-stands','p-runways','c-clean','r-fuellers','d-tugs'):
                place=next(x for n in p['petriNets'] for x in n['places'] if x['id']==pid)
                assert s['placeCounts'][pid]==len(place['marking']),pid
            ev=json.loads(model.with_name(model.stem+'_run_events.json').read_text())
            releases=[e for e in ev if e['transitionId']=='s-t-file']
            assert len(releases)==len(cases)
            for e in releases:
                fl=e['consumed']['s-clock'][0];ac=e['consumed']['p-fleet'][0]
                if 'value' in fl:fl=fl['value']
                if 'value' in ac:ac=ac['value']
                assert fl['aircraft']['id']==ac['id']
            departures=[e for e in ev if e['transitionId']=='d-t-takeoff']
            assert len(departures)==len(cases)
            assert {e['produced']['p-departed'][0]['value']['studyCase'] for e in departures}=={c['study_case_id'] for c in cases}
            report.update(execution='completed',firings=s['firings'],departures=s['departed'],resource_return='pass')
        else:
            assert s['pendingDemand']==len(cases)
            report['execution']='load-only; all demand tokens present'
    ocel_path=model.with_suffix('.ocel.json')
    if ocel_path.exists():
        o=json.loads(ocel_path.read_text())
        objects={x['id']:x for x in o['objects']};assert len(objects)==len(o['objects'])
        assert len({e['id'] for e in o['events']})==len(o['events'])
        for tk,ik in [('objectTypes','objects'),('eventTypes','events')]:
            schemas={t['name']:{a['name']:a['type'] for a in t['attributes']} for t in o[tk]}
            for item in o[ik]:
                assert item['type'] in schemas
                for a in item['attributes']:
                    typ=schemas[item['type']][a['name']];v=a['value']
                    assert typ in ('string','integer','float','boolean','time')
                    assert (typ in ('string','time') and isinstance(v,str)) or (typ=='integer' and type(v)==int) or (typ=='float' and type(v) in (int,float)) or (typ=='boolean' and type(v)==bool)
                    if 'time' in a:datetime.fromisoformat(a['time'])
                for r in item['relationships']:assert r['objectId'] in objects
                if 'time' in item:datetime.fromisoformat(item['time'])
        report.update(ocel_events=len(o['events']),ocel_objects=len(o['objects']),ocel_integrity='pass; typed attributes, timestamps and relationships')
    reports.append(report)
(OUT/'validation_report.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps(reports,indent=2))
