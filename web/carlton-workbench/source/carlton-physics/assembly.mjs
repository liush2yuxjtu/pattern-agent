import { originalOutline, baselineDraft } from './pattern.mjs'
import { interpolate, onSurface } from './mounts.mjs'

export const decode = text => Uint8Array.from(atob(text),c=>c.charCodeAt(0)).buffer

function bounds(points) {
  const x=points.map(p=>p[0]), y=points.map(p=>p[1])
  return [Math.min(...x),Math.max(...x),Math.min(...y),Math.max(...y)]
}

function segments(points) {
  return points.slice(1).map(([x,y],i)=>{
    const [ax,ay]=points[i], dx=x-ax,dy=y-ay
    return {i,x:ax,y:ay,dx,dy,length:Math.hypot(dx,dy)}
  }).filter(s=>s.length>0.0001)
}

function project([x,y],s) {
  const t=Math.max(0,Math.min(1,((x-s.x)*s.dx+(y-s.y)*s.dy)/s.length**2))
  return {i:s.i,t,d:Math.hypot(x-s.x-t*s.dx,y-s.y-t*s.dy)}
}

function boundaryVertices(faces) {
  const edges=new Map()
  for(let i=0;i<faces.length;i+=3)for(let j=0;j<3;j++){
    const a=faces[i+j],b=faces[i+(j+1)%3],key=Math.min(a,b)+':'+Math.max(a,b)
    if(edges.has(key))edges.delete(key)
    else edges.set(key,[a,b])
  }
  return new Set([...edges.values()].flat())
}

function buildPanel(range,uv,edge) {
  const {part,offset,count}=range
  const flat=Array.from({length:count},(_,i)=>Array.from(uv.subarray(2*(offset+i),2*(offset+i)+2)))
  const original=originalOutline(part)
  const [x0,x1,y0,y1]=bounds(original)
  const [u0,u1,v0,v1]=bounds(flat)
  const edges=segments(original)
  const candidates=[]
  for(const signU of [1,-1])for(const signV of [1,-1]){
    const fold=part==='collar'
    const points=flat.map(([u,v])=>{
      const f=(u-u0)/(u1-u0),g=(v-v0)/(v1-v0)
      const folded=2*Math.abs(f-.5)
      return [
        x0+(x1-x0)*(signU===1?(fold?folded:f):(fold?1-folded:1-f)),
        y0+(y1-y0)*(signV===1?g:1-g),
      ]
    })
    let error=0
    for(let i=0;i<count;i++)if(edge.has(offset+i))error+=Math.min(...edges.map(s=>project(points[i],s).d))
    candidates.push({points,error,signU,signV,fold})
  }
  candidates.sort((a,b)=>a.error-b.error)
  const {points,signU,signV,fold}=candidates[0]
  const samples=points.map((point,j)=>{
    const all=edges.map(s=>({...project(point,s),length:s.length}))
    const nearest=all.reduce((a,b)=>a.d<b.d?a:b)
    const du=signU*(fold?Math.sign(flat[j][0]-(u0+u1)/2)||1:1)
    if(nearest.d<2)return {du,dv:signV,refs:[{...nearest,w:1}],sum:1}
    const refs=all.map(s=>({...s,w:Math.min(s.length,35)/(s.d**3)}))
    return {du,dv:signV,refs,sum:refs.reduce((s,r)=>s+r.w,0)}
  })
  return {
    ...range,original,samples,
    toDraft:([u,v])=>[signU===1?x0+1000*(u-u0):x1-1000*(u-u0),signV===1?y0+1000*(v-v0):y1-1000*(v-v0)],
    toUv:([x,y])=>[u0+(signU===1?x-x0:x1-x)*.001,v0+(signV===1?y-y0:y1-y)*.001],
  }
}

// Estimate the local 3D tangents of the reference fabric coordinates.
function tangents(position,uv,faces) {
  const derivatives=new Float64Array(3*position.length)
  for(let i=0;i<faces.length;i+=3){
    const a=faces[i],b=faces[i+1],c=faces[i+2]
    const u=uv[2*b]-uv[2*a], v=uv[2*b+1]-uv[2*a+1]
    const s=uv[2*c]-uv[2*a], t=uv[2*c+1]-uv[2*a+1]
    const det=u*t-s*v, weight=Math.abs(det)
    if(weight<1e-10)continue
    for(const id of [a,b,c]){
      const k=9*id
      for(let axis=0;axis<3;axis++){
        const p=position[3*b+axis]-position[3*a+axis]
        const q=position[3*c+axis]-position[3*a+axis]
        derivatives[k+axis]+=(t*p-v*q)*Math.sign(det)
        derivatives[k+3+axis]+=(u*q-s*p)*Math.sign(det)
      }
      derivatives[k+6]+=weight
    }
  }
  for(let k=0;k<derivatives.length;k+=9){
    const w=derivatives[k+6]
    for(const j of [0,3]){
      const m=Math.max(w,Math.hypot(...derivatives.subarray(k+j,k+j+3))/1.3,1e-10)
      for(let d=0;d<3;d++)derivatives[k+j+d]/=m
    }
  }
  return derivatives
}

