// Collapse short edges and near-collinear corners; source-space boundary error is independently bounded to 0.01 mm.
export function collapseShortEdges(positions,triangles,step){
 const points=positions.map(p=>p.clone()),ts=triangles.map(t=>t.slice());let total=0;
 const area=(a,b,c)=>(b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x);
 for(let pass=0;pass<12;pass++){
  const edges=new Map(),inc=points.map(()=>new Set()),neighbors=points.map(()=>new Set());
  ts.forEach((t,f)=>{if(!t)return;for(const a of t)inc[a].add(f);for(let k=0;k<3;k++){const a=t[k],b=t[(k+1)%3],key=a<b?a+':'+b:b+':'+a;if(!edges.has(key))edges.set(key,{a,b,faces:[]});edges.get(key).faces.push(f);neighbors[a].add(b);neighbors[b].add(a);}});
  const bd=points.map(()=>[]);for(const e of edges.values())if(e.faces.length===1){bd[e.a].push(e.b);bd[e.b].push(e.a);}
  const removable=i=>bd[i].length===2&&Math.abs(area(points[bd[i][0]],points[i],points[bd[i][1]]))/Math.max(1e-9,points[bd[i][0]].distanceTo(points[bd[i][1]]))<.005;
  const short=[...edges.values()].filter(e=>points[e.a].distanceTo(points[e.b])<step*.31).sort((a,b)=>points[a.a].distanceTo(points[a.b])-points[b.a].distanceTo(points[b.b]));const changed=new Set();let count=0;
  for(const e of short){let {a,b}=e;if(changed.has(a)||changed.has(b)||!inc[a].size||!inc[b].size)continue;
   if(bd[a].length&&!bd[b].length){[a,b]=[b,a];} // a removed, b retained
   if(bd[a].length){if(!bd[b].length)continue;if(!removable(a)){if(removable(b))[a,b]=[b,a];else continue;}if(!neighbors[a].has(b))continue;}
   const common=[...neighbors[a]].filter(i=>neighbors[b].has(i)),opposite=e.faces.map(f=>ts[f]?.find(i=>i!==a&&i!==b)).filter(i=>i!==undefined);if(common.length!==opposite.length||common.some(i=>!opposite.includes(i)))continue;
   let valid=true;for(const f of inc[a]){const t=ts[f];if(t.includes(b))continue;const next=t.map(i=>i===a?b:i),old=area(...t.map(i=>points[i])),fresh=area(...next.map(i=>points[i]));if(fresh*old<=0||Math.abs(fresh)<1e-7){valid=false;break;}}
   if(!valid)continue;
   for(const f of inc[a]){const t=ts[f];if(t.includes(b))ts[f]=null;else ts[f]=t.map(i=>i===a?b:i);}for(const n of neighbors[a])changed.add(n);for(const n of neighbors[b])changed.add(n);changed.add(a);changed.add(b);count++;
  }
  total+=count;if(!count)break;
 }
 const used=[...new Set(ts.filter(Boolean).flat())].sort((a,b)=>a-b),ids=new Map(used.map((v,i)=>[v,i]));return{positions:used.map(i=>points[i]),triangles:ts.filter(Boolean).map(t=>t.map(i=>ids.get(i))),collapsedEdges:total};
}
