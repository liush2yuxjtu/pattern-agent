import * as T from 'three/webgpu'

const definitions={
  strain:{field:0,scale:100,upper:50,unit:'%',label:'最大主工程应变',note:'逐面按纸样净版计算。蓝灰表示零拉伸或压缩，红色表示达到色标上限。'},
  stress:{field:3,scale:0.001,upper:500,unit:'kPa',label:'最大主拉应力',note:'基于示例面料的 Cauchy 主应力。可比较热点，小面积三角面可出现数值尖峰，材料参数待实测标定。'},
  pressure:{scale:0.001,upper:0.3,unit:'kPa',label:'人台法向接触压力估算',note:'通过法向接触乘子和变形后受力面积换算。色标以上为饱和色，舒适性待实物标定。'},
}
const ramp=[0x203c57,0x23858e,0xe1cb59,0xcf433b].map(value=>new T.Color(value))

export function setupDiagnostics({coat,solver,get,onMode}){
  const panel=get('diagnostic-controls'),legend=get('diagnostic-legend')
  const buttons=[...panel.querySelectorAll('[data-diagnostic]')]
  const viewer=get('viewport')
  let mode='appearance',ready=false
  const shell=coat.geometry
  const shaded=coat.material
  const map=shell.toNonIndexed()
  const color=new T.BufferAttribute(new Float32Array(solver.faces.length*3),3)
  map.setAttribute('color',color)
  const material=new T.MeshBasicMaterial({side:T.DoubleSide,vertexColors:true})
  const tint=new T.Color()

  function paint(definition){
    const positions=solver.positions()
    const target=map.attributes.position.array
    const isPressure=mode==='pressure'
    const scalars=isPressure?solver.pressure():solver.fields()
    const rest=solver.rest()
    const samples=[]
    let max=0
    for(let i=0;i<solver.faces.length;i++){
      const vertex=solver.faces[i]
      for(let j=0;j<3;j++)target[3*i+j]=positions[3*vertex+j]
      const raw=mode==='pressure'?scalars[vertex]:scalars[8*Math.floor(i/3)+definition.field]
      const value=Math.max(0,raw*definition.scale)
      if(!Number.isFinite(value))throw Error('Non-finite diagnostic field')
      max=Math.max(max,value)
      if(!isPressure&&i%3===0){
        const a=vertex*2,b=solver.faces[i+1]*2,c=solver.faces[i+2]*2
        const weight=Math.abs((rest[b]-rest[a])*(rest[c+1]-rest[a+1])-(rest[c]-rest[a])*(rest[b+1]-rest[a+1]))
        samples.push([value,weight])
      }
      const p=Math.min(value/definition.upper,1)*(ramp.length-1)
      const j=Math.min(Math.floor(p),ramp.length-2)
      tint.copy(ramp[j]).lerp(ramp[j+1],p-j).toArray(color.array,3*i)
    }
    map.attributes.position.needsUpdate=color.needsUpdate=true
    Object.assign(viewer.dataset,{fieldMax:String(max),fieldSamples:String(scalars.length/(mode==='pressure'?1:8))})
    const label=isPressure?(' 本帧最大值 '+max.toFixed(3)+' kPa。'):(()=>{
      samples.sort((a,b)=>a[0]-b[0])
      const target=samples.reduce((sum,sample)=>sum+sample[1],0)*.95
      let accumulated=0
      const percentile=samples.find(sample=>(accumulated+=sample[1])>=target)[0]
      return ' 本帧面积加权 P95 '+percentile.toFixed(1)+' '+definition.unit+'。'
    })()
    get('diagnostic-caption').textContent=definition.note+label
    get('diagnostic-range').textContent='0 – '+definition.upper+' '+definition.unit
    get('diagnostic-name').textContent=definition.label
  }
  function render(){
    const definition=definitions[mode]
    const mapped=Boolean(definition&&ready)
    coat.geometry=mapped?map:shell
    coat.material=mapped?material:shaded
    legend.hidden=!definition
    get('diagnostic-scale').hidden=!mapped
    get('diagnostic-note').hidden=mode!=='line'
    if(mapped){
      paint(definition)
    }else{
      delete viewer.dataset.fieldMax
      delete viewer.dataset.fieldSamples
      get('diagnostic-caption').textContent='等待当前纸样的第 480 步结果。'
    }
    viewer.dataset.diagnostic=mode
    viewer.dataset.diagnosticReady=String(ready)
    for(const button of buttons)button.setAttribute('aria-pressed',String(button.dataset.diagnostic===mode))
    onMode(mode)
  }
  for(const button of buttons){
    button.disabled=false
    button.addEventListener('click',()=>{mode=button.dataset.diagnostic;render()})
  }
  return {shell,setReady(value){ready=value;render()}}
}
