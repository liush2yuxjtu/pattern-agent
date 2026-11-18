import assert from 'node:assert/strict';
import fs from 'node:fs';
import {FitLifecycle,SpecDraft} from '../src/studio-state.mjs';
const checks=[];function check(name,condition){assert.ok(condition,name);checks.push(name);}
const worker=()=>({terminated:false,terminateCount:0,onmessage(){},onerror(){},terminate(){this.terminated=true;this.terminateCount++;}});
let time=0;const fit=new FitLifecycle({now:()=>++time});
const first=fit.begin({revision:1,diagnostics:true}),old=worker();fit.attach(first,old);
check('Starting a job records its document revision and diagnostics intention',fit.snapshot().documentRevision===1&&fit.snapshot().diagnostics);
const second=fit.begin({revision:2});
check('A new job terminates the old worker and detaches callbacks',old.terminated&&old.onmessage===null&&old.onerror===null);
check('Diagnostic recording never leaks into a replacement job',!second.diagnostics&&!fit.snapshot().diagnostics);
const current=worker();fit.attach(second,current);
check('Late failure from an old job cannot stop the current worker',fit.fail(first,'late')===false&&fit.worker===current&&!current.terminated);
check('Late result from an old revision cannot become current data',fit.complete(first,{status:'PASS'})===false&&fit.state.phase==='SOLVING'&&!fit.state.report);
fit.complete(second,{status:'FAIL',reason:'geometric check'});
check('A completed geometric FAIL is readable data, distinct from a failed computation',fit.ready&&fit.state.status==='FAIL'&&!!fit.state.report&&!fit.worker);
const third=fit.begin({revision:3});fit.fail(third,'worker failed');
check('Computation failure removes the prior report and makes data unavailable',fit.state.phase==='ERROR'&&!fit.ready&&!fit.state.report);
const fourth=fit.begin({revision:3});fit.complete(fourth,{status:'PASS'});
check('Retry creates a fresh job and can reach a valid ready state',fit.ready&&fit.state.status==='PASS'&&fourth.generation>third.generation);
const missing=fit.begin({revision:4});fit.unavailable(missing,'body missing');
check('Missing assets have an explicit unavailable state with no old report',fit.state.phase==='UNAVAILABLE'&&!fit.state.report);
const attachJob=fit.begin({revision:5}),w1=worker(),w2=worker();fit.attach(attachJob,w1);fit.attach(attachJob,w2);
check('Attaching a replacement worker cannot leak the previously owned worker',w1.terminated&&fit.worker===w2&&!w2.terminated);

let seed=0x51a7e;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/2**32;};
const model=new FitLifecycle({now:()=>++time}),jobs=[],workers=[];let begins=0;
for(let i=0;i<5000;i++){
 const event=Math.floor(random()*6),job=jobs[Math.floor(random()*jobs.length)];
 if(event===0||!jobs.length){const j=model.begin({revision:++begins,diagnostics:random()<.3}),w=worker();model.attach(j,w);jobs.push(j);workers.push(w);}
 else if(event===1)model.complete(job,{status:random()<.8?'PASS':'FAIL'});
 else if(event===2)model.fail(job,'injected failure');
 else if(event===3)model.progress(job,{iter:Math.floor(random()*240)});
 else if(event===4)model.unavailable(job,'injected missing asset');
 else model.setSource(job,{cached:true});
 assert.equal(workers.filter(w=>!w.terminated).length,model.worker?1:0);
 assert.ok(!model.worker||model.state.phase==='SOLVING');
 assert.ok(!model.state.report||model.state.phase==='READY');
 assert.ok(model.state.phase!=='READY'||['PASS','FAIL'].includes(model.state.status));
}
check('5,000 deterministic adversarial job transitions preserve ownership and data validity',true);
check('The transition trace is bounded and records stale events',model.trace.length<=120&&model.trace.some(e=>e.event==='STALE_IGNORED'));
check('Trace transitions obey the explicit lifecycle graph',model.trace.every(e=>e.event==='BEGIN'?e.to==='SOLVING':e.event==='STALE_IGNORED'?e.from===e.to:e.from==='SOLVING'&&['READY','ERROR','UNAVAILABLE'].includes(e.to)));
model.stopWorker();

const timers=new Map(),callbacks=[],events=[];let timerId=0,base={length:0,sleeve:0},commits=[];
const queue=new SpecDraft({getBase:()=>base,commit:patch=>{commits.push({...patch});base={...base,...patch};return{ok:true};},
 schedule:fn=>{const id=++timerId;timers.set(id,fn);callbacks.push(fn);return id;},cancel:id=>timers.delete(id),onChange:e=>events.push(e)});
queue.stage('length',3);queue.stage('sleeve',2);
check('Rapid edits to different fields are coalesced without losing either value',queue.value('length')===3&&queue.value('sleeve')===2&&timers.size===1);
queue.flush();check('Saving can synchronously flush the complete pending specification',base.length===3&&base.sleeve===2&&commits.length===1&&!queue.pending&&timers.size===0);
callbacks[0]();check('An expired timer cannot commit a second transaction',commits.length===1);
queue.stage('length',4);const delayed=callbacks.at(-1);queue.discard('UNDO');queue.stage('length',5);delayed();
check('A discarded timer cannot flush a newer draft',queue.pending&&base.length===3&&commits.length===1);
queue.flush();check('The newest draft still commits normally',base.length===5&&commits.length===2);
queue.stage('length',6);queue.stage('length',5);queue.flush();
check('Returning a slider to its committed value creates no empty history entry',commits.length===2&&!queue.pending);
queue.stage('sleeve',3);queue.discard('REPLACE');
check('Replacing a project cancels pending specification intentions',!queue.pending&&timers.size===0&&base.sleeve===2);
assert.throws(()=>queue.stage('unknown',1));assert.throws(()=>queue.stage('length',NaN));
check('Invalid fields and nonfinite input do not mutate the draft',!queue.pending);
const rejected=new SpecDraft({getBase:()=>base,commit:()=>({ok:false,error:'invalid geometry'}),schedule:()=>0,cancel:()=>{}});
rejected.stage('length',7);check('Rejected geometry clears the pending draft instead of leaving misleading controls',!rejected.flush().ok&&!rejected.pending);
const throws=new SpecDraft({getBase:()=>base,commit:()=>{throw Error('failure');},schedule:()=>0,cancel:()=>{}});
throws.stage('length',7);check('Unexpected commit failure settles the draft and reports an error',!throws.flush().ok&&!throws.pending);
const result={status:'PASS',checks,count:checks.length,adversarialTransitions:5000,lifecycleStates:['IDLE','SOLVING','READY','ERROR','UNAVAILABLE']};
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2));console.log(JSON.stringify(result));
