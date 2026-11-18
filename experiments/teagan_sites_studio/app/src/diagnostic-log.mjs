export class DiagnosticLog {
  constructor(label='pattern-crease') { this.label=label;this.entries=[];this.sequence=0; }
  record(stage,detail={},durationMs=0,start=performance.now()) {
    const event={sequence:++this.sequence,stage,timeMs:start,durationMs,detail};
    this.entries.push(event);if(this.entries.length>400)this.entries.shift();
    return event;
  }
  measure(stage,run,detail={}) {
    const id=this.label+':'+stage+':'+(this.sequence+1),start=performance.now();
    performance.mark(id+':start');
    try {const result=run();this.record(stage,typeof detail==='function'?detail(result):detail,performance.now()-start,start);return result;}
    finally {performance.mark(id+':end');performance.measure(id,id+':start',id+':end');performance.clearMarks(id+':start');performance.clearMarks(id+':end');}
  }
  export() {
    return {schema:'pattern-diagnostic-log/1',timeOriginMs:performance.timeOrigin,events:structuredClone(this.entries),
      traceEvents:this.entries.map(e=>({name:e.stage,cat:this.label,pid:1,tid:1,ts:e.timeMs*1000,args:e.detail,...(e.durationMs>0?{ph:'X',dur:e.durationMs*1000}:{ph:'i',s:'t'})})),
      noteZh:'耗时描述本次检测或求解；折角才是几何异常依据。旧网格重放不冒充原始求解器逐帧记录。'};
  }
}
