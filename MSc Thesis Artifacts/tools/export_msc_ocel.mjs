// Use Studio's own OCEL conversion, preserving nested object identities and qualifiers.
import fs from 'node:fs';
import {convertToOCEL2} from './studio_ocel_export.ts';
const file=process.argv[2];
const model=JSON.parse(fs.readFileSync(file,'utf8'));
const stem=file.replace(/\.ocpn$/,'');
const raw=JSON.parse(fs.readFileSync(stem+'_run_events.json','utf8'));
const places=model.petriNets.flatMap(n=>n.places),transitions=model.petriNets.flatMap(n=>n.transitions),arcs=model.petriNets.flatMap(n=>n.arcs);
const names=new Map(places.map(p=>[p.id,p.name]));
const events=raw.map((e,i)=>({id:'e'+(i+1),step:i+1,time:e.simulationTime,transitionId:e.transitionId,transitionName:e.transitionName,timestamp:new Date(Date.parse(model.simulationEpoch)+e.simulationTime),tokens:Object.fromEntries(['consumed','produced'].map(direction=>[direction,Object.entries(e[direction]).map(([placeId,tokens])=>({placeId,placeName:names.get(placeId)??placeId,tokens:JSON.stringify(tokens)}))]))}));
const included=new Set(transitions.filter(t=>!t.subPageId&&t.includeInOcel!==false).map(t=>t.id));
const ocel=convertToOCEL2(events,model.colorSets,transitions,places,model.simulationEpoch,arcs,included);
// Studio uses CPN type names and stringified primitives. Normalize for strict OCEL importers.
const aliases={int:'integer',real:'float',bool:'boolean'};
for(const [typeKey,itemKey] of [['objectTypes','objects'],['eventTypes','events']]){
  const schemas=new Map();
  for(const t of ocel[typeKey]){for(const a of t.attributes)a.type=aliases[a.type]??a.type;schemas.set(t.name,new Map(t.attributes.map(a=>[a.name,a.type])));}
  for(const item of ocel[itemKey])for(const a of item.attributes){
    const t=schemas.get(item.type)?.get(a.name);
    if(t==='integer'||t==='float'){a.value=Number(a.value);if(!Number.isFinite(a.value)||(t==='integer'&&!Number.isInteger(a.value)))throw Error('Invalid numeric attribute');}
    if(t==='boolean'){if(a.value!=='true'&&a.value!=='false')throw Error('Invalid boolean attribute');a.value=a.value==='true';}
  }
}
const ids=new Set(ocel.objects.map(o=>o.id));
for(const e of ocel.events){if(!Number.isFinite(Date.parse(e.time)))throw Error('Invalid timestamp');for(const r of e.relationships)if(!ids.has(r.objectId))throw Error('Dangling e2o');}
for(const o of ocel.objects)for(const r of o.relationships)if(!ids.has(r.objectId))throw Error('Dangling o2o');
fs.writeFileSync(stem+'.ocel.json',JSON.stringify(ocel,null,2));
console.log(JSON.stringify({file:stem+'.ocel.json',events:ocel.events.length,objects:ocel.objects.length,objectTypes:ocel.objectTypes.map(t=>t.name),eventTypes:ocel.eventTypes.length}));
