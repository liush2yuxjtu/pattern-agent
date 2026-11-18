// Uses triangle positions and topology, never smoothed rendering normals.
const sub = (a,b) => a.map((v,i)=>v-b[i]);
const dot = (a,b) => a.reduce((s,v,i)=>s+v*b[i],0);
const cross = (a,b) => [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const length = a => Math.hypot(...a);
const distance2d = (p,a,b) => {
  const v=[b.x-a.x,b.y-a.y],q=[p.x-a.x,p.y-a.y];
  const t=Math.max(0,Math.min(1,dot(q,v)/(dot(v,v)||1)));
  return Math.hypot(q[0]-v[0]*t,q[1]-v[1]*t);
};
const stats = values => {
  const a=values.slice().sort((x,y)=>x-y);
  return {count:a.length,min:a.length?a[0]:null,median:a.length?(a[Math.floor((a.length-1)/2)]+a[Math.floor(a.length/2)])/2:null,
    p95:a.length?a[Math.ceil(a.length*.95)-1]:null,max:a.length?a.at(-1):null};
};
export const summarizeCreaseEdges = (edges,limitDeg=45,warningDeg=25) => ({
  stats:stats(edges.map(e=>e.angleDeg)),peak:edges.reduce((a,b)=>!a||b.angleDeg>a.angleDeg?b:a,null),
  sharpCount:edges.filter(e=>e.angleDeg>limitDeg).length,
  warningCount:edges.filter(e=>e.angleDeg>warningDeg&&e.angleDeg<=limitDeg).length,
  histogram:[[0,5],[5,15],[15,25],[25,45],[45,180]].map(([min,max],i)=>({minDeg:min,maxDeg:max,
    count:edges.filter(e=>(i===0?e.angleDeg>=min:e.angleDeg>min)&&e.angleDeg<=max).length})),
});

export function inspectCreases(panels,{limitDeg=45,warningDeg=25,underarmExclusionMm=15,includeBody=false}={}) {
  const parts=[];
  for(const p of panels.filter(p=>includeBody||(p.partId||p.part||'').startsWith('sleeve'))) {
    const id=p.partId||p.part,vertices=p.vertices,uv=p.points2d;
    if(!vertices?.length||!p.triangles?.length||uv?.length!==vertices.length)throw Error('袖片缺少三维位置、三角面或毫米材料坐标');
    if(!vertices.every(v=>v.length===3&&v.every(Number.isFinite))||!uv.every(v=>Number.isFinite(v.x)&&Number.isFinite(v.y)))throw Error('袖片存在非有限坐标');
    const edges=new Map(),normals=[],centers=[],invalidFaces=[];
    p.triangles.forEach((t,f)=>{
      if(t.length!==3||!t.every(i=>Number.isInteger(i)&&i>=0&&i<vertices.length))throw Error('袖片三角面索引无效');
      const [a,b,c]=t.map(i=>vertices[i]),n=cross(sub(b,a),sub(c,a)),area2=length(n);
      normals.push(Number.isFinite(area2)&&area2>1e-12?n.map(v=>v/area2):null);
      centers.push(a.map((v,k)=>(v+b[k]+c[k])/3));
      if(!Number.isFinite(area2)||area2<=1e-12)invalidFaces.push(f);
      for(let k=0;k<3;k++) {
        const a=t[k],b=t[(k+1)%3],key=a<b?a+':'+b:b+':'+a;
        if(!edges.has(key))edges.set(key,{id:id+':'+key,a:Math.min(a,b),b:Math.max(a,b),faces:[],directions:[]});
        const e=edges.get(key);e.faces.push(f);e.directions.push(a<b?1:-1);
      }
    });
    const underarm=(p.boundary||[]).filter(e=>e.edge.startsWith('underarm'));
    if(id.startsWith('sleeve')&&!underarm.length)throw Error('袖片没有袖底缝标记，不能悄悄套用排除范围');
    const rows=[],invalidEdges=[];
    for(const e of edges.values()) {
      if(e.faces.length===1)continue;
      if(e.faces.length!==2||e.directions[0]===e.directions[1]||e.faces.some(f=>!normals[f])) {
        invalidEdges.push({...e,reason:e.faces.length!==2?'non-manifold':e.directions[0]===e.directions[1]?'inconsistent-winding':'degenerate-face'});continue;
      }
      const a=uv[e.a],b=uv[e.b],midUv={x:(a.x+b.x)/2,y:(a.y+b.y)/2};
      const underarmDistanceMm=underarm.length?Math.min(...underarm.map(s=>distance2d(midUv,uv[s.a],uv[s.b]))):null;
      if(underarmDistanceMm!==null&&!Number.isFinite(underarmDistanceMm)){invalidEdges.push({...e,reason:'invalid-material-distance'});continue;}
      const n=e.faces.map(f=>normals[f]),angleDeg=Math.atan2(length(cross(n[0],n[1])),dot(n[0],n[1]))*180/Math.PI;
      const excluded=underarmDistanceMm!==null&&underarmDistanceMm<underarmExclusionMm;
      rows.push({...e,angleDeg,excluded,classification:excluded?'excluded':angleDeg>limitDeg?'sharp':angleDeg>warningDeg?'warning':'smooth',
        midpoint:vertices[e.a].map((v,k)=>(v+vertices[e.b][k])/2),midUv,endpointsUv:[a,b],normals:n,faceCenters:e.faces.map(f=>centers[f]),underarmDistanceMm,
        edgeLengthMm:length(sub(vertices[e.a],vertices[e.b]))*1000});
    }
    const included=rows.filter(e=>!e.excluded),sharp=included.filter(e=>e.classification==='sharp');
    const byVertex=new Map();for(const e of sharp)for(const i of[e.a,e.b]){if(!byVertex.has(i))byVertex.set(i,[]);byVertex.get(i).push(e);}
    const seen=new Set(),clusters=[];
    for(const edge of sharp){if(seen.has(edge.id))continue;const pending=[edge],cluster=[];while(pending.length){const e=pending.pop();if(seen.has(e.id))continue;seen.add(e.id);cluster.push(e);for(const i of[e.a,e.b])for(const next of byVertex.get(i)||[])if(!seen.has(next.id))pending.push(next);}clusters.push({edgeIds:cluster.map(e=>e.id),count:cluster.length,maxDeg:Math.max(...cluster.map(e=>e.angleDeg)),lengthMm:cluster.reduce((s,e)=>s+e.edgeLengthMm,0)});}
    parts.push({partId:id,edges:rows,stats:stats(included.map(e=>e.angleDeg)),sharpCount:sharp.length,warningCount:included.filter(e=>e.classification==='warning').length,
      excludedCount:rows.length-included.length,invalidFaces,invalidEdges,clusters});
  }
  if(!parts.length)throw Error('没有可检查的袖片');
  const eligible=parts.filter(p=>p.partId.startsWith('sleeve')).flatMap(p=>p.edges.filter(e=>!e.excluded));
  const peak=eligible.reduce((a,b)=>!a||b.angleDeg>a.angleDeg?b:a,null);
  const invalidCount=parts.reduce((s,p)=>s+p.invalidFaces.length+p.invalidEdges.length+(p.stats.count===0?1:0),0);
  const sharpCount=eligible.filter(e=>e.angleDeg>limitDeg).length;
  const allEdges=parts.flatMap(p=>p.edges),excluded=allEdges.filter(e=>e.excluded);
  return {schema:'sleeve-crease-diagnostic/1',status:invalidCount?'INVALID':sharpCount?'FAIL':'PASS',
    scopeZh:includeBody?'整件衣服各裁片内部的几何折角；非应力、压力或实物合体结论':'当前网格的袖片内部几何折角；非应力、压力或实物合体结论',
    method:'oriented adjacent triangle normals from positions; atan2(norm(cross),dot), no abs(dot); source-UV underarm exclusion',
    angleConventionZh:'相邻三角面方向的转折：平面0°，直角90°，折回180°；角度取决于网格细度，不是整只袖子的弯曲角。',
    verdictScopeZh:`PASS仅适用于袖片排除袖底缝${underarmExclusionMm} mm邻域的内部尖棱检查。${limitDeg}°是本项目的检查阈值，不代表整件衣服合格。`,
    limits:{limitDeg,warningDeg,underarmExclusionMm},sharpCount,invalidCount,peak,parts,
    all:summarizeCreaseEdges(allEdges,limitDeg,warningDeg),quality:summarizeCreaseEdges(eligible,limitDeg,warningDeg),
    underarm:summarizeCreaseEdges(excluded,limitDeg,warningDeg)};
}
export function inspectSleeveCreases(panels,options={}){return inspectCreases(panels,{...options,includeBody:false});}
