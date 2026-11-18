import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import { cisFemaleAdult38 } from './package/src/index.mjs'
import { makeDraft,signedArea } from './adapter.mjs'
import { makeMesh,pointInPolygon } from './mesh.mjs'
const draft=makeDraft({mode:'ENGINE_CONFORMANCE',measurements:cisFemaleAdult38,options:{fitWaist:true}})
const mesh=makeMesh(draft,{spacingMM:24})
const edgeKey=(a,b)=>a<b?`${a}/${b}`:`${b}/${a}`
const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
const properCross=(a,b,c,d)=>cross(a,b,c)*cross(a,b,d)<-1e-12&&cross(c,d,a)*cross(c,d,b)<-1e-12
const result=[]
const used=new Set(mesh.triangles.flat())
assert.equal(used.size,mesh.restXY.length,'no orphan particles')
assert(mesh.restXY.length>=700&&mesh.restXY.length<=2000,'default target particle range')
assert.equal(mesh.seams.length,10)
assert.deepEqual(mesh.restUVperCorner,mesh.triangles.map(face=>face.map(id=>mesh.restXY[id])),'corner UVs preserve material rest coordinates')
for(const panel of mesh.panels){
 const polygon=panel.boundaryVertexIds.map(i=>mesh.restXY[i])
 const faces=mesh.triangles.slice(...panel.triangleRange)
 const triangleEdges=new Set()
 let area=0,crossings=0
 for(const face of faces){
  const xy=face.map(i=>mesh.restXY[i])
  const a=signedArea(xy)
  assert(a>1e-8,'positive nondegenerate face')
  area+=a
  assert(face.every(id=>mesh.panelOfVertex[id]===panel.id),'triangles stay in panel')
  const centroid=[0,1].map(axis=>xy.reduce((sum,p)=>sum+p[axis],0)/3)
  assert(pointInPolygon(centroid,polygon),'triangle centroid lies inside panel')
  for(let i=0;i<3;i++){
   const a=face[i],b=face[(i+1)%3]
   triangleEdges.add(edgeKey(a,b))
   for(const [c,d]of panel.boundaryConstraints)if(properCross(mesh.restXY[a],mesh.restXY[b],mesh.restXY[c],mesh.restXY[d]))crossings++
  }
 }
 assert.equal(crossings,0,'triangle edges do not cross constrained boundary')
 assert(panel.boundaryConstraints.every(([a,b])=>triangleEdges.has(edgeKey(a,b))),'all boundary constraints appear in mesh')
 assert(Math.abs(area-panel.boundaryAreaMM2)<0.0001,'triangles cover boundary polygon exactly')
 const sourceAreaError=Math.abs(area-panel.sourceAreaMM2)/panel.sourceAreaMM2
 assert(sourceAreaError<0.005,'mesh approximates native seam area within 0.5%')
 result.push({id:panel.id,particles:panel.vertexIds.length,triangles:faces.length,sourceAreaMM2:panel.sourceAreaMM2,boundaryAreaMM2:panel.boundaryAreaMM2,coveredAreaMM2:area,relativeSourceAreaError:sourceAreaError,boundaryCrossings:crossings,allConstraintsPresent:true})
}
const seamChecks=mesh.seams.map(seam=>{
 assert(seam.pairs.length>=2)
 assert.equal(seam.aVertexIds.length,seam.bVertexIds.length)
 const roles=side=>{const r=mesh.panels.find(p=>p.id===side.panel).pathLabels[side.edge].endpointRoles;return side.direction===1?r:[...r].reverse()}
 assert.deepEqual(roles(seam.a),roles(seam.b),'seam semantic endpoint directions agree')
 for(const [a,b]of seam.pairs){
  assert(mesh.panels.find(p=>p.id===seam.a.panel).boundaryVertexIds.includes(a))
  assert(mesh.panels.find(p=>p.id===seam.b.panel).boundaryVertexIds.includes(b))
 }
 assert.equal(seam.t[0],0);assert.equal(seam.t.at(-1),1)
 return {id:seam.id,pairs:seam.pairs.length,endpointRoles:seam.endpointRoles,equalT:true,boundaryOnly:true}
})
const finer=makeMesh(draft,{spacingMM:20})
assert(finer.restXY.length>mesh.restXY.length,'spacing change increases particle resolution')
const report={status:'PASS',particles:mesh.restXY.length,triangles:mesh.triangles.length,spacingMM:24,finerSpacingMM:20,finerParticles:finer.restXY.length,panels:result,seams:seamChecks,restUVUnit:'mm',placement:'NONE',physics:'NONE'}
writeFileSync('probes/pattern/base-mesh.json',JSON.stringify(mesh,null,2))
writeFileSync('probes/pattern/mesh-conformance-result.json',JSON.stringify(report,null,2))
console.log(JSON.stringify(report,null,2))
