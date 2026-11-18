import assert from 'node:assert/strict';
import {createSimulation} from '../../../web/cloth-lab/src/simulation.js';
import {createReplay} from '../../../web/cloth-lab/src/replay.js';
import {createPersistence} from '../../../web/cloth-lab/src/persistence.js';
let accesses=0,checked=0;
for(const availability of [{renderBlocked:true,renderPending:false},{renderBlocked:false,renderPending:true}]){
 const S={...availability,renderError:'guard probe',wasm:new Proxy({},{get(){accesses++;throw Error('Unexpected WASM access');}}),parameters:{marker:'unchanged'},track:{frames:[],cursor:-1,atRecordedState:false}};
 const initial=JSON.stringify(S.parameters),track=S.track;
 const simulation=createSimulation(S,{}),replay=createReplay(S,{}),persistence=createPersistence(S,{});
 for(const operation of [()=>simulation.setupCloth(),()=>simulation.takeSteps(1),()=>simulation.advance(1),()=>simulation.setRunning(true),()=>replay.startRecording(),()=>replay.applyFrame({}),()=>replay.seekFrame(0),()=>replay.playReplay(),()=>persistence.restore({}),()=>persistence.importReplay({})]){
  let failed=false;
  try{await operation();}catch(error){assert.match(error.message,/Renderer (?:is blocked|backend is switching)/);failed=true;}
  assert(failed,'guard must reject');checked++;
  assert.equal(JSON.stringify(S.parameters),initial);
  assert.equal(S.track,track);
 }
}
assert.equal(accesses,0);
console.log(JSON.stringify({guardedOperations:checked,wasmAccesses:accesses,stateUnchanged:true},null,2));
