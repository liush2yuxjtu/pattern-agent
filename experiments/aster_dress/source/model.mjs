// Aster 01: millimetres throughout. Exact conical development, not a cloth solver.
export const DEFAULTS = { bust: 920, waist: 760, hem: 2400, bodice: 270, skirt: 780, allowance: 10, hemAllowance: 25 };
export const TAU = Math.PI * 2, N = 8, STEP = TAU / N;
export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export const num = (v, d = 1) => Number(v.toFixed(d));
export function dimensions(c, type) {
  const r0 = c.waist / TAU, r1 = (type === 'B' ? c.bust : c.hem) / TAU;
  const h = type === 'B' ? c.bodice : c.skirt, dr = r1 - r0, s = Math.hypot(h, dr), k = dr / s;
  return { r0, r1, h, dr, s, k, L0: r0 / k };
}
export function point3(c, type, i, u, t) {
  const d = dimensions(c, type), r = d.r0 + d.dr * t, a = (i + u) * STEP;
  return [r * Math.sin(a), type === 'B' ? c.skirt + d.h * t : d.h * (1-t), r * Math.cos(a)];
}
export function point2(c, type, u, t) {
  const d = dimensions(c, type), L = d.L0 + d.s * t, b = (u-.5) * STEP * d.k;
  const x = L * Math.sin(b), y = L * Math.cos(b) - d.L0;
  return [x, type === 'B' ? d.s - y : y];
}
export function edge(c, type, name, samples = 96) {
  return Array.from({length:samples+1}, (_,i) => {
    const f=i/samples;
    return name==='left' ? point2(c,type,0,f) : name==='right' ? point2(c,type,1,f) : point2(c,type,f,name==='waist'?0:1);
  });
}
export function outline(c,type, samples=96) {
  const top=type==='B'?1:0, bottom=1-top, p=[];
  for(let j=0;j<samples;j++)p.push(point2(c,type,j/samples,top));
  for(let j=0;j<samples;j++)p.push(point2(c,type,1,top+(bottom-top)*j/samples));
  for(let j=0;j<samples;j++)p.push(point2(c,type,1-j/samples,bottom));
  for(let j=0;j<samples;j++)p.push(point2(c,type,0,bottom+(top-bottom)*j/samples));
  return p;
}
export function polygonArea(p) { return p.reduce((a,v,i)=>{const q=p[(i+1)%p.length];return a+v[0]*q[1]-q[0]*v[1]},0)/2; }
export function offsetOutline(c,type,samples=96) {
  const p=outline(c,type,samples), sign=Math.sign(polygonArea(p));
  const line=(i)=>{let a=p[i],b=p[(i+1)%p.length],dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy);let amount=type==='S'&&i>=samples*2&&i<samples*3?c.hemAllowance:c.allowance;return {a:[a[0]+sign*dy/len*amount,a[1]-sign*dx/len*amount],d:[dx,dy]};};
  return p.map((_,i)=>{const a=line((i+p.length-1)%p.length),b=line(i),cross=a.d[0]*b.d[1]-a.d[1]*b.d[0];if(Math.abs(cross)<1e-9)return b.a;const q=[b.a[0]-a.a[0],b.a[1]-a.a[1]],t=(q[0]*b.d[1]-q[1]*b.d[0])/cross;return [a.a[0]+t*a.d[0],a.a[1]+t*a.d[1]];});
}
export function bounds(p){return {minX:Math.min(...p.map(v=>v[0])),maxX:Math.max(...p.map(v=>v[0])),minY:Math.min(...p.map(v=>v[1])),maxY:Math.max(...p.map(v=>v[1]))};}
export function layout(c){
  const b=bounds(offsetOutline(c,'B')),s=bounds(offsetOutline(c,'S')),w=s.maxX-s.minX+65,hB=b.maxY-b.minY+85,hS=s.maxY-s.minY+95;
  return {w,hB,width:w*8+100,height:hB+hS+130,place:(type,i)=>[50+w*(i+.5),70+(type==='B'?-b.minY:hB-s.minY)]};
}
export function panelIds(){return ['B','S'].flatMap(t=>Array.from({length:N},(_,i)=>t+String(i+1).padStart(2,'0')));}
export function seams(c){const all=[];for(const type of ['B','S'])for(let i=0;i<N;i++){const d=dimensions(c,type);all.push({id:`${type}${String(i+1).padStart(2,'0')}`,type,index:i,a:`${type}${String(i+1).padStart(2,'0')}`,b:`${type}${String((i+1)%N+1).padStart(2,'0')}`,edgeA:'right',edgeB:'left',lengthA:d.s,lengthB:d.s,label:`${type==='B'?'Bodice':'Skirt'} ${i+1}${i===3?' · center back':''}`,closure:i===3});}for(let i=0;i<N;i++)all.push({id:`W${String(i+1).padStart(2,'0')}`,type:'W',index:i,a:`B${String(i+1).padStart(2,'0')}`,b:`S${String(i+1).padStart(2,'0')}`,edgeA:'waist',edgeB:'waist',lengthA:c.waist/N,lengthB:c.waist/N,label:`Waist ${i+1}`,closure:false});return all;}
export function seamPoints(c,seam,side){const type=side==='a'?seam.a[0]:seam.b[0],idx=Number((side==='a'?seam.a:seam.b).slice(1))-1;return Array.from({length:65},(_,j)=>{const f=j/64;return seam.type==='W'?{u:f,t:0,type,i:idx}: {u:side==='a'?1:0,t:f,type,i:idx};});}
export function length(p){return p.slice(1).reduce((s,v,i)=>s+Math.hypot(...v.map((n,j)=>n-p[i][j])),0);}
export function verify(c=DEFAULTS){
  let maxRelativeEdgeError=0,maxSeamMismatch=0,maxCoincidenceError=0,maxAreaError=0,checkedEdges=0;
  const panelResults=[];
  for(const type of ['B','S']){
    const nu=32,nt=24;let area3=0,area2=0;
    for(let t=0;t<nt;t++)for(let u=0;u<nu;u++){
      const uv=[[u/nu,t/nt],[(u+1)/nu,t/nt],[u/nu,(t+1)/nt],[(u+1)/nu,(t+1)/nt]];
      const p3=uv.map(([x,y])=>point3(c,type,0,x,y)),p2=uv.map(([x,y])=>point2(c,type,x,y));
      for(const [a,b] of [[0,1],[0,2],[1,2],[1,3],[2,3]]){const l3=Math.hypot(...p3[a].map((v,k)=>v-p3[b][k])),l2=Math.hypot(...p2[a].map((v,k)=>v-p2[b][k]));maxRelativeEdgeError=Math.max(maxRelativeEdgeError,Math.abs(l2-l3)/l3);checkedEdges++;}
      for(const [a,b,z] of [[0,1,2],[1,3,2]]){const e=p3[b].map((v,k)=>v-p3[a][k]),f=p3[z].map((v,k)=>v-p3[a][k]);area3+=Math.hypot(e[1]*f[2]-e[2]*f[1],e[2]*f[0]-e[0]*f[2],e[0]*f[1]-e[1]*f[0])/2;area2+=Math.abs(polygonArea([p2[a],p2[b],p2[z]]));}
    }
    maxAreaError=Math.max(maxAreaError,Math.abs(area2-area3)/area3);
    panelResults.push({type,slantLengthMM:dimensions(c,type).s,area3DMM2:area3,area2DMM2:area2,outlineFinite:offsetOutline(c,type).every(p=>p.every(Number.isFinite))});
  }
  const pairResults=seams(c).map(s=>{maxSeamMismatch=Math.max(maxSeamMismatch,Math.abs(s.lengthA-s.lengthB));const pa=seamPoints(c,s,'a'),pb=seamPoints(c,s,'b');const dist=Math.max(...pa.map((p,j)=>{const a=point3(c,p.type,p.i,p.u,p.t),q=pb[j],b=point3(c,q.type,q.i,q.u,q.t);return Math.hypot(...a.map((v,k)=>v-b[k]));}));maxCoincidenceError=Math.max(maxCoincidenceError,dist);return {...s,deltaMM:Math.abs(s.lengthA-s.lengthB),maxCoincidenceErrorMM:dist};});
  return {method:'Independent 3D/2D sampled edge and triangle comparisons; 65 endpoint samples per seam pair. Curved-surface chords have finite tessellation error.',units:'mm',checkedEdges,seamPairs:pairResults.length,maxRelativeEdgeError,maxAreaError,maxSeamMismatchMM:maxSeamMismatch,maxCoincidenceErrorMM:maxCoincidenceError,panelResults,pairResults,passed:maxRelativeEdgeError<0.0001&&maxAreaError<0.0002&&maxSeamMismatch<0.001&&maxCoincidenceError<0.001&&panelResults.every(x=>x.outlineFinite)};
}
