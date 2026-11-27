// One independent replication, using official cpnsim WASM 0.6.2.
import fs from 'node:fs';
import crypto from 'node:crypto';
import {initSync,WasmSimulator} from '../tmp/ocpn_runtime/package/cpnsim.js';
const plan=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),job=plan.jobs[Number(process.argv[3])];
const model=JSON.parse(fs.readFileSync(job.model,'utf8'));
const aliases=new Map(),substitutions=new Set();
for(const n of model.petriNets)for(const t of n.transitions)if(t.subPageId){substitutions.add(t.id);for(const a of t.socketAssignments??[])aliases.set(a.portPlaceId,a.socketPlaceId);}
const resolve=id=>aliases.has(id)?resolve(aliases.get(id)):id;
const flat={id:'flat',name:model.ocpnName,places:[],transitions:[],arcs:[]};
for(const n of model.petriNets){flat.places.push(...n.places.filter(p=>!aliases.has(p.id)));flat.transitions.push(...n.transitions.filter(t=>!substitutions.has(t.id)));flat.arcs.push(...n.arcs.filter(a=>!substitutions.has(a.source)&&!substitutions.has(a.target)).map(a=>({...a,source:resolve(a.source),target:resolve(a.target)})));}
for(const p of flat.places)p.marking=JSON.stringify(p.marking??[]);
model.petriNets=[flat];
initSync({module:fs.readFileSync(new URL('../tmp/ocpn_runtime/package/cpnsim_bg.wasm',import.meta.url))});
const sim=new WasmSimulator(JSON.stringify(model));
const get=(x,k)=>x instanceof Map?x.get(k):x?.[k];
const values=x=>x instanceof Map?x.values():Object.values(x??{});
function caseIds(x,out=new Set()){
  if(Array.isArray(x)){for(const y of x)caseIds(y,out);return out;}
  if(x&&typeof x==='object'){
    const c=get(x,'studyCase'),id=get(x,'id');
    if(c){out.add(c);return out;}
    if(typeof id==='string'){if(id.startsWith('TA-BER-'))out.add(id.slice(3));return out;}
    for(const y of values(x))caseIds(y,out);
  }
  return out;
}
const watched=new Set(['s-t-file','a-t-inblock','t-aght','t-joined','d-t-ardt','d-t-push-start','d-t-takeoff','c-t-clean-start','c-t-clean-end','c-t-deb-bridge-end','c-t-deb-bus-end','c-t-board-bridge','c-t-board-bus','c-t-board-bridge-end','c-t-board-bus-end','r-t-fuel-hyd','r-t-fuel-tnk','r-t-fuel-start','r-t-fuel-end','d-t-tug-attach','d-t-asat','d-t-deice-start']);
const branches={'c-t-doors':'Cabin / boarding','r-t-load-end':'Baggage hold','r-t-fuel-end':'Fuel','r-t-lav-end':'Water / lavatory','r-t-water-skip':'Water / lavatory','c-t-cater-end':'Catering','c-t-cater-skip':'Catering','d-t-tsat':'Departure planning'};
const cases=new Map();let steps=0,halted=false;
const started=performance.now();
while(steps<plan.max_steps){
  const event=sim.run_step();if(!event){halted=true;break;}steps++;
  const tid=event.transitionId,time=event.simulationTime;
  if(watched.has(tid))for(const id of caseIds([event.consumed,event.produced])){
    if(!cases.has(id))cases.set(id,{events:{},branches:[]});
    const c=cases.get(id);if(c.events[tid]===undefined)c.events[tid]=time;
  }
  if(branches[tid])for(const tok of get(event.produced,'p-thread-done')??[]){
    const val=get(tok,'value')??tok,id=get(val,'id')?.slice(3);
    if(id&&cases.has(id))cases.get(id).branches.push({name:branches[tid],time:get(tok,'timestamp')??time});
  }
  if(steps%2000===0)fs.writeFileSync(job.output+'_progress.json',JSON.stringify({steps,timeMs:time,elapsedSeconds:(performance.now()-started)/1000}));
}
const manifest=JSON.parse(fs.readFileSync(job.model.replace(/\.ocpn$/,'_manifest.json'),'utf8'));
const initial=new Map(flat.places.map(p=>[p.id,JSON.parse(p.marking)]));
const marking=sim.getMarking();
const counts=id=>(get(marking,id)??[]).length;
if(!halted||counts('p-departed')!==manifest.cases||counts('s-clock')!==0||counts('p-fleet')!==manifest.aircraft)throw Error('Replication failed completion/aircraft integrity');
for(const id of ['p-stands','p-runways','c-clean','r-fuellers','d-tugs'])if(counts(id)!==initial.get(id).length)throw Error('Resource return failure: '+id);
const perCase=[];
for(const [id,c] of cases){
 const e=c.events;
 const at=(...ids)=>Math.min(...ids.map(k=>e[k]).filter(x=>x!==undefined));
 const gap=(a,b)=>(a-b)/60000;
 if(c.branches.length!==6)throw Error('Expected six branches for '+id);
 const latest=Math.max(...c.branches.map(b=>b.time));
 const r={case:id,block_min:gap(e['d-t-push-start'],e['a-t-inblock']),release_to_takeoff_min:gap(e['d-t-takeoff'],e['s-t-file']),clean_wait_min:gap(e['c-t-clean-start'],at('c-t-deb-bridge-end','c-t-deb-bus-end')),fuel_wait_min:gap(at('r-t-fuel-hyd','r-t-fuel-tnk'),e['t-aght']),tug_wait_min:gap(e['d-t-tug-attach'],e['d-t-ardt']),fuel_service_min:gap(e['r-t-fuel-end'],e['r-t-fuel-start']),clean_service_access_min:gap(e['c-t-clean-end'],e['c-t-clean-start']),clean_to_board_min:gap(at('c-t-board-bridge','c-t-board-bus'),e['c-t-clean-end']),approval_to_offblock_min:gap(e['d-t-push-start'],e['d-t-asat']),release_to_ready_min:gap(e['d-t-ardt'],e['s-t-file']),release_ms:e['s-t-file'],ready_ms:e['d-t-ardt'],offblock_ms:e['d-t-push-start'],takeoff_ms:e['d-t-takeoff'],remote_stand:e['c-t-board-bus']!==undefined,deiced:e['d-t-deice-start']!==undefined,last_ready:c.branches.filter(b=>b.time===latest).map(b=>b.name).join(' + ')};
 for(const [key,v] of Object.entries(r))if(key.endsWith('_min')&&(!Number.isFinite(v)||v<0))throw Error('Invalid metric '+key+' '+id);
 perCase.push(r);
}
if(perCase.length!==manifest.cases)throw Error('Case coverage mismatch');
const mean=x=>x.reduce((a,b)=>a+b,0)/x.length;
const quantile=(x,q)=>{const s=[...x].sort((a,b)=>a-b),i=(s.length-1)*q;return s[Math.floor(i)]+(s[Math.ceil(i)]-s[Math.floor(i)])*(i%1);};
const summary={...job,model_sha256:crypto.createHash('sha256').update(fs.readFileSync(job.model)).digest('hex'),runtime:'cpnsim 0.6.2',steps,cases:perCase.length,complete:true,elapsed_seconds:(performance.now()-started)/1000,mean_block_min:mean(perCase.map(c=>c.block_min)),median_block_min:quantile(perCase.map(c=>c.block_min),.5),p90_block_min:quantile(perCase.map(c=>c.block_min),.9),mean_fuel_wait_min:mean(perCase.map(c=>c.fuel_wait_min)),p90_fuel_wait_min:quantile(perCase.map(c=>c.fuel_wait_min),.9),mean_clean_wait_min:mean(perCase.map(c=>c.clean_wait_min)),mean_tug_wait_min:mean(perCase.map(c=>c.tug_wait_min)),long_approval_cases:perCase.filter(c=>c.approval_to_offblock_min>30).length,long_preboard_cases:perCase.filter(c=>c.clean_to_board_min>30).length,cabin_last_share:perCase.filter(c=>c.last_ready==='Cabin / boarding').length/perCase.length};
fs.writeFileSync(job.output+'_cases.json',JSON.stringify(perCase));
fs.writeFileSync(job.output+'_summary.json',JSON.stringify(summary,null,2));
sim.free();console.log(JSON.stringify(summary));
