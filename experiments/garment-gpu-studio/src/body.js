import original from '../assets/body.json' with {type:'json'};
const copy = value => JSON.parse(JSON.stringify(value));
export const BASE_SIZE = { heightCm:166.59271, chestMm:854.7237, waistMm:670.4762, hipMm:968.6076 };
export const referenceBody = () => copy(original);

// Intersect the rendered triangles; join exact mesh-edge intersections into loops.
export function section(body, y) {
  const segments=[], p=body.positions, t=body.triangles;
  for(let f=0; f<t.length; f+=3){
    const hits=[];
    for(let e=0;e<3;e++){
      const a=t[f+e]*3,b=t[f+(e+1)%3]*3, ay=p[a+1],by=p[b+1];
      if((ay<=y && by>y)||(by<=y && ay>y)){
        const q=(y-ay)/(by-ay); hits.push([p[a]+q*(p[b]-p[a]),p[a+2]+q*(p[b+2]-p[a+2])]);
      }
    }
    if(hits.length===2)segments.push(hits);
  }
  const key=p=>p.map(x=>Math.round(x*1e7)).join(','),adj=new Map();
  for(const [a,b]of segments){for(const [u,v]of [[a,b],[b,a]]){const k=key(u);if(!adj.has(k))adj.set(k,[]);adj.get(k).push(v);}}
  const seen=new Set(),loops=[];
  for(const [start]of adj){
    if(seen.has(start))continue;const points=[];let k=start,previous=null;
    while(!seen.has(k)){
      seen.add(k); const ns=adj.get(k)||[]; const next=ns.find(q=>key(q)!==previous)||ns[0]; if(!next)break;
      const here=k.split(',').map(x=>Number(x)/1e7);points.push(here);previous=k;k=key(next);
    }
    if(k===start&&points.length>3){const xs=points.map(p=>p[0]);if(Math.min(...xs)<0&&Math.max(...xs)>0)loops.push(points);}
  }
  if(!loops.length)throw new Error('人体截面没有闭合躯干环');
  const points=loops.sort((a,b)=>b.length-a.length)[0];
  const perimeter=points.reduce((s,p,i)=>s+Math.hypot(p[0]-points[(i+1)%points.length][0],p[1]-points[(i+1)%points.length][1]),0);
  return {height:y,circumference:perimeter,pointsXZ:points.flat()};
}

export function makeBody(size) {
  for(const [k,lo,hi]of [['heightCm',145,195],['chestMm',800,1100],['waistMm',580,1000],['hipMm',800,1200]])
    if(!Number.isFinite(size[k])||size[k]<lo||size[k]>hi)throw new Error(`${k}: ${lo}–${hi}`);
  const body=referenceBody(),sy=size.heightCm/BASE_SIZE.heightCm;
  const anchors=[[0,1],[.55,1],[original.measurements.hip.height,size.hipMm/BASE_SIZE.hipMm],[original.measurements.waist.height,size.waistMm/BASE_SIZE.waistMm],[original.measurements.chest.height,size.chestMm/BASE_SIZE.chestMm],[1.43,1],[1.666,1]];
  function horizontal(y){for(let i=1;i<anchors.length;i++)if(y<=anchors[i][0]){const a=anchors[i-1],b=anchors[i],q=Math.max(0,(y-a[0])/(b[0]-a[0]));return a[1]+q*(b[1]-a[1]);}return 1;}
  const transform=p=>{const s=horizontal(p[1]),cz=.025;return [p[0]*s,p[1]*sy,cz+(p[2]-cz)*s];};
  // Scaling varies through each source triangle. Correct the anchor factors by
  // measuring the resulting triangle-plane loops, rather than claiming nominal
  // factors are exact measurements of the morphed mesh.
  for(let pass=0;pass<5;pass++){
    body.positions=[];for(let i=0;i<original.positions.length;i+=3)body.positions.push(...transform(original.positions.slice(i,i+3)));
    let maxError=0;for(const [key,field,index]of [['chest','chestMm',4],['waist','waistMm',3],['hip','hipMm',2]]){
      const actual=section(body,original.measurements[key].height*sy).circumference*1000;maxError=Math.max(maxError,Math.abs(actual-size[field]));if(pass<4)anchors[index][1]*=size[field]/actual;
    }if(maxError<.01)break;
  }
  for(const k of ['shoulderLeft','shoulderRight','axillaLeft','axillaRight','neckCenter'])body.landmarks[k]=transform(original.landmarks[k]);
  for(const hand of ['left','right'])body.landmarks.armCenters[hand]=original.landmarks.armCenters[hand].map(transform);
  body.measurements.height=original.measurements.height*sy;
  for(const k of ['chest','waist','hip','neck'])body.measurements[k]={...body.measurements[k],...section(body,original.measurements[k].height*sy)};
  body.measurements.shoulderWidth=Math.abs(body.landmarks.shoulderRight[0]-body.landmarks.shoulderLeft[0]);
  body.measurements.shoulderHeight=body.landmarks.shoulderRight[1];
  const n=body.collision.bvh.nodes,order=body.collision.bvh.triangleOrder;
  for(let i=n.length/10-1;i>=0;i--){const at=i*10;const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
    if(n[at+9]>0){for(let j=0;j<n[at+9];j++){const f=order[n[at+8]+j]*3;for(let c=0;c<3;c++){const v=body.triangles[f+c]*3;for(let d=0;d<3;d++){lo[d]=Math.min(lo[d],body.positions[v+d]);hi[d]=Math.max(hi[d],body.positions[v+d]);}}}}
    else for(const child of [n[at+6],n[at+7]])for(let d=0;d<3;d++){lo[d]=Math.min(lo[d],n[child*10+d]);hi[d]=Math.max(hi[d],n[child*10+d+3]);}
    for(let d=0;d<3;d++){n[at+d]=lo[d];n[at+d+3]=hi[d];}
  }
  body.bounds={min:n.slice(0,3),max:n.slice(3,6)};
  body.requestedSize=copy(size);body.provenance.morph='Smooth cross-section scale of CC0 reference mesh; not a body scan. Display and collision use identical morphed triangles.';
  body.measurementErrorMm=Object.fromEntries([['chest','chestMm'],['waist','waistMm'],['hip','hipMm']].map(([a,b])=>[a,body.measurements[a].circumference*1000-size[b]]));
  return body;
}
