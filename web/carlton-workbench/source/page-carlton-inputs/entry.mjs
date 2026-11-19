import { Carlton } from '@freesewing/carlton'
import { plugin as theme } from '@freesewing/plugin-theme'
import source from './standard-m.json'
import * as labels from './labels.mjs'

const root = document.getElementById('carlton-input-explorer')
const linked = root.hasAttribute('data-physics')
const by = selector => root.querySelector(selector)
const html = (tag, className, content='') => {
  const node = document.createElement(tag)
  if (className) node.className = className
  node.textContent = content
  return node
}
const svgNode = (tag, attrs) => {
  const node = document.createElementNS('http://www.w3.org/2000/svg',tag)
  for (const [key,value] of Object.entries(attrs)) node.setAttribute(key,value)
  return node
}
const config = Carlton.patternConfig
const groups = [
  ['body','围度与肩线'],['bodyLength','躯干长度'],['arm','手臂尺寸'],
  ['fit','合体'],['armhole','袖窿'],['style','外观'],['collar','领子'],
  ['sleeve','袖子'],['pocket','贴袋'],['otherPockets','胸袋与内袋'],['output','出样'],
]
const filters = {
  arm: new Set(['shoulderToElbow','shoulderToWrist','wrist']),
  torso: new Set(['hpsToBust','hpsToWaistBack','waistToArmpit','waistToHips','waistToFloor','waistToSeat']),
  armhole: new Set(['armholeDepth','armholeDepthFactor','frontArmholeDeeper','legacyArmholeDepth']),
  sleeve: new Set(['bicepsEase','cuffEase','sleeveLengthBonus','sleeveBend','sleevecapHeight','sleevecapEase','cuffLength']),
  style: new Set(['s3Collar','s3Armhole','buttonSpacingHorizontal','length','lapelReduction','frontOverlap','beltWidth']),
}
const notes = {
  highBust:'打开「用上胸围打版」后，上胸围才用于相关运算。',
  draftForHighBust:'开启后会使用上胸围。',
  armholeDepth:'采用新版袖窿规则时生效。',
  armholeDepthFactor:'打开「采用旧版袖窿深度」后生效。',
  coatLength:'从前片高肩点垂直量到下摆，可直接输入毫米。',
  sa:'缝份属于 FreeSewing 出样设置。',
}
const detailPaths = ['rollLine','pocket','pocketFlap','chestPocket','innerPocket',
  'fold','cuff','dart','backStay','triangle','folds','foldEdge','welt','hint','flb','chestPiece']
const panels = new Map(), controls = new Map(), tiles = new Map()
const status = by('[data-status]')
const reset = by('[data-reset]')
const models = Object.keys(labels.pieces)
let settings = baselineSettings()
let selected = null
let pending = 0
let gesture
let original
let valid
let affected = new Set()
let validSettings = baselineSettings()
let showFull = linked
let cachedSvg = null
let validDraft
let gestureLength
const frontLength = pattern => {
  const {cfHem,hps,s3CollarSplit}=pattern.parts[0]['carlton.front'].points
  return cfHem.y-(hps??s3CollarSplit).y
}
function requestSimulation(){
  if(!linked||!validDraft)return
  root.dispatchEvent(new CustomEvent('carlton-draft',{detail:{
    pattern:validDraft,chest:validSettings.measurements.chest,length:Number(frontLength(validDraft).toFixed(2)),
  }}))
}

function baselineSettings() {
  return {measurements:{...source.measurements}, options:{}, sa:0}
}
function copySettings(input) {
  return {measurements:{...input.measurements},options:{...input.options},sa:input.sa}
}
function read(settings,item) {
  if (item.type==='garment') return Number(frontLength(validDraft).toFixed(2))
  if (item.type==='settings') return settings.sa
  const val=settings[item.type][item.key]
  if (val==null) return item.base
  if (item.toggle) return Number(val)
  return item.unit==='%' ? Math.round(val*1000)/10 : val
}
function set(settings,item,value) {
  if (item.type==='garment'){
    const ratio=(validSettings.options.length??config.options.length.pct/100)
    const desired=ratio+(value-frontLength(validDraft))/validSettings.measurements.waistToFloor
    settings.options.length=desired
    gestureLength=value
  } else if (item.type==='settings') settings.sa=value
  else settings[item.type][item.key]=item.toggle ? Boolean(value) : item.unit==='%' ? value/100 : value
}
const format = (item,value) => item.toggle ? (value?'开':'关') : value+item.unit

