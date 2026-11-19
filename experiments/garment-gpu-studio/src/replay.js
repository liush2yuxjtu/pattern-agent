export class Replay {
  constructor(limit=240){this.limit=limit;this.reset('');}
  reset(version){this.version=version;this.frames=[];this.cursor=0;this.events=[];}
  record(p,step,dt,metrics){const frame={id:step,version:this.version,time:step*dt,positions:new Float32Array(p),metrics:structuredClone(metrics)};this.frames.push(frame);if(this.frames.length>this.limit)this.frames.splice(1,1);this.cursor=this.frames.length-1;if(metrics.penetratingVertices>0||metrics.seamGapMm>2||metrics.strainMax>.25||metrics.bodyFaceCrossings>0||metrics.selfFaceCrossings>0)this.events.push({id:step,time:frame.time,penetration:metrics.penetratingVertices,bodyCrossings:metrics.bodyFaceCrossings,selfCrossings:metrics.selfFaceCrossings,strain:metrics.strainMax});return frame;}
  seek(index,version){if(version!==this.version)throw new Error('STALE replay');if(!this.frames.length)throw new Error('No recorded frames');this.cursor=Math.max(0,Math.min(this.frames.length-1,Math.round(index)));return this.frames[this.cursor];}
  json(){return {version:this.version,frames:this.frames.map(f=>({...f,positions:Array.from(f.positions)})),events:this.events};}
}
