export function buildConstraints(doc) {
  const count=doc.mesh.restUV.length,parent=Int32Array.from({length:count},(_,i)=>i);
  const find=i=>parent[i]===i?i:parent[i]=find(parent[i]);
  for(const seam of doc.seams)for(const [a,b]of seam.pairs)parent[find(b)]=find(a);
  const groups=new Map();for(let i=0;i<count;i++){const r=find(i);if(!groups.has(r))groups.set(r,[]);groups.get(r).push(i);}
  const list=[...groups.values()],rootToNode=new Map(list.map((g,i)=>[find(g[0]),i]));
  const map=Array.from({length:count},(_,i)=>rootToNode.get(find(i)));
  const initial=new Float32Array(list.length*4);
  for(let g=0;g<list.length;g++){for(const i of list[g])for(let a=0;a<3;a++)initial[g*4+a]+=doc.mesh.initial[i*3+a]/list[g].length;initial[g*4+3]=1;}
  // Welded seam groups are exact equality constraints. Rest UVs remain independent.
  const edges=doc.mesh.edges.map(e=>({a:map[e.a],b:map[e.b],rest:e.restMm/1000,compliance:0,kind:'stretch'})).filter(e=>e.a!==e.b);
  const bending=[],shared=new Map();
  for(const piece of doc.pieces)for(let f=0;f<piece.triangles.length;f+=3){
    const t=piece.triangles.slice(f,f+3).map(i=>i+piece.offset);
    for(let e=0;e<3;e++){const a=t[e],b=t[(e+1)%3],c=t[(e+2)%3],key=[a,b].sort((a,b)=>a-b).join(',');
      if(shared.has(key)){const d=shared.get(key);bending.push({a:map[c],b:map[d],rest:Math.hypot(doc.mesh.restUV[c][0]-doc.mesh.restUV[d][0],doc.mesh.restUV[c][1]-doc.mesh.restUV[d][1])/1000,compliance:.002,kind:'bend'});}else shared.set(key,c);
    }
  }
  const all=[...edges,...bending],used=Array.from({length:list.length},()=>new Set()),colors=[];
  for(const c of all){let k=0;while(used[c.a].has(k)||used[c.b].has(k))k++;if(!colors[k])colors[k]=[];colors[k].push(c);used[c.a].add(k);used[c.b].add(k);}
  return {map,groups:list,initial,edges,bending,colors,triangles:doc.mesh.triangles.map(i=>map[i]),pins:doc.mesh.pins.map(i=>map[i]),nodeCount:list.length};
}

export function expandPositions(model,p) {const out=new Float32Array(model.map.length*3);for(let i=0;i<model.map.length;i++)for(let a=0;a<3;a++)out[i*3+a]=p[model.map[i]*4+a];return out;}
