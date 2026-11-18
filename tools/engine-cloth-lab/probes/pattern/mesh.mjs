import cdt2d from 'cdt2d'
import { signedArea } from './adapter.mjs'

const distance=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1])
const key=(panel,edge)=>`${panel}/${edge}`
export function pointInPolygon(p,polygon){
 let inside=false
 for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){
  const a=polygon[i],b=polygon[j]
  if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])inside=!inside
 }
 return inside
}
const segmentDistance=(p,a,b)=>{
 const dx=b[0]-a[0],dy=b[1]-a[1],l2=dx*dx+dy*dy
 const t=l2===0?0:Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/l2))
 return distance(p,[a[0]+dx*t,a[1]+dy*t])
}
function resample(points,segments){
 const cumulative=[0]
 for(let i=1;i<points.length;i++)cumulative.push(cumulative.at(-1)+distance(points[i-1],points[i]))
 const total=cumulative.at(-1)
 let j=1
 return Array.from({length:segments+1},(_,i)=>{
  if(i===0)return [...points[0]]
  if(i===segments)return [...points.at(-1)]
  const offset=total*i/segments
  while(j<cumulative.length-1&&cumulative[j]<offset)j++
  const t=(offset-cumulative[j-1])/(cumulative[j]-cumulative[j-1])
  return points[j-1].map((value,axis)=>value+(points[j][axis]-value)*t)
 })
}
export function makeMesh(draft,{spacingMM=24,boundarySpacingMM=spacingMM}={}){
 if(draft.status!=='DRAFTED')throw new Error('Only explicit drafted geometry can be meshed')
 if(!Number.isFinite(spacingMM)||spacingMM<=0)throw new Error('spacingMM must be positive')
 if(!Number.isFinite(boundarySpacingMM)||boundarySpacingMM<=0)throw new Error('boundarySpacingMM must be positive')
 const segmentCounts=new Map()
 for(const p of draft.panels)for(const e of Object.values(p.pathLabels))segmentCounts.set(key(p.id,e.id),Math.max(1,Math.ceil(e.lengthMM/boundarySpacingMM)))
 for(const seam of draft.seams){
  const ak=key(seam.a.panel,seam.a.edge),bk=key(seam.b.panel,seam.b.edge)
  const n=Math.max(segmentCounts.get(ak),segmentCounts.get(bk))
  segmentCounts.set(ak,n);segmentCounts.set(bk,n)
 }
 const restXY=[],triangles=[],panelOfVertex=[],panels=[]
 for(const source of draft.panels){
  const offset=restXY.length,points=[],pointIds=new Map(),labels={},boundary=[]
  const add=p=>{const k=p.map(v=>v.toFixed(7)).join(',');if(pointIds.has(k))return pointIds.get(k);const id=points.length;points.push(p);pointIds.set(k,id);return id}
  for(const e of Object.values(source.pathLabels)){
   const n=segmentCounts.get(key(source.id,e.id))
   const samples=resample(e.samplesMM,n)
   labels[e.id]={id:e.id,vertexIds:samples.map(add),endpointRoles:e.endpointRoles,lengthMM:e.lengthMM,sourceNativeOps:e.nativeOps,mirrorX:e.mirrorX,segmentCount:n}
  }
  for(const item of source.boundaryOrder){
   const ids=labels[item.edge].vertexIds
   const ordered=item.direction===1?ids:[...ids].reverse()
   if(boundary.length&&boundary.at(-1)!==ordered[0])throw new Error(`Disconnected boundary ${source.id}/${item.edge}`)
   boundary.push(...ordered.slice(boundary.length?1:0))
  }
  if(boundary[0]!==boundary.at(-1))throw new Error(`Open boundary ${source.id}`)
  boundary.pop()
  const polygon=boundary.map(id=>points[id])
  const constraints=boundary.map((id,i)=>[id,boundary[(i+1)%boundary.length]])
  const xs=polygon.map(p=>p[0]),ys=polygon.map(p=>p[1]),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys)
  const rowHeight=spacingMM*Math.sqrt(3)/2
  for(let row=0,y=minY+rowHeight/2;y<maxY;row++,y+=rowHeight){
   for(let x=minX+spacingMM/2+(row%2)*spacingMM/2;x<maxX;x+=spacingMM){
    const point=[x,y]
    if(!pointInPolygon(point,polygon))continue
    if(constraints.some(([a,b])=>segmentDistance(point,points[a],points[b])<spacingMM*0.28))continue
    add(point)
   }
  }
  const faces=cdt2d(points,constraints,{exterior:false,interior:true,delaunay:true})
  if(!faces.length)throw new Error(`No triangles ${source.id}`)
  restXY.push(...points);panelOfVertex.push(...points.map(()=>source.id))
  const firstTriangle=triangles.length
  triangles.push(...faces.map(face=>{
   const f=signedArea(face.map(id=>points[id]))<0?[face[0],face[2],face[1]]:face
   return f.map(id=>id+offset)
  }))
  const mappedLabels=Object.fromEntries(Object.entries(labels).map(([id,e])=>[id,{...e,vertexIds:e.vertexIds.map(i=>i+offset)}]))
  panels.push({id:source.id,vertexIds:points.map((_,i)=>i+offset),boundaryVertexIds:boundary.map(i=>i+offset),boundaryConstraints:constraints.map(e=>e.map(i=>i+offset)),pathLabels:mappedLabels,triangleRange:[firstTriangle,triangles.length],sourceAreaMM2:source.areaMM2,boundaryAreaMM2:Math.abs(signedArea(polygon)),sourcePart:source.sourcePart,sourcePath:source.sourcePath,outlineRole:source.outlineRole,unit:'mm'})
 }
 const seams=draft.seams.map(seam=>{
  const chain=side=>{const ids=panels.find(p=>p.id===side.panel).pathLabels[side.edge].vertexIds;return side.direction===1?ids:[...ids].reverse()}
  const a=chain(seam.a),b=chain(seam.b)
  if(a.length!==b.length)throw new Error(`Seam vertex mismatch ${seam.id}`)
  return {...seam,pairs:a.map((id,i)=>[id,b[i]]),t:a.map((_,i)=>i/(a.length-1)),aVertexIds:a,bVertexIds:b}
 })
 return {restXY,triangles,panelOfVertex,panels,seams,restUVperCorner:triangles.map(face=>face.map(id=>[...restXY[id]])),provenance:{mesher:'cdt2d',method:'constrained Delaunay with interior triangular lattice',spacingMM,boundarySpacingMM,restUVUnit:'mm',source:draft.provenance,placement:'NONE',physics:'NONE'}}
}
