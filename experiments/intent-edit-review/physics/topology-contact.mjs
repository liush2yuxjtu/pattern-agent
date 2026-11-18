// Static material adjacency exclusions apply only to contact response.
// The independent intersection verifier still tests every incident face pair.
export function contactExclusions(triangles,count){
 const neighbors=Array.from({length:count},(_,i)=>new Set([i])),faces=[];
 for(let t=0;t<triangles.length;t+=3){
  const face=Array.from(triangles.slice(t,t+3));faces.push(face);
  for(const a of face)for(const b of face)neighbors[a].add(b);
 }
 return {
  excludeVertexFace:(id,face)=>faces[face].some(other=>neighbors[id].has(other)),
  excludeEdgePair:([a,b],[c,d])=>neighbors[a].has(c)||neighbors[a].has(d)||neighbors[b].has(c)||neighbors[b].has(d)
 };
}
