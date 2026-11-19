// Independent verifier. Does not import the product solver, collider or WASM math.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2],cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const vec=(p,i)=>[p[i*3],p[i*3+1],p[i*3+2]];
function stretchesQR(a,b){const x=Math.hypot(...a);if(x===0)return [Math.hypot(...b),0];const q=dot(a,b)/x,r=Math.hypot(...cross(a,b))/x,high=(Math.hypot(x+r,q)+Math.hypot(x-r,q))/2;return [high,high===0?0:x*r/high];}
function hit(a,b,t,ray=false){const d=sub(b,a),u=sub(t[1],t[0]),v=sub(t[2],t[0]),h=cross(d,v),den=dot(u,h);if(Math.abs(den)<1e-13)return null;const s=sub(a,t[0]),f=dot(s,h)/den,q=cross(s,u),g=dot(d,q)/den,k=dot(v,q)/den,e=1e-9;if(f>e&&g>e&&f+g<1-e&&k>e&&(ray||k<1-e))return k;return null;}
function crosses(a,b){for(let i=0;i<3;i++)if(hit(a[i],a[(i+1)%3],b)!==null||hit(b[i],b[(i+1)%3],a)!==null)return true;return false;}
function faces(p,indices){const out=[];for(let i=0;i<indices.length;i+=3){const ids=indices.slice(i,i+3),xyz=ids.map(i=>vec(p,i)),lo=[0,1,2].map(k=>Math.min(...xyz.map(p=>p[k]))),hi=[0,1,2].map(k=>Math.max(...xyz.map(p=>p[k])));out.push({ids,xyz,lo,hi});}return out;}
function overlaps(a,b){return a.lo[0]<=b.hi[0]+1e-10&&a.hi[0]>=b.lo[0]-1e-10&&a.lo[1]<=b.hi[1]+1e-10&&a.hi[1]>=b.lo[1]-1e-10&&a.lo[2]<=b.hi[2]+1e-10&&a.hi[2]>=b.lo[2]-1e-10;}
function crossingPairs(a,b,roots=null){let count=0,candidates=0;const examples=[];for(let i=0;i<a.length;i++)for(let j=roots?i+1:0;j<b.length;j++){
  if(!overlaps(a[i],b[j]))continue;if(roots&&a[i].ids.some(x=>b[j].ids.some(y=>roots[x]===roots[y])))continue;candidates++;
  if(crosses(a[i].xyz,b[j].xyz)){count++;if(examples.length<30)examples.push([i,j]);}
 }return {count,candidates,examples};}
function insideCount(p,bodyFaces){let inside=0;const d=[1,.231764,.417398];for(let i=0;i<p.length;i+=3){const a=p.slice(i,i+3),b=a.map((x,k)=>x+d[k]),times=[];for(const f of bodyFaces){const at=hit(a,b,f.xyz,true);if(at!==null)times.push(at);}times.sort((a,b)=>a-b);let count=0,last=-Infinity;for(const t of times)if(t-last>1e-8){count++;last=t;}if(count%2)inside++;}return inside;}
export function verifyGeometrySnapshot(snapshot,runtime,label='case'){
  const d=snapshot.project.document,p=snapshot.positions,body=snapshot.project.body,tri=d.mesh.triangles,uv=d.mesh.restUV,errors=[],checks=[];
  const check=(name,value,detail=null)=>{checks.push({name,status:value?'PASS':'FAIL',detail});if(!value)errors.push(name);};
  const triangle=[[0,0,0],[1,0,0],[0,1,0]];
  assert.notEqual(hit([.2,.2,-1],[.2,.2,1],triangle),null);assert.equal(hit([2,2,-1],[2,2,1],triangle),null);
  assert.ok(Math.abs(stretchesQR([1,0,0],[0,1e-9,0])[1]-1e-9)<1e-20);
  const values=[];
  for(let f=0;f<tri.length;f+=3){const [i,j,k]=tri.slice(f,f+3),x0=(uv[j][0]-uv[i][0])/1000,y0=(uv[j][1]-uv[i][1])/1000,x1=(uv[k][0]-uv[i][0])/1000,y1=(uv[k][1]-uv[i][1])/1000,det=x0*y1-x1*y0,e1=sub(vec(p,j),vec(p,i)),e2=sub(vec(p,k),vec(p,i));assert.ok(Math.abs(det)>1e-14);
    const a=e1.map((v,n)=>(v*y1-e2[n]*y0)/det),b=e1.map((v,n)=>(e2[n]*x0-v*x1)/det),s=stretchesQR(a,b);values.push(Math.max(Math.abs(s[0]-1),Math.abs(s[1]-1)));
  }
  values.sort((a,b)=>a-b);const q=.95*(values.length-1),index=Math.floor(q),p95=values[index]+(values[Math.min(index+1,values.length-1)]-values[index])*(q-index),max=values.at(-1);
  check('finite coordinates',p.every(Number.isFinite));check('independent QR principal strain p95 <= 10%',p95<=.1,p95);check('independent QR max principal strain <= 25%',max<=.25,max);
  check('WASM diagnostics agree with independent QR',Math.abs(p95-runtime.metrics.strainP95)<1e-8&&Math.abs(max-runtime.metrics.strainMax)<1e-8);
  const parent=Int32Array.from({length:p.length/3},(_,i)=>i),find=i=>parent[i]===i?i:parent[i]=find(parent[i]);let gap=0;
  for(const seam of d.seams)for(const [a,b]of seam.pairs){parent[find(b)]=find(a);gap=Math.max(gap,Math.hypot(...sub(vec(p,a),vec(p,b)))*1000);}
  check('independent seam gap <= 2 mm',gap<=2,gap);const roots=Array.from(parent,(_,i)=>find(i)),cloth=faces(p,tri),human=faces(body.positions,body.triangles);
  const bodyPairs=crossingPairs(cloth,human),selfPairs=crossingPairs(cloth,cloth,roots),inside=insideCount(p,human);
  check('independent closed-body ray parity: zero internal vertices',inside===0,inside);check('independent complete body face crossing count = 0',bodyPairs.count===0,bodyPairs);check('independent nonadjacent self crossing count = 0',selfPairs.count===0,selfPairs);
  return {label,status:errors.length?'FAIL':'PASS',checks,principalStrain:{p95,max},seamGapMm:gap,bodyFaceCrossings:bodyPairs.count,selfFaceCrossings:selfPairs.count,insideBodyVertices:inside,method:'Independent JavaScript QR-based singular values, closed-mesh ray parity, exhaustive AABB-filtered strict two-way triangle crossings.',limits:'Discrete saved frames only; coplanar overlap, CCD, material calibration and real-person fit are outside these automated assertions.'};
}
export function verifySavedGeometry(root){const report=JSON.parse(fs.readFileSync(path.join(root,'evidence/browser-report-js.json'))),results=[];
  for(const [label,file,key]of [['baseline','gpu-snapshot-js.json','settled'],['wide','gpu-snapshot-wide-js.json','wideSettled']]){
    const filePath=path.join(root,'evidence',file),snapshot=JSON.parse(fs.readFileSync(filePath));const r=verifyGeometrySnapshot(snapshot,report[key],label);r.snapshotSha256=createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');results.push(r);
  }
  const out={status:results.every(r=>r.status==='PASS')?'PASS':'FAIL',results};fs.writeFileSync(path.join(root,'evidence/independent-report-js.json'),JSON.stringify(out,null,2));return out;
}
