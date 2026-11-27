// Headless validation with the same cpnsim 0.6.2 engine used by Studio.
import fs from 'node:fs';
import path from 'node:path';
import {initSync,WasmSimulator} from '../tmp/ocpn_runtime/package/cpnsim.js';
const input=process.argv[2];
if(!input) throw Error('Usage: node tools/run_msc_ocpn.mjs model.ocpn [maxSteps]');
const raw=JSON.parse(fs.readFileSync(input,'utf8'));
const p=structuredClone(raw), alias=new Map(), substitution=new Set();
for(const n of p.petriNets)for(const t of n.transitions)if(t.subPageId){
  substitution.add(t.id);
  for(const a of t.socketAssignments??[])alias.set(a.portPlaceId,a.socketPlaceId);
}
const resolve=id=>alias.has(id)?resolve(alias.get(id)):id;
const flat={id:'flat',name:p.ocpnName,places:[],transitions:[],arcs:[]};
for(const n of p.petriNets){
  for(const x of n.places)if(!alias.has(x.id))flat.places.push(x);
  flat.transitions.push(...n.transitions.filter(t=>!substitution.has(t.id)));
  flat.arcs.push(...n.arcs.filter(a=>!substitution.has(a.source)&&!substitution.has(a.target)).map(a=>({...a,source:resolve(a.source),target:resolve(a.target)})));
}
for(const x of flat.places)x.marking=JSON.stringify(x.marking??[]);
p.petriNets=[flat];
initSync({module:fs.readFileSync(new URL('../tmp/ocpn_runtime/package/cpnsim_bg.wasm',import.meta.url))});
const norm=x=>x instanceof Map?Object.fromEntries([...x].map(([k,v])=>[k,norm(v)])):Array.isArray(x)?x.map(norm):x&&typeof x==='object'?Object.fromEntries(Object.entries(x).map(([k,v])=>[k,norm(v)])):typeof x==='bigint'?Number(x):x;
const sim=new WasmSimulator(JSON.stringify(p));
const events=[],max=Number(process.argv[3]??50000);
for(let i=0;i<max;i++){
  const ev=sim.run_step();if(!ev)break;
  events.push(norm(ev));
  if(i%100===99)console.log('progress',i+1,Number(sim.getCurrentTime()));
}
const marking=norm(sim.getMarking());
const summary={runtime:'@rwth-pads/cpnsim 0.6.2',model:path.basename(input),firings:events.length,currentTimeMs:Number(sim.getCurrentTime()),departed:marking['p-departed']?.length??0,pendingDemand:marking['s-clock']?.length??0,availableAircraft:marking['p-fleet']?.length??0,enabledTransitions:max>0?norm(sim.getEnabledTransitions()):'not queried (load-only validation)',placeCounts:Object.fromEntries(Object.entries(marking).map(([k,v])=>[k,v.length]))};
const stem=input.replace(/\.ocpn$/,'');
fs.writeFileSync(stem+'_run_events.json',JSON.stringify(events));
fs.writeFileSync(stem+'_run_summary.json',JSON.stringify(summary,null,2));
console.log(JSON.stringify({...summary,placeCounts:undefined}));
if(events.length)console.log('event sample',JSON.stringify(events[0]).slice(0,1600));
sim.free();
