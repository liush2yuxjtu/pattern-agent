// The fit job owns its worker. Display modes and view visibility never start jobs.
export class FitLifecycle {
  constructor({onTransition=()=>{},now=()=>performance.now()}={}) {
    this.onTransition=onTransition;this.now=now;this.generation=0;this.job=null;this.worker=null;
    this.state={phase:'IDLE',status:'PENDING'};this.source={cached:false};this.trace=[];
  }
  record(event,from,detail={}) {
    const item={event,from,to:this.state.phase,generation:this.generation,documentRevision:this.job?.revision??null,timeMs:this.now(),...detail};
    this.trace.push(item);if(this.trace.length>120)this.trace.shift();this.onTransition({...item});
  }
  stopWorker() {
    const worker=this.worker;this.worker=null;
    if(worker){worker.onmessage=null;worker.onerror=null;worker.terminate();}
  }
  begin({revision,diagnostics=false}={}) {
    const from=this.state.phase;this.stopWorker();
    this.job=Object.freeze({generation:++this.generation,revision,diagnostics});
    this.state={phase:'SOLVING',status:'SOLVING',generation:this.generation,documentRevision:revision};this.source={cached:false};
    this.record('BEGIN',from,{diagnostics});return this.job;
  }
  isCurrent(job){return job===this.job&&this.state.phase==='SOLVING';}
  stale(job,event){this.record('STALE_IGNORED',this.state.phase,{ignoredGeneration:job?.generation,ignoredEvent:event});return false;}
  setSource(job,source){if(!this.isCurrent(job))return this.stale(job,'SOURCE');this.source={...source};return true;}
  attach(job,worker){if(!this.isCurrent(job)){worker.terminate();return false;}if(this.worker!==worker)this.stopWorker();this.worker=worker;return true;}
  progress(job,progress){if(!this.isCurrent(job))return this.stale(job,'PROGRESS');this.state.progress={...progress};return true;}
  complete(job,report) {
    if(!this.isCurrent(job))return this.stale(job,'COMPLETE');
    if(!report||!['PASS','FAIL'].includes(report.status))throw Error('求解报告状态无效');
    const from=this.state.phase;this.stopWorker();this.state={phase:'READY',status:report.status,report,generation:job.generation,documentRevision:job.revision};
    this.record('COMPLETE',from,{status:report.status,cached:this.source.cached});return true;
  }
  fail(job,message){return this.terminal(job,'ERROR','FAIL',message);}
  unavailable(job,message){return this.terminal(job,'UNAVAILABLE','UNAVAILABLE',message);}
  terminal(job,phase,status,message) {
    if(!this.isCurrent(job))return this.stale(job,phase);
    const from=this.state.phase;this.stopWorker();this.state={phase,status,message,generation:job.generation,documentRevision:job.revision};
    this.record(phase,from,{message});return true;
  }
  get ready(){return this.state.phase==='READY';}
  snapshot(){return structuredClone({phase:this.state.phase,status:this.state.status,generation:this.generation,documentRevision:this.job?.revision??null,
    diagnostics:this.state.phase==='SOLVING'&&!!this.job?.diagnostics,cached:!!this.source.cached,workerActive:!!this.worker,
    progress:this.state.progress?{...this.state.progress}:null,trace:this.trace.map(e=>({...e}))});}
}

// Coalesce fields, not events: changing a second slider cannot discard the first.
export class SpecDraft {
  constructor({getBase,commit,onChange=()=>{},delay=160,schedule=(fn,ms)=>globalThis.setTimeout(fn,ms),cancel=id=>globalThis.clearTimeout(id)}) {
    Object.assign(this,{getBase,commit,onChange,delay,schedule,cancel});this.patch={};this.timer=null;this.revision=0;
  }
  get pending(){return Object.keys(this.patch).length>0;}
  value(field){return Object.hasOwn(this.patch,field)?this.patch[field]:this.getBase()[field];}
  stage(field,value) {
    if(!Object.hasOwn(this.getBase(),field)||!Number.isFinite(value))throw Error('尺寸数值无效');
    if(Object.is(value,this.getBase()[field]))delete this.patch[field];else this.patch[field]=value;
    this.revision++;this.clearTimer();const revision=this.revision;
    if(this.pending)this.timer=this.schedule(()=>{if(revision===this.revision)this.flush();},this.delay);
    this.onChange('PENDING');
  }
  clearTimer(){if(this.timer!==null)this.cancel(this.timer);this.timer=null;}
  flush() {
    this.clearTimer();if(!this.pending)return{ok:true,changed:false};
    const patch={...this.patch};this.patch={};this.revision++;
    let result;try{result=this.commit(patch);}catch(e){result={ok:false,error:e.message};}
    this.onChange(result.ok?'COMMITTED':'REJECTED');return result;
  }
  discard(reason='REPLACED') {
    this.clearTimer();if(!this.pending)return false;this.patch={};this.revision++;this.onChange(reason);return true;
  }
  snapshot(){return{pending:this.pending,fields:{...this.patch},revision:this.revision};}
}
