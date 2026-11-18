import {create} from '../probes/rapier/engine.mjs';
import {human} from './pipeline.mjs';
let engine,mesh,revision,step=0,busy=false;
onmessage=async({data})=>{
  try{
    if(data.type==='init'){
      engine?.dispose();mesh=data.mesh;revision=data.revision;step=0;
      const t=performance.now();
      engine=await create({restXY:mesh.restXY,triangles:mesh.triangles,initialXYZ:data.positions,pinnedIDs:data.pins,seams:mesh.seams,body:human,...data.config});
      postMessage({type:'ready',revision,initMS:performance.now()-t,stats:engine.nativeStats()});
    }
    if(data.type==='step'&&engine&&!busy){
      busy=true;let totalMS=0;
      for(let i=0;i<data.steps;i++){
        const t=performance.now();engine.step();totalMS+=performance.now()-t;step++;
        if(i===0||step%10===0||i===data.steps-1){
          postMessage({type:'frame',revision,step,positions:Array.from(engine.getPositions()),solverMS:totalMS,final:i===data.steps-1,stats:i===data.steps-1?engine.nativeStats():null});
          await new Promise(r=>setTimeout(r,0));
        }
      }
      busy=false;
    }
  }catch(error){busy=false;postMessage({type:'error',revision,message:error.stack??String(error)});}
};
