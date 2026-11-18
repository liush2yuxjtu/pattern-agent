import {auditSleeveQuality} from './sleeve-quality.mjs';
import {BodyCollider} from './body-collider.mjs';
const sub=(a,b)=>a.map((v,k)=>v-b[k]),dot=(a,b)=>a.reduce((s,v,k)=>s+v*b[k],0),unit=a=>{const l=Math.hypot(...a);return a.map(v=>v/l);},cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
export function packPanels(meshes){return meshes.map(m=>{const d=m.userData;return{partId:d.partId,sourceId:d.sourceId,vertices:d.assembled.map(v=>v.toArray()),points2d:d.points2d,triangles:d.triangles,boundary:d.fitBoundary,triangleCount:d.triangles.length};});}
export function fitSignature(pattern,angle,revision){return JSON.stringify({schema:4,revision,chest:pattern.measurements.chest,angle,parts:Object.fromEntries(['front','back','sleeve'].map(k=>[k,{points:pattern.parts[k].points,seamOps:pattern.parts[k].seamOps}]))});}
function edges(panels,i,role,sign=0){const p=panels[i];return p.boundary.filter(e=>e.edge===role&&(!sign||(p.points2d[e.a].x+p.points2d[e.b].x)*sign>0)).map(e=>[p.vertices[e.a],p.vertices[e.b]]);}
function pairGap(a,b){const directed=(source,target)=>{let max=0;for(const edge of source)for(const t of[0,.125,.25,.375,.5,.625,.75,.875,1]){const p=edge[0].map((v,k)=>v*(1-t)+edge[1][k]*t);let min=Infinity;for(const[x,y]of target){const d=sub(y,x),r=sub(p,x),u=Math.max(0,Math.min(1,dot(r,d)/(dot(d,d)||1)));min=Math.min(min,Math.hypot(...p.map((v,k)=>v-x[k]-u*d[k])));}max=Math.max(max,min);}return max;};return Math.max(directed(a,b),directed(b,a))*1000;}
function insideProjected(segments,origin,u,v){let count=0;for(const[a,b]of segments){const p=sub(a,origin),q=sub(b,origin),x=dot(p,u),y=dot(p,v),xx=dot(q,u),yy=dot(q,v);if((y>0)!==(yy>0)&&x+(xx-x)*(-y)/(yy-y)>0)count++;}return count%2===1;}
export function auditWear(panels,body,{solver=null,collider=null,pattern=null}={}){
 collider ||=new BodyCollider(body.vertices,body.triangles);let min=Infinity,inside=0,faceIntersections=0,samples=0;const parts=[];
 for(const p of panels){let partInside=0,partIntersections=0;for(const v of p.vertices){const h=collider.closest(v);min=Math.min(min,h.signed);if(h.signed<-.0000001)partInside++;samples++;}
  for(const t of p.triangles){const tri=t.map(i=>p.vertices[i]);if(collider.intersections(tri).length)partIntersections++;for(const weights of[[1/3,1/3,1/3],[.5,.5,0],[0,.5,.5],[.5,0,.5]]){const pos=[0,1,2].map(k=>tri.reduce((s,v,j)=>s+v[k]*weights[j],0));const h=collider.closest(pos);min=Math.min(min,h.signed);if(h.signed<-.0000001)partInside++;samples++;}}
  inside+=partInside;faceIntersections+=partIntersections;parts.push({part:p.partId,insideSamples:partInside,intersectingTriangles:partIntersections});
 }
 const seams={shoulder:pairGap(edges(panels,0,'shoulder'),edges(panels,1,'shoulder')),side:pairGap(edges(panels,0,'side'),edges(panels,1,'side'))};
 for(const[i,sign]of[[2,1],[3,-1]]){seams[panels[i].partId+'-underarm']=pairGap(edges(panels,i,'underarm-right'),edges(panels,i,'underarm-left'));seams[panels[i].partId+'-cap']=pairGap(edges(panels,i,'cap'),[...edges(panels,0,'armhole',sign),...edges(panels,1,'armhole',sign)]);}
 const j=body.joints,openings={neck:insideProjected([...edges(panels,0,'neck'),...edges(panels,1,'neck')],j.neck,[1,0,0],[0,0,1]),hem:insideProjected([...edges(panels,0,'hem'),...edges(panels,1,'hem')],[0,0,-.04],[1,0,0],[0,0,1])};
 for(const[i,side]of[[2,'l'],[3,'r']]){const S=j[side+'-shoulder'],E=j[side+'-elbow'],axis=unit(sub(E,S)),u=unit(cross(axis,[0,0,1])),v=cross(axis,u);openings[panels[i].partId]=insideProjected(edges(panels,i,'hem'),S,u,v);}
 const clothVertices=panels.flatMap(p=>p.vertices),clothFaces=[];let off=0;for(const p of panels){clothFaces.push(...p.triangles.map(t=>t.map(i=>i+off)));off+=p.vertices.length;}const clothCollider=new BodyCollider(clothVertices,clothFaces);let torso=0;
 for(let d=0;d<360;d+=10){const rad=d*Math.PI/180,dir=[Math.cos(rad),0,Math.sin(rad)],p=[0,body.waistY,-.04],a=collider.ray(p,dir),b=clothCollider.ray(p,dir);if(a.length&&b.length&&b[0]>a[0]+.0005)torso++;}
 const sleeveQuality=pattern?auditSleeveQuality(panels,pattern):null;
 const seamMaxMm=Math.max(...Object.values(seams)),pass=inside===0&&faceIntersections===0&&min>=-1e-7&&seamMaxMm<=1&&torso===36&&Object.values(openings).every(Boolean)&&(!sleeveQuality||sleeveQuality.status==='PASS');
 return{schema:'static-geometric-wear/2',status:pass?'PASS':'FAIL',scopeZh:'演示人体静态几何穿着',insideSamples:inside,sampleCount:samples,intersectingTriangles:faceIntersections,minimumSampleClearanceMm:min*1000,seamMaxMm,seamGapsMm:seams,openings,torsoDirections:torso,torsoDirectionCount:36,parts,solver,sleeveQuality,bodyCollision:'RUN',materialPhysics:'NOT_CALIBRATED',personalFit:'NOT_VALIDATED',tolerances:{seamGapMm:1,intersectionM:1e-9},checkedAt:new Date().toISOString()};
}