export function makeAssembly(cloth,faces){
  const reference=new Float32Array(decode(cloth.position))
  const uv=new Float32Array(decode(cloth.uv))
  const boundary=boundaryVertices(faces)
  const panels=cloth.ranges.map(range=>buildPanel(range,uv,boundary))
  const gradient=tangents(reference,uv,faces)
  const findPanel=id=>panels.find(({offset,count})=>id>=offset&&id<offset+count)
  const hostFaces=new Map(panels.filter(panel=>panel.part==='front').map(panel=>[
    panel,faces.filter(id=>id>=panel.offset&&id<panel.offset+panel.count),
  ]))
  const trimDefinitions=cloth.trims.map(trim=>({...trim}))
  for(const kind of ['button','buttonhole'])for(const row of [1,2,3]){
    const pair=trimDefinitions.filter(trim=>trim.kind===kind&&trim.key.startsWith('button'+row))
    const draftX=({anchor})=>findPanel(anchor[0]).toDraft(interpolate(uv,anchor,2))[0]
    pair.sort((a,b)=>draftX(a)-draftX(b))
    pair[0].key='button'+row+'Left'
    pair[1].key='button'+row+'Right'
  }
  const pocketFrame=(points,prefix)=>{
    const {x,y}=points[prefix+'TopLeft']
    return {x,y,width:points[prefix+'TopRight'].x-x,height:points[prefix+'BottomLeft'].y-y}
  }
  function movedAnchor(originalAnchor,panel,flat,move){
    const point=interpolate(baselineFlat,originalAnchor,2)
    const target=panel.toUv(move(panel.toDraft(point)))
    if(Math.hypot(target[0]-point[0],target[1]-point[1])<1e-9&&flat.every((v,i)=>v===baselineFlat[i])){
      return {anchor:originalAnchor,point,distance:0}
    }
    return {...onSurface(target,flat,hostFaces.get(panel),2),point:target}
  }
  function deform(draft){
    const position=reference.slice()
    const flat=uv.slice()
    const changedPanels=[]
    for(const {part,name,offset,count,original,samples} of panels){
      const updated=draft.outline(part)
      if(updated.length!==original.length)throw Error(name+' 裁片的轮廓结构发生变化')
      const delta=updated.map(([x,y],i)=>[x-original[i][0],y-original[i][1]])
      if(delta.every(([x,y])=>Math.hypot(x,y)<0.001))continue
      changedPanels.push(name)
      for(let i=0;i<count;i++){
        const {du,dv,refs,sum}=samples[i]
        let x=0,y=0
        for(const {i:j,t,w} of refs){
          x+=w*((1-t)*delta[j][0]+t*delta[j+1][0])
          y+=w*((1-t)*delta[j][1]+t*delta[j+1][1])
        }
        x*=du*.001/sum
        y*=dv*.001/sum
        const k=i+offset
        flat[2*k]+=x
        flat[2*k+1]+=y
        for(let axis=0;axis<3;axis++)position[3*k+axis]+=x*gradient[9*k+axis]+y*gradient[9*k+3+axis]
      }
    }
    return {position,flat,changedPanels}
  }
  const baselineFlat=deform(baselineDraft).flat
  return function assemble(draft){
    const {position,flat,changedPanels}=deform(draft)
    const pocketMoves=new Map()
    let pocketProjectionMm=0
    const pockets=cloth.pockets.map(([id,...originalAnchor])=>{
      const piece=findPanel(id)
      const front=findPanel(originalAnchor[0])
      const before=pocketFrame(baselineDraft.front,piece.part)
      const after=pocketFrame(draft.front,piece.part)
      const hit=movedAnchor(originalAnchor,front,flat,([x,y])=>[
        after.x+(x-before.x)*after.width/before.width,
        after.y+(y-before.y)*after.height/before.height,
      ])
      pocketProjectionMm=Math.max(pocketProjectionMm,1000*hit.distance)
      const start=interpolate(position,originalAnchor,3)
      const end=interpolate(position,hit.anchor,3)
      const translation=end.map((v,i)=>v-start[i])
      if(!pocketMoves.has(piece))pocketMoves.set(piece,[])
      pocketMoves.get(piece).push(translation)
      return [id,...hit.anchor]
    })
    for(const [piece,moves] of pocketMoves){
      const mean=[0,1,2].map(axis=>moves.reduce((sum,m)=>sum+m[axis],0)/moves.length)
      if(Math.hypot(...mean)>.000001){
        if(!changedPanels.includes(piece.name))changedPanels.push(piece.name)
        for(let id=piece.offset;id<piece.offset+piece.count;id++){
          for(let axis=0;axis<3;axis++)position[3*id+axis]+=mean[axis]
        }
      }
    }
    const trims=trimDefinitions.map(trim=>{
      const from=baselineDraft.front[trim.key],to=draft.front[trim.key]
      const panel=findPanel(trim.anchor[0])
      const hit=movedAnchor(trim.anchor,panel,flat,([x,y])=>[x+to.x-from.x,y+to.y-from.y])
      return {...trim,anchor:hit.anchor,targetUv:hit.point,projectionMm:1000*hit.distance}
    })
    return {position,flat,changedPanels,pockets,trims,pocketProjectionMm}
  }
}

export function fingerprint(array){
  const bytes=new Uint8Array(array.buffer,array.byteOffset,array.byteLength)
  let hash=2166136261
  for(const byte of bytes)hash=Math.imul(hash^byte,16777619)
  return (hash>>>0).toString(16).padStart(8,'0')
}