function snapshot(input) {
  const d=new Carlton({...source,...input,layout:false}).draft()
  if(d.setStores[0].logs.error.length) throw Error('draft')
  const pieces=Object.fromEntries(models.map(key=>{
    const part=d.parts[0]['carlton.'+key]
    const paths={}
    for (const name of ['seam','sa',...detailPaths]) {
      const path=part.paths[name]
      if (!path || path.hidden) continue
      const value=path.asPathstring()
      if(!value || /NaN|Infinity|undefined/.test(value)) throw Error('path')
      paths[name]=value
    }
    const box=(part.paths.sa??part.paths.seam).bbox()
    const {topLeft:a,bottomRight:b}=box
    const bounds=[a.x,a.y,b.x,b.y]
    if(!paths.seam || !bounds.every(Number.isFinite) || b.x<=a.x || b.y<=a.y) throw Error('bounds')
    const marks=Object.entries(part.snippets).flatMap(([name,s])=>{
      if(!/button|notch|snap/i.test(name)||!Number.isFinite(s.anchor?.x)||!Number.isFinite(s.anchor?.y)) return []
      return [[name,+s.anchor.x.toFixed(2),+s.anchor.y.toFixed(2)]]
    })
    return [key,{paths,marks,bounds,signature:JSON.stringify([paths,marks])}]
  }))
  return {pieces,draft:d}
}

function fitView(pieces) {
  const x=Math.min(...pieces.map(p=>p.bounds[0]))
  const y=Math.min(...pieces.map(p=>p.bounds[1]))
  const width=Math.max(...pieces.map(p=>p.bounds[2]))-x
  const height=Math.max(...pieces.map(p=>p.bounds[3]))-y
  const pad=Math.max(width,height)*.07
  return [x-pad,y-pad,width+2*pad,height+2*pad].join(' ')
}

function refreshTiles() {
  for(const [key,{button,icon,path}] of tiles) {
    const piece=valid[key]
    icon.setAttribute('viewBox',fitView([piece]))
    path.setAttribute('d',piece.paths.seam)
    button.classList.toggle('affected',affected.has(key))
    button.dataset.affected=String(affected.has(key))
    button.setAttribute('aria-label',labels.pieces[key]+(affected.has(key)?'（已变化）':''))
  }
}

function packedSvg() {
  if (!cachedSvg) cachedSvg = new Carlton({...source,...validSettings,layout:true}).use(theme).draft().render()
  return cachedSvg
}
function refreshFull() {
  const node = new DOMParser().parseFromString(packedSvg(),'image/svg+xml').documentElement
  if(node.localName!=='svg') throw Error('SVG')
  node.setAttribute('role','img')
  node.setAttribute('aria-label','Carlton 完整 2D 纸样')
  by('[data-full]').replaceChildren(node)
}
function downloadFull() {
  const file=URL.createObjectURL(new Blob([packedSvg()],{type:'image/svg+xml'}))
  const link=html('a')
  link.href=file
  link.download='Carlton-当前纸样.svg'
  link.click()
  setTimeout(()=>URL.revokeObjectURL(file),1000)
}

function refreshDetail() {
  by('[data-detail]').hidden=showFull||!selected
  by('[data-tiles]').hidden=showFull||Boolean(selected)
  by('[data-full]').hidden=!showFull
  by('[data-atlas-title]').textContent=showFull?'完整 2D SVG':selected?labels.pieces[selected]:'全部 20 块裁片'
  by('[data-back]').hidden=!selected
  const button=by('[data-show-full]')
  button.setAttribute('aria-pressed',String(showFull))
  button.textContent=showFull?'返回裁片总览':'完整 2D SVG'
  if(showFull) { refreshFull(); return }
  if(!selected) return
  const svg=by('[data-piece-plot]')
  const baseline=original[selected]
  const piece=valid[selected]
  svg.setAttribute('viewBox',fitView([baseline,piece]))
  svg.setAttribute('aria-label',labels.pieces[selected]+'基准和当前纸样叠图')
  const paths=[svgNode('path',{d:baseline.paths.seam,class:'before',fill:'none'})]
  for(const [name,value] of Object.entries(piece.paths)) {
    paths.push(svgNode('path',{d:value,class:name==='seam'?'after':name==='sa'?'sa':'detail',fill:'none'}))
  }
  for(const [,x,y] of piece.marks) paths.push(svgNode('circle',{cx:x,cy:y,r:Math.max(piece.bounds[2]-piece.bounds[0],piece.bounds[3]-piece.bounds[1])*.003,class:'mark'}))
  svg.replaceChildren(...paths)
}

