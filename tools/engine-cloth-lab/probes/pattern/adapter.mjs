import { Teagan } from '@freesewing/teagan'
import { Path } from '@freesewing/core'

const VERSION = '4.10.2'
const xy = p => [p.x, p.y]
const mirror = (p, sign) => [p[0] * sign, p[1]]
const distance = (a,b) => Math.hypot(a[0]-b[0],a[1]-b[1])
export const signedArea = pts => pts.reduce((a,p,i) => {const q=pts[(i+1)%pts.length];return a+p[0]*q[1]-q[0]*p[1]},0)/2
const line = (a,b) => new Path().move(a).line(b)
const armhole = p => new Path().move(p.armhole).curve(p.armholeCp2,p.armholeHollowCp1,p.armholeHollow).curve(p.armholeHollowCp2,p.shoulderCp1,p.shoulder)
const sample = (path, step=3) => {
 const n=Math.max(1,Math.ceil(path.length()/step))
 const first=path.ops.find(op=>op.type==='move').to
 const last=path.ops.at(-1).type==='close'?first:[...path.ops].reverse().find(op=>op.to).to
 return Array.from({length:n+1},(_,i)=>xy(i===0?first:i===n?last:path.shiftFractionAlong(i/n)))
}
const serialize = path => path.ops.map(op => Object.fromEntries(Object.entries(op).map(([key,val])=>[key,['to','cp1','cp2'].includes(key)?xy(val):val])))
const edge = (id,path,sign=1,step=3) => ({id, samplesMM:sample(path,step).map(p=>mirror(p,sign)),lengthMM:path.length(),nativeOps:serialize(path),mirrorX:sign<0})
const endpointRoles={hem:['centerHem','hem'],side:['underarm','hem'],armhole:['shoulder','underarm'],shoulder:['neck','shoulder'],neck:['neck','centerNeck'],'underarm.front':['underarm','cuff'],'underarm.back':['underarm','cuff'],'cap.front':['underarm','shoulder'],'cap.back':['underarm','shoulder']}
function panel(id, edges, outlineEdges, nativePart, nativePath) {
 const outlineMM=[]
 const labels=Object.fromEntries(edges.map(e=>[e.id,{...e,endpointRoles:endpointRoles[e.id]??endpointRoles[e.id.split('.').at(-1)]}]))
 for(const [name,reverse] of outlineEdges){
  const points=reverse?[...labels[name].samplesMM].reverse():labels[name].samplesMM
  if(outlineMM.length && distance(outlineMM.at(-1),points[0])>0.01) throw new Error(`Boundary gap in ${id}/${name}: ${JSON.stringify([outlineMM.at(-1),points[0]])}`)
  outlineMM.push(...points.slice(outlineMM.length?1:0))
 }
 if(distance(outlineMM[0],outlineMM.at(-1))>0.01)throw new Error(`Unclosed ${id}`)
 outlineMM.pop()
 if(Math.abs(signedArea(outlineMM))<1)throw new Error(`Zero-area ${id}`)
 return {id,outlineMM,pathLabels:labels,boundaryOrder:outlineEdges.map(([edge,reverse])=>({edge,direction:reverse?-1:1})),sourcePart:nativePart,sourcePath:'seam',sourceNativeOps:serialize(nativePath),sourceNativeAreaMM2:Math.abs(signedArea(sample(nativePath))),areaMM2:Math.abs(signedArea(outlineMM)),outlineRole:'NET_SEAMLINE',unit:'mm'}
}
function body(part, id, step){
 const p=part.points
 const center=id==='front'?p.cfNeck:p.cbNeck
 const neck=new Path().move(p.neck).curve(p.neckCp2,id==='front'?p.cfNeckCp1:p.cbNeckCp1,center)
 const paths={hem:part.paths.hemBase,side:part.paths.sideSeam.reverse(),armhole:armhole(p).reverse(),shoulder:line(p.neck,p.shoulder),neck}
 const edges=[]
 for(const side of ['left','right'])for(const [name,path]of Object.entries(paths))edges.push(edge(`${side}.${name}`,path,side==='left'?-1:1,step))
 return panel(id,edges,[['left.hem',false],['left.side',true],['left.armhole',true],['left.shoulder',true],['left.neck',false],['right.neck',true],['right.shoulder',false],['right.armhole',false],['right.side',false],['right.hem',true]],part.name??`teagan.${id}`,part.paths.seam)
}
function sleeve(part,id,sign,frontArmholeLength,step){
 const p=part.points
 const cap=part.paths.sleevecap
 const split=cap.split(cap.shiftAlong(frontArmholeLength))
 if(!split[0]||!split[1])throw new Error('Invalid sleeve cap division')
 const edges=[edge('hem',part.paths.hemBase,sign,step),edge('underarm.front',line(p.bicepsRight,p.hemRight),sign,step),edge('underarm.back',line(p.bicepsLeft,p.hemLeft),sign,step),edge('cap.front',split[0],sign,step),edge('cap.back',split[1].reverse(),sign,step)]
 return panel(id,edges,[['hem',false],['underarm.front',true],['cap.front',false],['cap.back',true],['underarm.back',false]],'teagan.sleeve',part.paths.seam)
}
function svgFor(panels){
 let x=0;let h=0;const groups=[]
 for(const p of panels){
  const xs=p.outlineMM.map(p=>p[0]),ys=p.outlineMM.map(p=>p[1]);const minX=Math.min(...xs),minY=Math.min(...ys),w=Math.max(...xs)-minX,height=Math.max(...ys)-minY
  groups.push(`<g transform="translate(${x-minX+10},${10-minY})"><path fill="#e3dfd1" stroke="#292720" stroke-width="1" d="M ${p.outlineMM.map(p=>p.join(',')).join(' L ')} Z"/><text x="${minX+w/2}" y="${minY+height/2}" text-anchor="middle" font-size="13">${p.id}</text></g>`)
  x+=w+20;h=Math.max(h,height+20)
 }
 return `<svg xmlns="http://www.w3.org/2000/svg" width="${x}mm" height="${h}mm" viewBox="0 0 ${x} ${h}">${groups.join('')}</svg>`
}
export function makeDraft(input={}){
 const provenance={engine:'FreeSewing Teagan',version:VERSION,mode:input.mode??'GOLDEN_SOURCE',goldenEquivalence:'NOT_VALIDATED',canonicalUnitScale:'UNKNOWN',nativeCapabilities:{bodyOnFold:true,sleeve:'SHORT_SLEEVE',neckband:false},sourceLinks:['https://www.npmjs.com/package/@freesewing/teagan/v/4.10.2','https://codeberg.org/freesewing/freesewing'],parameters:{measurements:input.measurements??null,options:input.options??{}}}
 const measurements=input.measurements
 const required=Teagan.patternConfig.measurements
 const unknown=required.filter(name=>!Number.isFinite(measurements?.[name])||measurements[name]<=0)
 if(input.mode!=='ENGINE_CONFORMANCE' && !input.approvedMeasurementMapping)return {status:'UNKNOWN',panels:[],seams:[],svg:null,provenance,measurementSources:input.measurementSources??{},missing:unknown,reason:'Canonical U/mm, net/cut role, and human measurements are unapproved. No implicit model defaults.'}
 if(unknown.length)return {status:'UNKNOWN',panels:[],seams:[],svg:null,provenance,measurementSources:input.measurementSources??{},missing:unknown,reason:'Required engine measurements are missing.'}
 const options={...input.options}
 const pattern=new Teagan({measurements,options,sa:0,complete:false}).draft()
 const parts=pattern.parts[0]
 for(const name of ['front','back','sleeve'])if(!parts[`teagan.${name}`]?.paths?.seam)throw new Error(`Native draft missing ${name}`)
 const step=input.sampleStepMM??3
 const front=parts['teagan.front'],back=parts['teagan.back'],s=parts['teagan.sleeve']
 const frontLength=armhole(front.points).length()
 const panels=[body(front,'front',step),body(back,'back',step),sleeve(s,'sleeve-left',1,frontLength,step),sleeve(s,'sleeve-right',-1,frontLength,step)]
 const seams=[]
 const bind=(id,aPanel,aEdge,bPanel,bEdge)=>{
  const a=panels.find(p=>p.id===aPanel).pathLabels[aEdge],b=panels.find(p=>p.id===bPanel).pathLabels[bEdge]
  seams.push({id,a:{panel:aPanel,edge:aEdge,direction:1},b:{panel:bPanel,edge:bEdge,direction:1},pairingDirection:'SAME_SEMANTIC_ENDPOINT_ORDER',lengthAMM:a.lengthMM,lengthBMM:b.lengthMM,deltaMM:b.lengthMM-a.lengthMM,physicalApproval:input.mode==='ENGINE_CONFORMANCE'?'ENGINE_CONFORMANCE_ONLY':'NOT_VALIDATED'})
 }
 for(const side of ['left','right']){
  bind(`shoulder.${side}`,'front',`${side}.shoulder`,'back',`${side}.shoulder`)
  bind(`side.${side}`,'front',`${side}.side`,'back',`${side}.side`)
  bind(`armhole.${side}.front`,'front',`${side}.armhole`,`sleeve-${side}`,'cap.front')
  bind(`armhole.${side}.back`,'back',`${side}.armhole`,`sleeve-${side}`,'cap.back')
  bind(`underarm.${side}`,`sleeve-${side}`,'underarm.front',`sleeve-${side}`,'underarm.back')
 }
 // Body armholes run shoulder-to-underarm; sleeve cap chains run underarm-to-shoulder.
 for(const seam of seams.filter(s=>s.id.startsWith('armhole.')))seam.b.direction=-1
 for(const seam of seams){
  const ends=side=>{const roles=panels.find(p=>p.id===side.panel).pathLabels[side.edge].endpointRoles;return side.direction===1?roles:[...roles].reverse()}
  if(JSON.stringify(ends(seam.a))!==JSON.stringify(ends(seam.b)))throw new Error(`Endpoint direction mismatch ${seam.id}`)
  seam.endpointRoles=ends(seam.a)
 }
 return {status:'DRAFTED',panels,seams,svg:svgFor(panels),provenance,measurementSources:input.measurementSources??{},nativeParameters:{requiredMeasurements:required,options},validation:{sourceAreasNonZero:panels.every(p=>p.areaMM2>0),goldenCadEquivalence:false,neckbandMissing:true,longSleeveSupported:false,sleevecapResidualMM:s.paths.sleevecap.length()-armhole(front.points).length()-armhole(back.points).length()}}
}
