// Bounded Float32 trajectory storage. Playback restores data; it never integrates.
export const MAX_FRAMES = 1201;
export const VERTICES = 850;
export const STATE_FLOATS = VERTICES * 10;
const BYTES = STATE_FLOATS * 4;
const SCHEMA = 'pattern-agent.cloth-trajectory.v1';

export function validateParameters(p) {
  if (!p || ![550,575,600,625,650,675,700,725,750,775,800].includes(p.bottomMm) ||
      p.topMm !== 420 || !Array.isArray(p.lengthsMm) || p.lengthsMm.length !== 2 ||
      !Number.isInteger(p.lengthsMm[0]) || p.lengthsMm[0] < 400 || p.lengthsMm[0] > 700 || p.lengthsMm[0] % 25 ||
      !['good','mismatch','open','reverse'].includes(p.fault) ||
      p.lengthsMm[1] !== p.lengthsMm[0] + (p.fault === 'mismatch' ? 40 : 0) ||
      !['woven','soft'].includes(p.material) || !Number.isInteger(p.bodyOffsetMm) ||
      Math.abs(p.bodyOffsetMm) > 60 || p.bodyOffsetMm % 10 ||
      typeof p.collision !== 'boolean' || typeof p.wind !== 'boolean') throw new Error('Invalid recording parameters');
  return {...p, lengthsMm:[...p.lengthsMm]};
}

export function topologyKey(p) {
  return JSON.stringify([p.bottomMm,p.topMm,p.lengthsMm,p.fault,p.material]);
}

export function encodeTrajectory(track, fingerprint) {
  return {schema:SCHEMA, fingerprint, fps:120, maxFrames:MAX_FRAMES,
    stateLayout:['positions:2550','previous:2550','pins:2550','contacts:850'],
    cursor:track.cursor, atRecordedState:track.atRecordedState,
    frames:track.frames.map(({state,...meta}) => {
      const bytes=new Uint8Array(state.buffer,state.byteOffset,state.byteLength);
      let binary='';
      for(let i=0;i<bytes.length;i+=8192) binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
      return {...meta,state:btoa(binary)};
    })};
}

export function decodeTrajectory(data, fingerprint, parameters) {
  if (!data || data.schema!==SCHEMA || data.fingerprint!==fingerprint || data.fps!==120 ||
      !Array.isArray(data.frames) || data.frames.length>MAX_FRAMES || !Number.isInteger(data.cursor) ||
      data.cursor < (data.frames.length ? 0 : -1) || data.cursor>=data.frames.length ||
      typeof data.atRecordedState!=='boolean') throw new Error('Incompatible or oversized trajectory');
  const key=topologyKey(parameters);
  let priorFrame=-1,priorTime=-1;
  const frames=data.frames.map(f=>{
    const p=validateParameters(f.parameters);
    if(topologyKey(p)!==key || !Number.isInteger(f.frame) || f.frame<priorFrame || f.frame>1e7 ||
       !Number.isFinite(f.time) || f.time<0 || f.time<priorTime || f.time>1e6 ||
       !Number.isFinite(f.stepMs) || f.stepMs<0 ||
       !['start','step','settings','injection'].includes(f.kind) ||
       typeof f.state!=='string' || f.state.length!==4*Math.ceil(BYTES/3) ||
       !/^[A-Za-z0-9+/]+={0,2}$/.test(f.state)) throw new Error('Invalid trajectory frame');
    const raw=atob(f.state);
    if(raw.length!==BYTES) throw new Error('Invalid trajectory buffer length');
    const state=new Float32Array(Uint8Array.from(raw,c=>c.charCodeAt(0)).buffer);
    if(!state.every((v,i)=>Number.isFinite(v)&&(i<VERTICES*9 ? Math.abs(v)<10 : v===0||v===1))) throw new Error('Invalid trajectory state');
    priorFrame=f.frame;priorTime=f.time;
    return {frame:f.frame,time:f.time,stepMs:f.stepMs,kind:f.kind,parameters:p,state};
  });
  return {frames,cursor:data.cursor,atRecordedState:data.atRecordedState};
}