function reflectInputs() {
  for(const {item,range,numeric} of controls.values()) {
    const value=read(settings,item)
    range.value=value
    numeric.value=value
    range.setAttribute('aria-valuetext',format(item,value))
  }
}

function queueDraft() {
  cancelAnimationFrame(pending)
  pending=requestAnimationFrame(()=>{
    try {
      let {pieces:next,draft}=snapshot(settings)
      if(gestureLength!=null){
        const remainder=gestureLength-frontLength(draft)
        if(Math.abs(remainder)>0.005){
          settings.options.length+=remainder/settings.measurements.waistToFloor
          const adjusted=snapshot(settings)
          next=adjusted.pieces
          draft=adjusted.draft
        }
      }
      const item=gesture?.item
      const before=gesture?.before ?? original
      affected=new Set(models.filter(key=>next[key].signature!==before[key].signature))
      valid=next
      validDraft=draft
      if(linked){
        const currentLength=controls.get('coatLength')
        currentLength.range.value=Number(frontLength(draft).toFixed(2))
        if(gestureLength==null)currentLength.numeric.value=currentLength.range.value
        const percentage=controls.get('length')
        if(gestureLength!=null){
          percentage.range.value=percentage.numeric.value=read(settings,percentage.item)
          gestureLength=undefined
        }
      }
      validSettings=copySettings(settings)
      cachedSvg=null
      status.classList.remove('text-destructive')
      status.textContent=item?item.label+' · '+affected.size+' 块裁片变化':'拖动滑块查看受影响裁片'
      status.dataset.count=affected.size
      root.dataset.ready='true'
      refreshTiles()
      refreshDetail()
      requestSimulation()
    } catch {
      status.classList.add('text-destructive')
      status.textContent='当前组合无法出样，画布保留最近一次有效版。'
      status.dataset.count=''
      root.dataset.ready='false'
      gestureLength=undefined
      if(linked)root.dispatchEvent(new Event('carlton-invalid'))
    }
  })
}
function begin(item) {
  const baseline=copySettings(settings)
  let before=valid
  try { before=snapshot(baseline).pieces } catch {}
  gesture={item,before}
}

function add(group,item) {
  const cell=html('div','slider-field')
  const id='carlton-slider-'+item.key
  const header=html('div','slider-head')
  const label=html('label','slider-label',item.label)
  label.htmlFor=id
  const valueField=html('span','slider-value')
  const numeric=html('input','value-field')
  Object.assign(numeric,{type:'number',min:item.min,max:item.max,step:item.step})
  numeric.inputMode=item.step<1?'decimal':'numeric'
  numeric.setAttribute('aria-label',item.label+' 数值'+(item.unit?' '+item.unit.trim():''))
  numeric.dataset.valueKey=item.key
  const valueLabel=html('span','value-unit',item.toggle?'关／开':item.unit.trim())
  valueField.append(numeric,valueLabel)
  header.append(label,valueField)

  const range=html('input','form-range')
  Object.assign(range,{id,type:'range',min:item.min,max:item.max,step:item.step})
  const hint=notes[item.key]
  if(hint) label.setAttribute('data-tooltip',hint)
  range.dataset.key=item.key
  cell.append(header,range)
  panels.get(group).append(cell)
  controls.set(item.key,{item,range,numeric})

  function update(value,fromRange=false) {
    if(gesture?.item!==item) begin(item)
    set(settings,item,value)
    if(fromRange) numeric.value=value
    else range.value=value
    range.setAttribute('aria-valuetext',format(item,value))
    by('[data-hint]').textContent=hint??''
    queueDraft()
  }
  for(const control of [range,numeric]) control.addEventListener('focus',()=>{
    if(gesture?.item!==item) begin(item)
    by('[data-hint]').textContent=hint??''
  })
  range.addEventListener('pointerdown',()=>begin(item))
  range.addEventListener('input',()=>update(range.valueAsNumber,true))
  numeric.addEventListener('input',()=>{
    if(numeric.value!==''&&numeric.validity.valid) update(numeric.valueAsNumber)
  })
  numeric.addEventListener('change',()=>{
    if(numeric.value===''||!numeric.validity.valid) {
      numeric.value=read(settings,item)
      by('[data-hint]').textContent='请使用 '+item.min+' 到 '+item.max+item.unit+' 范围内的数值。'
    }
  })
}

