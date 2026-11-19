const sub=(a,b)=>a.map((x,i)=>x-b[i]),dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2],cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
export function segmentTriangle(a,b,t){const d=sub(b,a),e1=sub(t[1],t[0]),e2=sub(t[2],t[0]),h=cross(d,e2),det=dot(e1,h);if(Math.abs(det)<1e-13)return false;const s=sub(a,t[0]),u=dot(s,h)/det,q=cross(s,e1),v=dot(d,q)/det,at=dot(e2,q)/det,e=1e-9;return u>e&&v>e&&u+v<1-e&&at>e&&at<1-e;}
export function triangleCross(a,b){for(let i=0;i<3;i++)if(segmentTriangle(a[i],a[(i+1)%3],b)||segmentTriangle(b[i],b[(i+1)%3],a))return true;return false;}
export function faceData(p,triangles,stride=3){const faces=[];for(let f=0;f<triangles.length;f+=3){const ids=triangles.slice(f,f+3),points=ids.map(i=>Array.from(p.slice(i*stride,i*stride+3))),min=[0,1,2].map(a=>Math.min(...points.map(x=>x[a]))),max=[0,1,2].map(a=>Math.max(...points.map(x=>x[a])));faces.push({ids,points,min,max});}return faces;}
const overlaps=(a,b)=>[0,1,2].every(k=>a.min[k]<=b.max[k]+1e-10&&a.max[k]>=b.min[k]-1e-10);
export function createFaceAudit(body){const bodyFaces=faceData(body.positions,body.triangles),nodes=body.collision.bvh.nodes,order=body.collision.bvh.triangleOrder;
 function bodyPairs(faces){const pairs=[];let candidates=0;for(let f=0;f<faces.length;f++){const a=faces[f],stack=[0];while(stack.length){const at=stack.pop()*10;let overlap=true;for(let k=0;k<3;k++)if(a.min[k]>nodes[at+3+k]+1e-10||a.max[k]<nodes[at+k]-1e-10){overlap=false;break;}if(!overlap)continue;if(nodes[at+9])for(let i=0;i<nodes[at+9];i++){const id=order[nodes[at+8]+i],b=bodyFaces[id];if(overlaps(a,b)){candidates++;if(triangleCross(a.points,b.points))pairs.push([f,id]);}}else stack.push(nodes[at+6],nodes[at+7]);}}return {pairs,candidates};}
 function selfPairs(faces){const buckets=new Map(),seen=new Set(),pairs=[];let candidates=0;const cell=.045;
  for(let f=0;f<faces.length;f++){const a=faces[f],lo=a.min.map(x=>Math.floor(x/cell)),hi=a.max.map(x=>Math.floor(x/cell));if(hi.some((x,k)=>x-lo[k]>24))throw new Error('Divergent triangle before self-intersection audit');
   for(let x=lo[0];x<=hi[0];x++)for(let y=lo[1];y<=hi[1];y++)for(let z=lo[2];z<=hi[2];z++){
    const key=`${x},${y},${z}`,list=buckets.get(key)||[];for(const g of list){const pair=g*faces.length+f;if(seen.has(pair))continue;seen.add(pair);const b=faces[g];if(a.ids.some(i=>b.ids.includes(i))||!overlaps(a,b))continue;candidates++;if(triangleCross(a.points,b.points))pairs.push([g,f]);}list.push(f);buckets.set(key,list);
   }
  }return {pairs,candidates};
 }
 return {bodyPairs,selfPairs,bodyFaces};
}
export function faceNormal(points){const n=cross(sub(points[1],points[0]),sub(points[2],points[0])),length=Math.hypot(...n)||1;return n.map(x=>x/length);}
