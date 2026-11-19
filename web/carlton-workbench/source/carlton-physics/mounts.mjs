// Locate an attachment on its host mesh and keep barycentric weights so it
// follows the cloth instead of sliding over the animated surface.
export function onSurface(point, coordinates, faces, dimensions) {
  const dot=(a,b)=>a.reduce((sum,value,i)=>sum+value*b[i],0)
  const sub=(a,b)=>a.map((value,i)=>value-b[i])
  const at=id=>coordinates.slice(id*dimensions,(id+1)*dimensions)
  let closest
  for(let i=0;i<faces.length;i+=3){
    const ids=Array.from(faces.slice(i,i+3))
    const [a,b,c]=ids.map(at)
    const ab=sub(b,a), ac=sub(c,a), ap=sub(point,a)
    const bb=dot(ab,ab), cc=dot(ac,ac), bc=dot(ab,ac)
    const bp=dot(ab,ap), cp=dot(ac,ap), det=bb*cc-bc*bc
    const v=(cc*bp-bc*cp)/det, w=(bb*cp-bc*bp)/det
    const weights=[1-v-w,v,w]
    const candidates=weights.every(t=>t>=0)?[weights]:[[0,1],[1,2],[2,0]].map(([s,e])=>{
      const start=[a,b,c][s], dir=sub([a,b,c][e],start)
      const t=Math.max(0,Math.min(1,dot(sub(point,start),dir)/dot(dir,dir)))
      const edge=[0,0,0]
      edge[s]=1-t
      edge[e]=t
      return edge
    })
    for(const candidate of candidates){
      const projected=interpolate(coordinates,[...ids,...candidate],dimensions)
      const distance=Math.hypot(...sub(point,projected))
      if(distance<(closest?.distance??Infinity))closest={distance,anchor:[...ids,...candidate]}
    }
  }
  return closest
}

export function interpolate(coordinates,[a,b,c,u,v,w],dimensions){
  return Array.from({length:dimensions},(_,i)=>
    u*coordinates[dimensions*a+i]+v*coordinates[dimensions*b+i]+w*coordinates[dimensions*c+i])
}
