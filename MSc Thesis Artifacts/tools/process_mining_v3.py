"""Object-centric process mining on simulated OCEL 2.0 logs (PM4Py).

Usage: python process_mining_v3.py <out_dir> <ocel.json> [<ocel.json> ...]
Produces (in out_dir):
  ocdfg_turnaround_resources.png/svg   OC-DFG (frequency) for Turnaround + shared-resource object types
  ocdfg_turnaround_performance.png     OC-DFG annotated with median durations
  ocpn.png                             discovered object-centric Petri net (Turnaround + resources)
  carrier_activity_durations.csv       median service durations by carrier class (from the flattened log)
  carrier_variants.json                variant counts per carrier class
  conformance.json                     token-based replay fitness: models discovered per class, replayed on the other class
  resource_load.csv                    turnarounds served per resource object and day
"""
import json, re, sys
from pathlib import Path
import pandas as pd
import pm4py

KEEP = ['Turnaround', 'Fueller', 'Bus', 'CleaningTeam', 'PushbackTug', 'CateringTruck', 'Loader']
PAIRS = {  # service: (start activity, end activity)
    'deplaning': (r'Deplaning Start', r'Deplaning\s*Complete'),
    'cleaning': (r'Cabin Cleaning\s*Start', r'Cabin Cleaning\s*Complete'),
    'catering': (r'Catering\s*Start', r'Catering\s*Complete'),
    'refuelling': (r'Refuelling\s*Start', r'Refuelling\s*Complete'),
    'boarding': (r'Boarding Start', r'Boarding\s*Complete'),
    'ground_handling': (r'Start Ground', r'Aircraft Ready'),
}


def clean(a):
    return re.sub(r'\s+', ' ', a).strip()


def carrier_of_turnarounds(ocel):
    """carrier type per Turnaround object, read from the related inbound Flight's carrierType attribute."""
    obj = ocel.objects
    col = [c for c in obj.columns if c.lower() == 'carriertype']
    o2o = ocel.o2o
    if not col: return {}
    fl = obj[obj['ocel:type'] == 'Flight'].set_index('ocel:oid')[col[0]].to_dict()
    m = {}
    for _, r in o2o.iterrows():
        if r['ocel:oid'].startswith('turnaround_') and r['ocel:oid_2'] in fl and r['ocel:qualifier'] == 'inbound flight':
            m[r['ocel:oid']] = fl[r['ocel:oid_2']]
    return m


