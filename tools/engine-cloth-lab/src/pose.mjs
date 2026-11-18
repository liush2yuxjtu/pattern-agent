// This initial assembly is a declared demonstration assumption, not a fit result.
import {MeshBodyCollider} from '../reference/src/mesh-collider.js';
export function assemble(mesh,draft,body,profile='planar-gentle'){
  const output=new Float32Array(mesh.restXY.length*3), shoulderY=body.landmarks.shoulderY+0.035;
  const panels=Object.fromEntries(draft.panels.map(p=>[p.id,p]));
  for(let i=0;i<mesh.restXY.length;i++){
    const [u,v]=mesh.restXY[i], id=mesh.panelOfVertex[i];let x,y,z;
    if(id==='front'||id==='back'){
      const panel=panels[id],side=panel.pathLabels['right.side'].samplesMM,half=side.reduce((best,p)=>Math.abs(p[1]-v)<Math.abs(best[1]-v)?p:best,side[0])[0];
      const angle=Math.max(-1,Math.min(1,u/half))*Math.PI/2;
      x=.183*Math.sin(angle); y=shoulderY-v*.001;
      const r=.137*Math.max(.32,Math.min(1,v/160));
      z=.035+(id==='front'?1:-1)*r*Math.cos(angle)+(id==='front'?.006:-.006);
    }else{
      const sign=id.endsWith('left')?-1:1;
      const panel=panels[id],w=Math.max(...panel.outlineMM.map(p=>Math.abs(p[0]))),capY=Math.min(...panel.outlineMM.map(p=>p[1]));
      const theta=Math.PI*u/w,axisDistance=(v-capY)*.001;
      const radius=.058;
      // Shoulder -> upper arm axis in this MakeHuman A-pose. Both sleeves use their original local UVs.
      x=sign*(.162+axisDistance*.73+radius*Math.cos(theta)*.68);
      y=1.365-axisDistance*.68+radius*Math.cos(theta)*.73;
      z=.018+radius*Math.sin(theta)*(id.endsWith('left')?1:-1);
    }
    output.set([x,y,z],i*3);
  }
  const pins=[];
  for(const panel of mesh.panels.filter(p=>['front','back'].includes(p.id)))for(const side of ['left','right']){
    const ids=panel.pathLabels?.[`${side}.shoulder`]?.vertexIds;
    if(ids?.length)pins.push(ids[Math.floor(ids.length*.7)]);
  }
  for(const i of pins)output[i*3+2]=.035;
  if(profile==='planar-gentle'){
    const collider=new MeshBodyCollider(body);
    for(let i=0;i<mesh.restXY.length;i++){
      const [u,v]=mesh.restXY[i],id=mesh.panelOfVertex[i];let p;
      if(id==='front'||id==='back')p=[u*.001,1.5-v*.001,id==='front'?.23:-.2];
      else{const sign=id.endsWith('left')?-1:1;p=[sign*(.48+v*.00073)+u*.00068,1.4-v*.00068+sign*u*.00073,.23];}
      output.set(collider.project(...p,.03),i*3);
    }
    return {positions:output,pins:[...new Set(pins.filter(i=>mesh.panelOfVertex[i]==='front'))],config:{dt:1/120,particleRadius:.005,edgeFrequency:60,bendFrequency:2,additionalSolverIterations:0,additionalPgsIterations:2,solverIterations:4,maxExtraSubsteps:0,seamMode:'spring',seamStiffness:.01,seamDamping:.0035},provenance:{status:'DEMO_ASSUMED',method:'Planar panels outside body, one-time 30mm initial clearance projection, two front shoulder supports, gentle native zero-rest spring joints.',sewing:'OPEN / NOT_VALIDATED',preprocessingOnly:true,bodyIdentity:body.name,materialRest:'Unchanged panel-local millimetres'}};
  }
  return {positions:output,pins:[...new Set(pins)],provenance:{status:'DEMO_ASSUMED',method:'Elliptic torso and cylindrical upper-arm initial assembly; four visible shoulder supports at matching front/back shoulder locations.',bodyIdentity:body.name,materialRest:'Unchanged panel-local millimetres'}};
}
