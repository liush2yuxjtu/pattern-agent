import {inspectCreases,summarizeCreaseEdges} from './crease-diagnostics.mjs';
const sub=(a,b)=>a.map((v,i)=>v-b[i]);
const add=(a,b)=>a.map((v,i)=>v+b[i]);
const scale=(a,s)=>a.map(v=>v*s);
const dot=(a,b)=>a.reduce((n,v,i)=>n+v*b[i],0);
const norm=a=>Math.hypot(...a);
const unit=a=>{const l=norm(a);return l>1e-12?scale(a,1/l):null;};
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const closest=(p,a,b)=>{const d=sub(b,a),t=Math.max(0,Math.min(1,dot(sub(p,a),d)/(dot(d,d)||1)));return add(a,scale(d,t));};

// UV winding may differ between panels. Orient the paired boundary directions
// oppositely, then compare their actual geometric face normals. No abs(normal dot).
// Boundary correspondence is geometric and its gap is explicitly checked.
export function inspectGarmentCreases(panels,options={}){
  const result=inspectCreases(panels,{...options,includeBody:true}),samples=[],unmatched=[];
  const boundaries=new Map();
  for(const panel of panels){
    const id=panel.partId||panel.part,adj=new Map();
    panel.triangles.forEach((t,face)=>{for(let k=0;k<3;k++){const a=t[k],b=t[(k+1)%3],key=[a,b].sort((a,b)=>a-b).join(':');if(!adj.has(key))adj.set(key,[]);adj.get(key).push({face,opposite:t[(k+2)%3]});}});
    boundaries.set(id,(panel.boundary||[]).map(e=>{const neighbors=adj.get([e.a,e.b].sort((a,b)=>a-b).join(':'))||[];return{...e,panel,partId:id,a3:panel.vertices[e.a],b3:panel.vertices[e.b],neighbor:neighbors.length===1?neighbors[0]:null};}));
  }
  const edges=(id,role,sign=0)=>(boundaries.get(id)||[]).filter(e=>e.edge===role&&(!sign||(e.panel.points2d[e.a].x+e.panel.points2d[e.b].x)*sign>0));
  const pairs=[['shoulder',edges('front','shoulder'),edges('back','shoulder')],['side',edges('front','side'),edges('back','side')]];
  for(const [id,sign]of[['sleeve-right',1],['sleeve-left',-1]]){
    pairs.push([id+'-cap',edges(id,'cap'),[...edges('front','armhole',sign),...edges('back','armhole',sign)]]);
    pairs.push([id+'-underarm',edges(id,'underarm-right'),edges(id,'underarm-left')]);
  }
  for(const [seamId,left,right]of pairs){
    // Sample each boundary segment from each side, avoiding endpoint ambiguity.
    for(const [sources,targets,direction]of[[left,right,'a'],[right,left,'b']])for(const source of sources){
      const midpoint=scale(add(source.a3,source.b3),.5),axis=unit(sub(source.b3,source.a3));let target=null,point=null,gap=Infinity;
      for(const candidate of targets){const q=closest(midpoint,candidate.a3,candidate.b3),d=norm(sub(q,midpoint));if(d<gap){target=candidate;point=q;gap=d;}}
      const id=`seam:${seamId}:${direction}:${source.partId}:${source.a}:${source.b}`;
      if(!target||!axis||!source.neighbor||!target.neighbor||gap>.001){unmatched.push({id,seamId,gapMm:Number.isFinite(gap)?gap*1000:null,reason:'missing-face-or-seam-gap-over-1mm'});continue;}
      let targetAxis=unit(sub(target.b3,target.a3));
      if(!targetAxis){unmatched.push({id,seamId,gapMm:gap*1000,reason:'degenerate-target-edge'});continue;}
      if(dot(axis,targetAxis)>0)targetAxis=scale(targetAxis,-1);
      const normals=[unit(cross(axis,sub(source.panel.vertices[source.neighbor.opposite],source.a3))),unit(cross(targetAxis,sub(target.panel.vertices[target.neighbor.opposite],target.a3)))];
      if(normals.some(n=>!n)){unmatched.push({id,seamId,gapMm:gap*1000,reason:'degenerate-face-normal'});continue;}
      const angleDeg=Math.atan2(norm(cross(normals[0],normals[1])),dot(normals[0],normals[1]))*180/Math.PI;
      samples.push({id,seamId,kind:'seam',partId:source.partId,a:source.a,b:source.b,faces:[source.neighbor.face],
        counterpart:{partId:target.partId,face:target.neighbor.face,a:target.a,b:target.b},angleDeg,excluded:false,
        classification:angleDeg>45?'sharp':angleDeg>25?'warning':'smooth',midpoint,gapMm:gap*1000,
        normals,tangentMismatchDeg:Math.acos(Math.max(-1,Math.min(1,-dot(axis,targetAxis))))*180/Math.PI,
        faceCenters:[source,target].map(e=>scale(e.panel.triangles[e.neighbor.face].map(i=>e.panel.vertices[i]).reduce(add,[0,0,0]),1/3)),
        edgeLengthMm:norm(sub(source.a3,source.b3))*1000});
    }
  }
  const internal=result.parts.flatMap(p=>p.edges);
  return{...result,schema:'garment-crease-diagnostic/1',measurementStatus:result.invalidCount?'INVALID':'MEASURED',statusScope:'sleeve-internal-quality-only',
    sleeveVerdict:{status:result.status,scopeZh:result.verdictScopeZh,peak:result.peak,sharpCount:result.sharpCount},
    coverage:'full-garment-interior-and-paired-seam-samples',
    seamMethod:'geometric face normals; paired boundary directions aligned oppositely; atan2(norm(cross),dot), never abs(normal dot); symmetric midpoint pairing; gap <=1 mm',
    seams:{samples,unmatched,missingGroups:pairs.filter(([,a,b])=>!a.length||!b.length).map(([id])=>id),summary:summarizeCreaseEdges(samples)},full:summarizeCreaseEdges([...internal,...samples]),
    openBoundaries:[...boundaries.values()].flat().filter(e=>['neck','hem'].includes(e.edge)).map(e=>({partId:e.partId,a:e.a,b:e.b,edge:e.edge})),
    coverageNoteZh:'前后片、左右袖片全部内边，以及肩缝、侧缝、袖山与袖底拼缝的双向中点采样。领口、衣摆、袖口是开口边，没有第二个面，折角不适用。'};
}
