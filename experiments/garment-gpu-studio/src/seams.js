export function checkSeams(doc,positions=null){
  const used=new Set(),errors=[];
  const rows=doc.seams.map(s=>{
    const refs=[];
    for(const side of [s.a,s.b]){const key=`${side.piece}/${side.edge}`;if(used.has(key))errors.push(`重复缝边: ${key}`);used.add(key);}
    for(const [j,side]of [s.a,s.b].entries()){
      const piece=doc.pieces.find(p=>p.id===side.piece),edge=piece?.seamEdges.find(e=>e.id===side.edge);
      if(!piece||!edge){errors.push(`无效缝边: ${s.id}`);refs.push([]);continue;}
      const ids=edge.vertices.map(i=>i+piece.offset),direction=j===0?s.directionA:s.directionB;
      if(![1,-1].includes(direction))errors.push(`未定义方向: ${s.id}`);
      refs.push(direction===-1?ids.reverse():ids);
      const length=ids.slice(1).reduce((sum,b,i)=>sum+Math.hypot(doc.mesh.restUV[b][0]-doc.mesh.restUV[ids[i]][0],doc.mesh.restUV[b][1]-doc.mesh.restUV[ids[i]][1]),0);
      if(Math.abs(length-(j===0?s.lengthAmm:s.lengthBmm))>1e-5)errors.push(`过期缝边长度: ${s.id}`);
    }
    if(refs[0].length!==s.pairs.length||refs[1].length!==s.pairs.length)errors.push(`采样数不符: ${s.id}`);
    s.pairs.forEach(([a,b],i)=>{if(a!==refs[0][i]||b!==refs[1][i])errors.push(`配对或方向错误: ${s.id}`);});
    if(!s.pairs.length)errors.push(`空接缝: ${s.id}`);
    let gap=0;
    for(const [a,b]of s.pairs){if(!Number.isInteger(a)||!Number.isInteger(b)||a<0||b<0||a>=doc.mesh.restUV.length||b>=doc.mesh.restUV.length)errors.push(`无效节点: ${s.id}`);
      if(positions)gap=Math.max(gap,1000*Math.hypot(...[0,1,2].map(k=>positions[a*3+k]-positions[b*3+k])));}
    const mismatch=Math.abs(s.lengthAmm-s.lengthBmm)/Math.max(s.lengthAmm,s.lengthBmm);
    return {id:s.id,pairs:s.pairs.length,lengthAmm:s.lengthAmm,lengthBmm:s.lengthBmm,mismatch,gapMm:gap,directionB:s.directionB,easeRule:'arc-length paired; original edge rest lengths retained',status:mismatch>.02||gap>2?'FAIL':'PASS'};
  });
  return {status:errors.length||rows.some(x=>x.status==='FAIL')?'FAIL':'PASS',errors,rows,maxGapMm:Math.max(...rows.map(x=>x.gapMm)),maxMismatch:Math.max(...rows.map(x=>x.mismatch))};
}
