import assert from 'node:assert/strict'
import {createHash} from 'node:crypto'
import {mkdir,readFile} from 'node:fs/promises'
import {createRequire} from 'node:module'
import {join} from 'node:path'

const require=createRequire(import.meta.url)
const {chromium}=require(process.env.PLAYWRIGHT_PACKAGE||'playwright')
const base=new URL(process.argv[2]||'http://127.0.0.1:8000/pattern-agent/carlton-workbench/')
const evidenceDir=process.env.CARLTON_BROWSER_EVIDENCE
if(evidenceDir)await mkdir(evidenceDir,{recursive:true})
const screenshot=(page,name)=>evidenceDir?page.screenshot({path:join(evidenceDir,name+'.png')}):null
const expectedCommit=process.argv[3]
const body=await readFile(new URL('evidence.tgz',import.meta.url))
const digest=bytes=>createHash('sha256').update(bytes).digest('hex')
const local=name=>readFile(new URL(name,import.meta.url))
const browser=await chromium.launch({
  headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE||undefined,
})
try{
  const context=await browser.newContext({viewport:{width:1320,height:900},acceptDownloads:true})
  await context.addInitScript(()=>{
    window.computeCalls=0
    if(!window.GPUComputePassEncoder)return
    const dispatch=GPUComputePassEncoder.prototype.dispatchWorkgroups
    GPUComputePassEncoder.prototype.dispatchWorkgroups=function(...args){
      window.computeCalls++
      return dispatch.apply(this,args)
    }
  })
  const page=await context.newPage()
  const errors=[]
  page.on('pageerror',error=>errors.push(error.message))
  page.on('console',message=>{if(message.type()==='error')errors.push(message.text())})
  const response=await page.goto(base.href)
  assert.equal(response.status(),200)
  assert.equal(digest(await response.body()),digest(await local('index.html')))
  assert.equal(await page.title(),'Carlton 打版与 3D 试穿')
  if(expectedCommit){
    const result=await context.request.get(new URL('../build.json',base).href)
    assert.equal(result.status(),200)
    const build=await result.json()
    assert.equal(build.commit,expectedCommit)
    for(const file of ['index.html','review.html','evidence.tgz','review-summary.json']){
      assert.equal(build.files['carlton-workbench/'+file],digest(await local(file)))
    }
  }
  const viewport=page.locator('#viewport')
  const svg=page.locator('[data-full] svg')
  const chest=page.locator('[data-value-key="chest"]')
  const length=page.locator('[data-value-key="coatLength"]')
  const readings=[]
  async function settle(chestMm,lengthMm){
    await page.waitForFunction(([chest,length])=>{
      const data=document.querySelector('#viewport').dataset
      return data.state==='error'||data.state==='unsupported-pattern'||
        (data.state==='complete'&&data.chest===chest&&data.length===length)
    },[chestMm,lengthMm],{timeout:120000})
    const data=await viewport.evaluate(node=>({...node.dataset}))
    assert.equal(data.state,'complete',await page.locator('#readout').textContent())
    assert.equal(data.backend,'webgpu')
    assert.equal(data.engine,'rust-wasm')
    assert.equal(data.integrator,'webgpu-compute')
    assert.equal(data.gpuSteps,'480')
    assert.equal(data.steps,'480')
    assert.equal(data.finite,'true')
    assert.equal(data.selfEnabled,'true')
    assert.ok(Number(data.selfTotal)>0)
    assert.ok(Number(data.pocketGap)<0.5)
    assert.ok(Number(data.dartGap)<2)
    assert.equal(await svg.locator('g[id*="-part-"]').count(),20)
    assert.equal(await viewport.locator('canvas').count(),1)
    const outline=digest((await svg.locator('g[id*="-part-"] path[d]').evaluateAll(
      paths=>paths.map(path=>path.getAttribute('d'))
    )).join(','))
    readings.push({...data,outline})
  }
  assert.equal(await page.locator('input[type="range"]').count(),62)
  await settle('1053','1302.96')
  await chest.fill('1083')
  await settle('1083','1302.96')
  await length.fill('1382.96')
  await settle('1083','1382.96')
  await page.getByRole('button',{name:'背面',exact:true}).click()
  await screenshot(page,'editor-back')
  await page.getByRole('button',{name:'恢复 M 码'}).click()
  await settle('1053','1302.96')
  for(const key of ['restHash','assemblyHash','resultHash','outline']){
    assert.equal(new Set(readings.slice(0,3).map(row=>row[key])).size,3,key)
    assert.equal(readings[0][key],readings[3][key],key)
  }
  assert.ok(await page.evaluate(()=>window.computeCalls)>=4*480)
  const svgPending=page.waitForEvent('download')
  await page.getByRole('button',{name:'下载 SVG'}).click()
  assert.match(await readFile(await (await svgPending).path(),'utf8'),/width="[\d.]+mm"/)
  const reviewPending=page.waitForNavigation()
  await page.getByRole('link',{name:'验收报告',exact:true}).click()
  const review=await reviewPending
  assert.equal(digest(await review.body()),digest(await local('review.html')))
  await page.locator('details summary').click()
  assert.deepEqual(await page.locator('img').evaluateAll(nodes=>Promise.all(nodes.map(async node=>{
    await node.decode()
    return node.naturalWidth>0
  }))),Array(22).fill(true))
  assert.equal(await page.locator('table tbody tr').count(),4)
  await screenshot(page,'review')
  const archivePending=page.waitForEvent('download')
  await page.getByRole('link',{name:'下载逐片 JSON 与 VTK'}).click()
  assert.equal(digest(await readFile(await (await archivePending).path())),digest(body))

  const phone=await context.newPage()
  await phone.setViewportSize({width:390,height:844})
  await phone.addInitScript(()=>Object.defineProperty(Navigator.prototype,'gpu',{get:()=>undefined}))
  await phone.goto(base.href)
  assert.ok(await phone.evaluate(()=>document.documentElement.scrollWidth===innerWidth))
  await phone.locator('#readout').getByText(/2D 纸样仍可使用/).waitFor()
  await phone.locator('[data-value-key="sa"]').fill('10')
  await phone.locator('[data-status]').getByText(/缝份.*裁片变化/).waitFor()
  assert.equal(await phone.locator('[data-full] g[id*="-part-"]').count(),20)
  await screenshot(phone,'editor-mobile')
  assert.deepEqual(errors,[])
  console.log(JSON.stringify({
    verdict:'PASS',base:base.href,commit:expectedCommit??null,appSha256:digest(await local('index.html')),
    archiveSha256:digest(body),runs:readings,reportImages:22,mobileWidth:390,
    observed:'4 × 480 steps, GPU dispatches, real SVG and VTK downloads, 2D operation without WebGPU',
  },null,2))
}finally{
  await browser.close()
}