for(const [key,title] of groups){
  const section=html('section','slider-section')
  const heading=html('h3','section-label',title)
  const panel=html('div','slider-grid');panel.dataset.group=key
  section.append(heading,panel)
  by('[data-group-panels]').append(section)
  panels.set(key,panel)
}
if(linked)panels.set('key',by('[data-key-inputs]'))
for(const key of [...config.measurements,...config.optionalMeasurements]){
  const base=source.measurements[key]
  const angle=key==='shoulderSlope'
  const group=linked&&key==='chest'?'key':filters.arm.has(key)?'arm':filters.torso.has(key)?'bodyLength':'body'
  add(group,{key,type:'measurements',base,label:labels.measurements[key]??key,
    min:angle?0:Math.floor(base*.85),max:angle?36:Math.ceil(base*1.15),
    unit:angle?'°':' mm',step:1})
}
for(const [key,opt] of Object.entries(config.options)){
  if(typeof opt!=='object'||opt===null)continue
  const toggle='bool' in opt
  const base=toggle?Number(opt.bool):opt.pct??opt.deg
  const group=opt.menu==='pockets'?(key.startsWith('chestPocket')||key.startsWith('innerPocket')?'otherPockets':'pocket'):
    opt.menu==='collar'?'collar':filters.sleeve.has(key)?'sleeve':filters.style.has(key)?'style':filters.armhole.has(key)?'armhole':'fit'
  add(group,{key,type:'options',label:labels.options[key]??key,toggle,base,
    min:toggle?0:opt.min,max:toggle?1:opt.max,
    step:[base,opt.min,opt.max].some(n=>Number.isFinite(n)&&n%1!==0) ? 0.1 : 1,
    unit:'pct' in opt?'%':'deg' in opt?'°':''})
}
if(linked)add('key',{key:'coatLength',type:'garment',label:'前片衣长',min:950,max:1900,step:.01,unit:' mm'})
add('output',{key:'sa',type:'settings',label:'缝份',base:0,min:0,max:25,step:1,unit:' mm'})

for(const key of models) {
  const button=html('button','piece-btn');button.type='button';button.dataset.piece=key
  const icon=svgNode('svg',{'aria-hidden':'true'})
  const path=svgNode('path',{fill:'none'});icon.append(path)
  button.append(icon,html('span','piece-label',labels.pieces[key]))
  by('[data-tiles]').append(button)
  tiles.set(key,{button,icon,path})
  button.addEventListener('click',()=>{selected=key;refreshDetail();by('[data-back]').focus()})
}
by('[data-show-full]').addEventListener('click',()=>{
  showFull=!showFull
  if(showFull) selected=null
  refreshDetail()
})
by('[data-download-full]').addEventListener('click',downloadFull)
by('[data-back]').addEventListener('click',()=>{
  const old=selected;selected=null;refreshDetail();tiles.get(old).button.focus()
})
reset.addEventListener('click',()=>{
  settings=baselineSettings();gesture=undefined;gestureLength=undefined
  by('[data-hint]').textContent=''
  queueDraft();
  if(linked)requestAnimationFrame(reflectInputs)
  else reflectInputs()
})
const initial=snapshot(settings)
original=valid=initial.pieces
validDraft=initial.draft
reflectInputs()
queueDraft()