def main(out, files):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    durations, variants, conf, loads = [], {}, {}, []
    logs = []
    for f in files:
        ocel = pm4py.read_ocel2_json(f)
        ocel.events['ocel:activity'] = ocel.events['ocel:activity'].map(clean)
        ocel.relations['ocel:activity'] = ocel.relations['ocel:activity'].map(clean)
        day = Path(f).stem.split('_')[2]
        cmap = carrier_of_turnarounds(ocel)
        # flattened turnaround log
        flat = pm4py.ocel_flattening(ocel, 'Turnaround')
        flat['carrier'] = flat['case:concept:name'].map(cmap).fillna('unknown'); flat['day'] = day
        flat['case:concept:name'] = day + '_' + flat['case:concept:name']  # turnaround ids repeat across days
        logs.append(flat)
        # resource load: distinct turnarounds per resource object
        rel = ocel.relations
        tas = rel[rel['ocel:type'] == 'Turnaround'][['ocel:eid', 'ocel:oid']].rename(columns={'ocel:oid': 'ta'})
        res = rel[rel['ocel:type'].isin(KEEP[1:])][['ocel:eid', 'ocel:oid', 'ocel:type']]
        j = res.merge(tas, on='ocel:eid').groupby(['ocel:type', 'ocel:oid']).ta.nunique().reset_index(name='turnarounds')
        j['day'] = day; loads.append(j)
        if f == files[0]:
            sub = pm4py.filter_ocel_object_types(ocel, KEEP)
            dfg = pm4py.discover_ocdfg(sub)
            pm4py.save_vis_ocdfg(dfg, str(out / 'ocdfg_turnaround_resources.png'), annotation='frequency', act_metric='events', edge_metric='event_couples', act_threshold=0, edge_threshold=60, rankdir='LR')
            pm4py.save_vis_ocdfg(dfg, str(out / 'ocdfg_turnaround_resources.svg'), annotation='frequency', act_metric='events', edge_metric='event_couples', act_threshold=0, edge_threshold=60, rankdir='LR')
            pm4py.save_vis_ocdfg(dfg, str(out / 'ocdfg_turnaround_performance.png'), annotation='performance', performance_aggregation='median', act_threshold=0, edge_threshold=60, rankdir='LR')
            rdfg = pm4py.discover_ocdfg(pm4py.filter_ocel_object_types(ocel, KEEP[1:]))
            pm4py.save_vis_ocdfg(rdfg, str(out / 'ocdfg_resources_only.png'), annotation='frequency', act_threshold=0, edge_threshold=3, rankdir='LR')
            ocpn = pm4py.discover_oc_petri_net(pm4py.filter_ocel_object_types(ocel, ['Turnaround', 'Fueller', 'Bus', 'CleaningTeam']))
            pm4py.save_vis_ocpn(ocpn, str(out / 'ocpn.png'), rankdir='TB')
            stats = dict(events=len(ocel.events), objects=len(ocel.objects), e2o=len(ocel.relations), o2o=len(ocel.o2o),
                         object_types=pm4py.ocel_get_object_types(ocel), activities=int(ocel.events['ocel:activity'].nunique()))
            (out / 'ocel_stats.json').write_text(json.dumps(stats, indent=2))
    L = pd.concat(logs, ignore_index=True)
    L = L.sort_values(['case:concept:name', 'time:timestamp'])
    # service durations per carrier (first start -> first matching end within a case)
    for svc, (s, e) in PAIRS.items():
        st = L[L['concept:name'].str.contains(s)].groupby('case:concept:name')['time:timestamp'].min()
        en = L[L['concept:name'].str.contains(e)].groupby('case:concept:name')['time:timestamp'].min()
        dd = ((en - st).dt.total_seconds() / 60).dropna().rename('min').reset_index()
        dd['carrier'] = dd['case:concept:name'].map(L.drop_duplicates('case:concept:name').set_index('case:concept:name').carrier)
        for c, g in dd.groupby('carrier'):
            durations.append(dict(service=svc, carrier=c, n=len(g), median=round(g['min'].median(), 2), p90=round(g['min'].quantile(.9), 2)))
    pd.DataFrame(durations).to_csv(out / 'carrier_activity_durations.csv', index=False)
    for c, g in L.groupby('carrier'):
        if c == 'unknown': continue
        v = pm4py.get_variants(g, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
        variants[c] = dict(cases=int(g['case:concept:name'].nunique()), variants=len(v),
                           top5_share=round(sum(sorted([len(x) if isinstance(x, list) else x for x in v.values()], reverse=True)[:5]) / g['case:concept:name'].nunique(), 3))
    (out / 'carrier_variants.json').write_text(json.dumps(variants, indent=2))
    # conformance: discover on one carrier class, replay the other (and itself)
    groups = {c: g for c, g in L.groupby('carrier') if c in ('low', 'full')}
    models = {c: pm4py.discover_petri_net_inductive(g, noise_threshold=0.2, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp') for c, g in groups.items()}
    for mc, (net, im, fm) in models.items():
        for lc, g in groups.items():
            fit = pm4py.fitness_token_based_replay(g, net, im, fm, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
            prec = pm4py.precision_token_based_replay(g, net, im, fm, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
            conf[f'model_{mc}__log_{lc}'] = dict(fitness=round(fit['log_fitness'], 4), perc_fit_traces=round(fit['perc_fit_traces'], 2), precision=round(prec, 4))
        pm4py.save_vis_petri_net(net, im, fm, str(out / f'petri_turnaround_{mc}.png'))
    (out / 'conformance.json').write_text(json.dumps(conf, indent=2))
    pd.concat(loads).to_csv(out / 'resource_load.csv', index=False)
    print(json.dumps(dict(variants=variants, conformance=conf), indent=1)); print(pd.DataFrame(durations).to_string())


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
