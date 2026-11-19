import {createBodyCollider} from './body-contact.js';
import {createFaceAudit,faceData,faceNormal} from './intersections.js';
export const CONTACT_SLOTS=8;
export function createContactSystem(body,model,doc){
  const collider=createBodyCollider(body),n=model.nodeCount,hints=new Int32Array(n).fill(-1),result={point:[0,0,0],normal:[0,0,0],signedDistance:0,triangle:-1};
  const audit=createFaceAudit(body);
  // Seven floats per plane plus padding: normal.xyz, signed activation,
  // target.xyz, reserved. GPU projects against planes from the actual mesh BVH.
  function planes(p,clearance=.005,includeFaces=false){
    const out=new Float32Array(n*8*CONTACT_SLOTS),extra=Array.from({length:n},()=>[]);
    for(let i=0;i<n;i++){const at=i*4,r=collider.closestPointInto(p[at],p[at+1],p[at+2],hints[i],result);hints[i]=r.triangle;
      out.set([...r.normal,r.signedDistance<clearance+.012?1:0,...r.point.map((x,a)=>x+r.normal[a]*clearance),0],i*8*CONTACT_SLOTS);}
    const faces=includeFaces?faceData(p,model.triangles,4):null,bodyCross=includeFaces?audit.bodyPairs(faces):{pairs:[]};
    function add(ids,normal,point,margin){for(const i of ids){const d=[0,1,2].reduce((s,a)=>s+(p[i*4+a]-point[a])*normal[a],0);if(d<margin)extra[i].push({normal,point:point.map((x,a)=>x+normal[a]*margin),depth:margin-d});}}
    for(const [a,b]of bodyCross.pairs){const face=audit.bodyFaces[b];add(faces[a].ids,faceNormal(face.points),face.points[0],clearance);}

    for(let i=0;i<n;i++){const list=extra[i].sort((a,b)=>b.depth-a.depth).slice(0,CONTACT_SLOTS-1);list.forEach((plane,j)=>out.set([...plane.normal,1,...plane.point,0],(i*CONTACT_SLOTS+j+1)*8));}
    return out;
  }
  function inspect(p,full=false){
    let minimum=Infinity,penetratingVertices=0,contacts=0,queries=0,deepest=-1;const distances=new Float32Array(p.length/3),failures=[];
    for(let i=0;i<p.length/3;i++){const r=collider.closestPointInto(p[i*3],p[i*3+1],p[i*3+2],-1,result);queries++;distances[i]=r.signedDistance;
      if(r.signedDistance<minimum){minimum=r.signedDistance;deepest=i;}if(r.signedDistance<.006)contacts++;
      if(r.signedDistance<-.0001){penetratingVertices++;if(failures.length<30)failures.push({vertex:i,triangle:r.triangle,depthMm:-r.signedDistance*1000});}}
    let penetratingSamples=0,minSample=Infinity;
    if(full){const samples=[...doc.mesh.edges.map(e=>[e.a,e.b])];for(let f=0;f<doc.mesh.triangles.length;f+=3)samples.push(doc.mesh.triangles.slice(f,f+3));
      for(const ids of samples){const xyz=[0,1,2].map(a=>ids.reduce((s,i)=>s+p[i*3+a],0)/ids.length),r=collider.closestPointInto(...xyz,-1,result);queries++;minSample=Math.min(minSample,r.signedDistance);if(r.signedDistance<-.0001)penetratingSamples++;}}
    let bodyFacePairs=null,selfFacePairs=null;
    if(full){const merged=new Float32Array(model.nodeCount*4);for(let i=0;i<model.map.length;i++)for(let a=0;a<3;a++)merged[model.map[i]*4+a]=p[i*3+a];const faces=faceData(merged,model.triangles,4);bodyFacePairs=audit.bodyPairs(faces);selfFacePairs=audit.selfPairs(faces);}
    const crossingVertices=bodyFacePairs?new Set(bodyFacePairs.pairs.flatMap(([face])=>doc.mesh.triangles.slice(face*3,face*3+3))):new Set();
    return {minimumDistanceMm:minimum*1000,penetrationMm:Math.max(0,-minimum*1000),penetratingVertices,penetratingSamples,minSampleDistanceMm:Number.isFinite(minSample)?minSample*1000:null,contacts,queries,deepestVertex:deepest,distances,failures,bodyFacePairs,selfFacePairs,crossingVertices,method:'CPU exact triangle BVH + strict two-way face crossing tests. GPU projects vertex and intersecting-body-face planes. Cloth self-intersections are detected, not resolved. Discrete tests; coplanar overlap and CCD not implemented.'};
  }
  return {planes,inspect,collider};
}
