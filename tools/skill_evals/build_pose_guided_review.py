#!/usr/bin/env python3
"""Publish same-frame, failure-sensitive pose fitting evidence without altering history."""
import argparse, hashlib, html, json, re, shutil
from pathlib import Path
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'work/pose-guided-fit-20261118'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text()) if p.exists() else {}
def write(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

def layers(source,dest):
    mask=next((source/n for n in ('final-mask.png','photo-depth-valid.png') if (source/n).exists()),None)
    if not mask:return
    m=cv2.imread(str(mask),0)
    if m.shape!=(1276,1000):raise ValueError('Projection must be original 1000 × 1276: '+str(mask))
    rgba=np.zeros((1276,1000,4),np.uint8)
    cv2.drawContours(rgba,cv2.findContours((m>0).astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0],-1,(255,175,0,255),2,cv2.LINE_AA)
    cv2.imwrite(str(dest/'contour.png'),rgba)
    if (source/'photo-render.png').exists():
        render=cv2.imread(str(source/'photo-render.png'))
        if render.shape[:2]!=m.shape:raise ValueError('Render and mask frame mismatch')
        rgba=cv2.cvtColor(render,cv2.COLOR_BGR2BGRA);rgba[:,:,3]=m
        cv2.imwrite(str(dest/'transparent-render.png'),rgba)

def target_layer(workspace,site):
    cue=read(workspace/'targets/pose-targets.json')
    layer=np.zeros((1276,1000,4),np.uint8)
    points={p['id']:tuple(round(v) for v in p['raw_xy']) for p in cue.get('points',[])}
    for a,b in cue.get('links',[]):
        cv2.line(layer,points[a],points[b],(0,220,255,255),2,cv2.LINE_AA)
    for p in points.values():cv2.circle(layer,p,6,(0,220,255,255),2,cv2.LINE_AA)
    cv2.imwrite(str(site/'targets/transparent-targets.png'),layer)

def skeleton_layer(source,dest):
    joints=next((source/p for p in ('joints.json','views/joints.json') if (source/p).exists()),None)
    camera=source/'camera.json'
    if not joints or not camera.exists():return
    matrix=np.asarray(read(camera)['world_to_pixel_homogeneous'])
    if matrix.shape!=(3,4):raise ValueError('Actual saved photo camera required for skeleton')
    points={}
    for p in read(joints)['joints']:
        q=matrix@np.r_[p['position'],1]
        points[p['name']]=tuple(int(round(v)) for v in q[:2]/q[2])
    layer=np.zeros((1276,1000,4),np.uint8)
    prefixes=('spine','root','pelvis','head','neck','shoulder','upperarm','lowerarm','wrist','upperleg','lowerleg','foot','clavicle')
    for p in read(joints)['joints']:
        if p['name'].startswith(prefixes) and p['parent'] in points:
            cv2.line(layer,points[p['name']],points[p['parent']],(255,35,210,255),3,cv2.LINE_AA)
            cv2.circle(layer,points[p['name']],5,(255,35,210,255),-1,cv2.LINE_AA)
    cv2.imwrite(str(dest/'transparent-skeleton.png'),layer)
    write(dest/'skeleton-projection.json',dict(method='Actual saved FK joint positions projected by saved photo matrix; no 2D fitting/warp; occlusion unclassified',joints_sha256=sha(joints),camera_sha256=sha(camera),pixels=points))

def component(prefix=''):
    # The same UI is embedded inline in the historical URL; no iframe or photo CSS warp.
    return f'''<link rel="stylesheet" href="{prefix}review.css"><section id="pose-review" data-prefix="{prefix}">
    <nav><a href="#pr-human-review">本轮评阅与反馈</a> · <a href="../skill/">当前技能</a> · <a href="{prefix}manifest.json">完整文件哈希</a> · <a href="{prefix}eval.html">独立大图评阅</a></nav>
    <header><p class="eyebrow">本轮：Image Gen 姿态引导 → 真实可调人体拟合</p><h1>先看身体哪里没对齐</h1><p id="pr-summary">正在读取真实产物与独立评分…</p><p class="pr-caution">原图固定为 1000 × 1276；只有真实三维相机投影可与它叠加。Image Gen 是示意姿态线索，不是检测器真值或人体尺寸测量。</p></header>
    <div class="pr-toolbar"><fieldset><legend>真实模型版本</legend><button id="pr-before">修改前 · 旧差拟合</button><button id="pr-after">修改后 · 最新候选</button></fieldset><label>模型透明度 <input id="pr-opacity" type="range" min="0" max="1" value="0.35" step="0.05"><output id="pr-opacity-value">0.35</output></label><label><input id="pr-contour" type="checkbox" checked> 真实轮廓</label><label><input id="pr-real-skeleton" type="checkbox"> 真实骨架</label><label><input id="pr-skeleton" type="checkbox"> 目标点线</label><button id="pr-zoom">放大叠加图</button></div>
    <div class="pr-grid"><figure><h2>1 · 原始商品照片</h2><button class="pr-image" data-zoom="reference/original-product.jpg"><img src="{prefix}reference/original-product.jpg" alt="原始商品照片，固定像素画幅"></button><figcaption>原始文件保持不变，不变形、不重绘。</figcaption></figure>
    <figure><h2>2 · Image Gen 姿态线索</h2><button class="pr-image" id="pr-guide-zoom"><img id="pr-guide" src="{prefix}targets/raw-target-overlay.png" alt="映射回原图的姿态标注"></button><label><input id="pr-guide-native" type="checkbox"> 查看 Image Gen 原始输出</label><figcaption id="pr-registration"></figcaption></figure>
    <figure><h2>3 · 原相机真实模型投影</h2><button class="pr-image" id="pr-model-zoom"><img id="pr-projection" alt="真实三维裸模的原相机裁切投影"></button><figcaption id="pr-model-caption">等待模型文件</figcaption></figure>
    <figure><h2>4 · 原图与真实模型叠加</h2><button class="pr-image pr-stack" id="pr-overlay-zoom"><img src="{prefix}reference/original-product.jpg" alt="固定原图"><img id="pr-render-layer" alt="透明真实网格投影"><img id="pr-contour-layer" alt="真实网格轮廓"><img id="pr-real-skeleton-layer" alt="真实FK骨架相机投影" hidden><img id="pr-skeleton-layer" src="{prefix}targets/transparent-targets.png" alt="示意目标点线" hidden></button><figcaption>青色细线来自真实网格边界；透明度可调，错位必须保留可见。</figcaption></figure></div>
    <section class="pr-section"><h2>关键区域验收：不以平均分掩盖失败</h2><p id="pr-verdict"></p><p class="pr-scroll-hint">手机可左右滑动下表，查看超出比例与轮廓误差。</p><div class="pr-table-scroll"><table id="pr-regions"><thead><tr><th>原图区域</th><th>修改前</th><th>修改后</th><th>前 → 后：超出衣服比例</th><th>前 → 后：外轮廓 P95 px</th></tr></thead><tbody></tbody></table></div><p id="pr-thresholds"></p><p><a download href="{prefix}review/acceptance.json">冻结验收阈值</a> · <a download href="{prefix}protocol.json">拟合协议</a> · <a href="{prefix}review/README.md">独立复算说明</a> · <a href="{prefix}review/pose-sanity-contract.json">补充动作反例门槛</a> · <a href="{prefix}review/grader-hill-climb.md">评分器如何被反例修正</a> · <a download href="{prefix}review/negative-controls/summary.json">负例控制结果</a></p><p>这是照片二维包络检查；衣服遮挡、隐藏关节、深度歧义和人体真实厘米尺寸仍有不确定性。通过二维检查不能证明三维姿态完美恢复。</p><p id="pr-action-gate"></p><p id="pr-integrity"></p><div id="pr-action-failures"></div><details><summary>腰髋逐行残差与独立原始评分</summary><pre id="pr-raw-grade"></pre></details></section>
    <section class="pr-section"><h2>同一保存状态的正 / 侧 / 背面</h2><div id="pr-views" class="pr-views"></div><p>这些视图用于检查同一姿态的三维合理性；背面与深度不是原图中已观测的事实。</p><p id="pr-model-link"></p><div id="pr-downloads"></div></section>
    <section class="pr-section" id="pr-human-review"><h2>本轮评阅：证据 → 人工反馈 → 下一轮改进</h2><p id="pr-assertion-version"></p><p>逐项核对实际输出；功能通过不抵消动作失败。这里保留评分器原始证据，不把文件数量当作质量分。</p><ol id="pr-expectations"></ol><a id="pr-expectations-source">查看此版本完整 grading.json</a><details><summary>评分器自身有哪些漏检？</summary><ul id="pr-eval-critique"></ul></details><h3>记录你的判断</h3><p id="pr-feedback-version"></p><label for="pr-human-acceptance">此版本的人工结论</label><select id="pr-human-acceptance" disabled><option value="not_reviewed">尚未评阅</option><option value="needs_changes">仍需改进</option><option value="accepted">可以接受</option></select><label for="pr-human-feedback">哪些部位不匹配？下一轮优先修哪里？</label><textarea id="pr-human-feedback" disabled rows="5" placeholder="例如：左肘过低，双掌仍朝上；请保持腰臀与相机，先修肘腕和握衣手势。"></textarea><p id="pr-feedback-status" role="status">正在读取此版本反馈…</p><button id="pr-export-feedback" disabled>导出 feedback.json</button><p>仅本地保存和下载，不自动发送。修改前后分别保存，原图、模型或相机变更后不会沿用旧验收。</p></section>
    <details class="pr-section" id="pr-rejected"><summary>失败迭代：为什么低二维点误差仍不能验收</summary><p>以下是同一目标动作的真实三维失败候选，不是新生成的模特商品图，也不是选定最终结果。</p><div id="pr-rejected-cases"></div></details>
    <details class="pr-section"><summary>来源、状态和网格哈希</summary><pre id="pr-provenance"></pre></details>
    <dialog id="pr-dialog"><div class="pr-dialog-toolbar"><button id="pr-close">关闭</button><button id="pr-zoom-out">缩小</button><button id="pr-zoom-in">放大</button><button id="pr-modal-before">修改前</button><button id="pr-modal-after">修改后</button><label>透明度 <input id="pr-modal-opacity" type="range" min="0" max="1" step="0.05" value="0.35"></label><span>滚动查看原始细节 · Esc 关闭</span></div><div id="pr-large"></div></dialog>
    </section><script src="{prefix}review.js"></script><script src="{prefix}review-feedback.js"></script>'''

def inject_history(document):
    if 'id="pose-review"' in document:
        start=document.index('<link rel="stylesheet" href="../pose-guided-fit/review.css">')
        marker='<script src="../pose-guided-fit/review.js"></script>'
        end=document.index(marker,start)+len(marker)
        feedback='<script src="../pose-guided-fit/review-feedback.js"></script>'
        if document[end:].startswith(feedback):end+=len(feedback)
        return document[:start]+component('../pose-guided-fit/')+document[end:]
    start=document.index('<body>')+len('<body>');end=document.rindex('</body>')
    old=document[start:end]
    return document[:start]+component('../pose-guided-fit/')+'<details id="pr-history"><summary>历史：六次功能评测与原始反馈（20/20 不代表照片匹配通过）</summary><div id="pr-history-body">'+old+'</div></details>'+document[end:]

CSS='''#pr-human-review{scroll-margin-top:130px}#pr-human-review textarea{display:block;width:100%;resize:vertical;min-height:120px;font:inherit;padding:12px;margin:8px 0}#pr-human-review label{display:block;margin-top:14px}#pr-human-review select{font:inherit;max-width:100%;padding:8px}#pr-expectations{padding-left:22px}#pr-expectations li{margin:16px 0}#pr-expectations p,#pr-eval-critique p{font-size:13px;overflow-wrap:anywhere}#pr-human-review details{margin:14px 0}#pr-feedback-status{color:#526157}body:has(#pose-review){margin:0}#pose-review{box-sizing:border-box}#pose-review [hidden]{display:none!important}html:has(#pose-review),body:has(#pose-review){height:auto!important;overflow:visible!important;background:#f4f5f4!important}#pose-review{width:100%;min-width:0;overflow-wrap:anywhere;font:15px/1.6 system-ui,sans-serif;color:#202823;max-width:1800px;margin:auto;padding:24px}#pose-review *{box-sizing:border-box}#pose-review h1{font-size:32px;margin:4px 0}#pose-review h2{font-size:17px;margin:0 0 10px}#pose-review p{margin:8px 0}#pose-review nav{margin-bottom:20px}#pose-review .eyebrow{font-size:13px;color:#58695e}#pose-review button,#pose-review input,#pose-review a{font:inherit}#pose-review button{cursor:pointer;border:1px solid #b7c1ba;background:white;border-radius:6px;padding:7px 12px;color:inherit}#pose-review button[aria-pressed=true]{background:#263d31;color:white}#pose-review a{color:#165d42}#pose-review .pr-caution{color:#58645c;max-width:100ch}.pr-toolbar{display:flex;gap:18px;flex-wrap:wrap;align-items:center;padding:15px 0;position:sticky;top:0;background:#f4f5f4f5;z-index:3}.pr-toolbar fieldset{border:0;padding:0}.pr-toolbar legend{font-size:12px}.pr-toolbar label{display:flex;gap:7px;align-items:center}.pr-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.pr-grid figure{margin:0;background:white;padding:12px;border:1px solid #d7ddd9;border-radius:9px}.pr-image{display:block!important;width:100%;padding:0!important;border:0!important;background:#edf0ee!important;position:relative;overflow:hidden;aspect-ratio:1000/1276}.pr-image img{display:block;width:100%;height:100%;object-fit:contain}.pr-stack img:not(:first-child){position:absolute;inset:0}.pr-grid figcaption{font-size:13px;color:#59655d;margin-top:8px}.pr-section{background:white;border:1px solid #d7ddd9;border-radius:9px;padding:20px;margin-top:20px}.pr-table-scroll{overflow:auto}#pr-regions{border-collapse:collapse;width:100%;min-width:620px}#pr-regions th,#pr-regions td{text-align:left;border-bottom:1px solid #e2e5e3;padding:10px}.pr-status{white-space:nowrap;display:inline-block;border-radius:4px;padding:2px 7px;font-weight:700}.pr-status.FAIL{background:#ffe0db;color:#9e2412}.pr-status.PASS{background:#e3f3e9;color:#236443}.pr-status.NOT_RUN,.pr-status.PENDING,.pr-status.UNKNOWN{background:#fff1d6;color:#77530d}.pr-reject-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:10px 0 24px}.pr-reject-grid img{width:100%;height:320px;object-fit:contain}.pr-views{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;max-width:1000px}.pr-views img{width:100%;max-height:420px;object-fit:contain;background:#f3f5f4}.pr-views button{width:100%}#pr-downloads{display:flex;gap:14px;flex-wrap:wrap}#pose-review pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 monospace;max-height:450px;overflow:auto}#pr-dialog{padding:0;width:min(96vw,1450px);height:94vh;max-width:96vw;max-height:94vh;border:0;border-radius:10px}#pr-dialog[open]{display:flex;flex-direction:column}#pr-dialog::backdrop{background:#16241de0}.pr-dialog-toolbar{flex-shrink:0;flex-wrap:wrap;display:flex;gap:12px;padding:12px;background:white;position:sticky;top:0;z-index:10}#pr-large{flex:1;min-height:0;overflow:auto;height:calc(100% - 60px);background:#d7ddd9;padding:15px}#pr-large>.pr-stack,#pr-large>img{width:1000px;max-width:none;display:block;transform-origin:top left}#pr-history{margin:25px;padding:18px;background:#fff;border:1px solid #b7c1ba}#pr-history>summary{cursor:pointer;font:bold 16px system-ui}#pr-history-body{position:relative;height:100vh;margin-top:20px;overflow:auto}#pr-history-body>.header{position:static}#pr-history-body>.footer{position:sticky;bottom:0}body:has(#pose-review)>#done-overlay{z-index:50}@media(max-width:1000px){.pr-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){.pr-reject-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.pr-reject-grid img{height:210px}#pose-review{padding:12px}#pose-review h1{font-size:25px}.pr-grid{grid-template-columns:1fr}.pr-toolbar{position:static;gap:10px}.pr-section{padding:12px}.pr-views{gap:4px}#pr-history{margin:12px}.pr-dialog-toolbar{flex-wrap:wrap}.pr-dialog-toolbar span{display:none}}
'''
JS=r'''(()=>{const root=document.querySelector('#pose-review'),prefix=root.dataset.prefix,$=s=>root.querySelector(s);let manifest,selected='baseline',zoom=1,opener;const labels={shoulder_left:'左肩（图像左）',shoulder_right:'右肩（图像右）',arm_left:'左臂',arm_right:'右臂',torso:'躯干',waist_hip_left:'左腰髋',waist_hip_right:'右腰髋'};const url=p=>prefix+p,fmt=x=>Number.isFinite(x)?x.toFixed(2):'—',badge=s=>`<span class="pr-status ${s}">${s}</span>`;
function image(p){return manifest.files[p]?url(p):''}function select(which){selected=which;const final=which==='model';$('#pr-before').setAttribute('aria-pressed',!final);$('#pr-after').setAttribute('aria-pressed',final);$('#pr-projection').src=image(which+'/photo-render.png')||image(which+'/contour.png')||url('reference/original-product.jpg');$('#pr-render-layer').src=image(which+'/transparent-render.png')||image(which+'/contour.png');$('#pr-contour-layer').src=image(which+'/contour.png');$('#pr-real-skeleton-layer').src=image(which+'/transparent-skeleton.png');$('#pr-model-caption').textContent=(final?'最新候选':'修改前旧拟合')+' · 真实相机原画幅，不拉伸网格。';$('#pr-model-link').innerHTML=manifest.files[which+'/final-state.json']?`<a id="pr-open-model" href="../../human-studio/?model=../garment-body/pose-guided-fit/${which}/final-state.json">打开当前${final?'修改后':'修改前'}可调人体 · 厘米尺寸与骨骼角度</a>`:'模型待保存';$('#pr-downloads').innerHTML=Object.keys(manifest.files).filter(p=>p.startsWith(which+'/')&&!p.slice(which.length+1).includes('/')&&/\.(json|obj|glb|zip|csv)$/.test(p)).map(p=>p.slice(which.length+1)).map(n=>`<a download href="${url(which+'/'+n)}">${n}</a>`).join('');$('#pr-views').innerHTML=['front','side','back'].map((v,i)=>{const p=[which+'/views/'+v+'.png',which+'/'+v+'.png'].find(p=>manifest.files[p]);return p?`<button data-zoom="${p}"><img src="${url(p)}" alt="${['正面','侧面','背面'][i]}真实三维"><span>${['正面','侧面','背面'][i]}</span></button>`:''}).join('');for(const b of $('#pr-views').querySelectorAll('button'))b.onclick=()=>openImage(b.dataset.zoom,b);const grade=manifest.grades[final?'final':'baseline']||{};$('#pr-raw-grade').textContent=JSON.stringify(grade,null,2);$('#pr-provenance').textContent=JSON.stringify({selected:which,reference_sha256:manifest.files['reference/original-product.jpg'],state_sha256:manifest.files[which+'/final-state.json'],mesh_sha256:manifest.files[which+'/posed.obj'],camera_sha256:manifest.files[which+'/camera.json'],grade},null,2);layers();}
function layers(){$('#pr-modal-opacity').value=$('#pr-opacity').value;$('#pr-real-skeleton-layer').hidden=!$('#pr-real-skeleton').checked;$('#pr-render-layer').style.opacity=$('#pr-opacity').value;$('#pr-opacity-value').textContent=$('#pr-opacity').value;$('#pr-contour-layer').hidden=!$('#pr-contour').checked;$('#pr-skeleton-layer').hidden=!$('#pr-skeleton').checked;$('#pr-skeleton-layer').style.opacity='.7';if($('#pr-dialog').open&&$('#pr-large').dataset.overlay==='true')makeLargeOverlay();}
function makeLargeOverlay(){const clone=$('#pr-overlay-zoom').cloneNode(true);clone.removeAttribute('id');clone.removeAttribute('onclick');clone.style.width=(1000*zoom)+'px';clone.querySelectorAll('[id]').forEach(e=>e.removeAttribute('id'));$('#pr-large').replaceChildren(clone);}
function showDialog(button){opener=button;zoom=1;$('#pr-dialog').showModal();$('#pr-close').focus();}function openImage(p,button){$('#pr-large').dataset.overlay='false';$('#pr-large').innerHTML=`<img src="${url(p)}" alt="原始证据大图">`;showDialog(button);}function openOverlay(button){$('#pr-large').dataset.overlay='true';showDialog(button);makeLargeOverlay();}
$('#pr-modal-before').onclick=()=>select('baseline');$('#pr-modal-after').onclick=()=>select('model');$('#pr-modal-opacity').oninput=()=>{$('#pr-opacity').value=$('#pr-modal-opacity').value;layers();};$('#pr-before').onclick=()=>select('baseline');$('#pr-after').onclick=()=>select('model');$('#pr-opacity').oninput=layers;$('#pr-contour').onchange=layers;$('#pr-skeleton').onchange=layers;$('#pr-real-skeleton').onchange=layers;$('#pr-guide-native').onchange=()=>{$('#pr-guide').src=url($('#pr-guide-native').checked?'reference/imagegen-pose.png':'targets/raw-target-overlay.png');};$('#pr-guide-zoom').onclick=()=>openImage($('#pr-guide-native').checked?'reference/imagegen-pose.png':'targets/raw-target-overlay.png',$('#pr-guide-zoom'));$('#pr-model-zoom').onclick=()=>openImage(selected+'/photo-render.png',$('#pr-model-zoom'));$('#pr-zoom').onclick=()=>openOverlay($('#pr-zoom'));$('#pr-overlay-zoom').onclick=()=>openOverlay($('#pr-overlay-zoom'));for(const b of root.querySelectorAll('[data-zoom]'))b.onclick=()=>openImage(b.dataset.zoom,b);$('#pr-close').onclick=()=>$('#pr-dialog').close();$('#pr-dialog').onclose=()=>opener?.focus();function scale(n){zoom=Math.max(.4,Math.min(3,zoom+n));if($('#pr-large').dataset.overlay==='true')makeLargeOverlay();else $('#pr-large>img').style.width=(1000*zoom)+'px';}$('#pr-zoom-in').onclick=()=>scale(.25);$('#pr-zoom-out').onclick=()=>scale(-.25);
fetch(url('manifest.json')).then(r=>r.json()).then(m=>{manifest=m;const a=m.grades.baseline?.visual_alignment_2d||{},b=m.grades.final?.visual_alignment_2d||{},status=b.verdict||'PENDING';$('#pr-summary').innerHTML='修改前：'+badge(a.verdict||'NOT_RUN')+'　修改后二维区域检查：'+badge(status)+'；三维动作：'+badge(m.grades.final?.pose_plausibility_3d?.verdict||'NOT_RUN')+'。'+(status==='FAIL'?'仍有关键区域未通过，下面直接显示残差。':status==='PASS'?'二维包络检查通过；三维姿态与尺寸仍须分别审查。':'候选或独立评分待完成，不宣称匹配成功。');$('#pr-verdict').innerHTML='最差区域：修改前 '+(labels[a.worst_region]||a.worst_region||'未知')+'；修改后 '+(labels[b.worst_region]||b.worst_region||'待评分')+'。任何关键区域 FAIL 都不能被功能分平均抵消。';$('#pr-regions tbody').innerHTML=Object.entries(labels).map(([k,label])=>{const x=a.regions?.[k]||{},y=b.regions?.[k]||{};return `<tr><td>${label}</td><td>${badge(x.verdict||'NOT_RUN')}</td><td>${badge(y.verdict||'PENDING')}</td><td>${fmt(100*x.outside_fraction)}% → ${fmt(100*y.outside_fraction)}%</td><td>${fmt(x.exterior_contour_p95_px)} → ${fmt(y.exterior_contour_p95_px)}</td></tr>`}).join('');$('#pr-thresholds').textContent='区域阈值与定义保持冻结（acceptance.json）；动作反例补充门槛独立记录（pose-sanity-contract.json），不以平均分抵消。';$('#pr-integrity').innerHTML='最新功能完整性：'+badge(m.grades.final?.functional_integrity?.verdict||'NOT_RUN')+'；三维姿态合理性：'+badge(m.grades.final?.pose_plausibility_3d?.verdict||'NOT_RUN')+'。历史20/20只记录当时功能断言。';$('#pr-rejected-cases').innerHTML=(m.rejected||[]).map(c=>`<section><h3>${c.id} · ${badge(c.grade.pose_plausibility_3d?.verdict||'FAIL')}</h3><p>${c.reason}</p><div class="pr-reject-grid">${c.images.map((p,i)=>`<button data-zoom="${p}"><img src="${url(p)}" alt="${c.id} ${['原相机投影','正面','侧面','背面'][i]}真实失败候选"><span>${['原相机投影','正面','侧面','背面'][i]}</span></button>`).join('')}</div></section>`).join('');for(const b of $('#pr-rejected-cases').querySelectorAll('[data-zoom]'))b.onclick=()=>openImage(b.dataset.zoom,b);const action=m.grades.final?.action_alignment_2d||{},wrists=action.original_visible_wrist_errors_px||{};$('#pr-action-gate').innerHTML='独立动作反例门槛：'+badge(action.verdict||'NOT_RUN')+'；原图左腕误差 '+fmt(wrists.wrist_image_left)+' px，右腕 '+fmt(wrists.wrist_image_right)+' px。仅防止明显方向/位置矛盾，不能替代握衣动作复核。';const observations=m.grades.final?.pose_plausibility_3d?.observations||[];const actionLabels={standing_balance:'站姿与足部支撑',connected_limbs:'肢体连接',gross_hand_body_overlap:'双手可见与明显穿身',shirt_grasp_action:'原图提衣握持动作',true_3d_depth:'真实隐藏深度'};$('#pr-action-failures').innerHTML=observations.map(o=>`<p>${badge(o.verdict)} ${actionLabels[o.id]||o.id} <span>${o.evidence}</span></p>`).join('');const reg=m.registration;$('#pr-registration').textContent=`标注映射到原图；${reg.inliers||'—'}个配准内点，平均误差${fmt(reg.inlier_mean_error_px)}px。原图未变形。`;$('#pr-after').disabled=!m.files['model/posed.obj'];$('#pr-modal-after').disabled=$('#pr-after').disabled;select(m.files['model/posed.obj']?'model':'baseline');}).catch(e=>{$('#pr-summary').textContent='证据读取失败：'+e.message;console.error(e);});})();'''

def build(workspace,site,allow_pending=False,candidate=None):
    site.mkdir(parents=True,exist_ok=True)
    for name,expected in read(workspace/'protocol.json').get('reference_files',{}).items():
        if sha(workspace/name)!=expected:raise ValueError('Frozen reference changed: '+name)
    grades={k:read(workspace/'review'/k/'grading.json') for k in ('baseline','final')}
    if (workspace/'review/final/PENDING.json').exists():
        # A rejected round may remain archived under final while the critic
        # waits for the next candidate. Never promote that stale judgment.
        grades['final']={}
    final=candidate or workspace/'model'
    required=['final-state.json','posed.obj','neutral.obj','camera.json','photo-render.png','final-mask.png']
    complete=all((final/n).exists() for n in required) and bool(grades['final'])
    if not complete and not allow_pending:raise ValueError('Final actual mesh/camera/render and independent grading required; --allow-pending is preview only')
    if not allow_pending and not all(grades['final'].get(k) for k in ('posed_obj_sha256','state_sha256','camera_sha256')):
        raise ValueError('Final grading must bind actual state, mesh and camera')
    # These subdirectories are generated output. Removed/rejected inputs must
    # not survive a rebuild and enter the new manifest as current evidence.
    for folder in ('reference','targets','baseline','model','review','reproduce','rejected'):
        destination=site/folder
        if destination.exists():shutil.rmtree(destination)
    for folder in ('reference','targets','baseline','model','review'):
        src=final if folder=='model' else workspace/folder;dst=site/folder;dst.mkdir(exist_ok=True)
        for p in sorted(src.rglob('*')):
            if p.is_file() and p.suffix in {'.png','.jpg','.json','.obj','.glb','.md','.csv','.py','.cjs','.mjs','.zip'}:
                target=dst/p.relative_to(src);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    if (workspace/'protocol.json').exists():shutil.copy2(workspace/'protocol.json',site/'protocol.json')
    reproduction=site/'reproduce';reproduction.mkdir(exist_ok=True)
    for name in ('grade_pose_guided_fit.py','check_pose_guided_views.py'):
        if (ROOT/'tools/skill_evals'/name).exists():shutil.copy2(ROOT/'tools/skill_evals'/name,reproduction/name)
    for folder in ('baseline','model'):
        src=final if folder=='model' else workspace/folder
        layers(src,site/folder)
        skeleton_layer(src,site/folder)
    rejected=[]
    for name,reason in [('round-2','全身明显前倾、足部支撑不合理；二维对齐不能抵消站姿问题。'),('round-9','双手在真实三维中分离，一臂伸向侧前方；原相机腕部点误差小也不能证明握衣动作正确。')]:
        src=workspace/'iterations'/name;grade=workspace/'review'/name/'grading.json'
        if not src.exists() or not grade.exists():continue
        images=[]
        for file in ('photo-render.png','views/front.png','views/side.png','views/back.png'):
            if (src/file).exists():
                target=site/'rejected'/name/file;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src/file,target);images.append(str(target.relative_to(site)))
        rejected.append(dict(id=name,reason=reason,images=images,grade=read(grade)))
    target_layer(workspace,site)
    for key,folder in [('baseline','baseline'),('final','model')]:
        for field,name in [('state_sha256','final-state.json'),('posed_obj_sha256','posed.obj'),('camera_sha256','camera.json')]:
            if grades[key].get(field) and grades[key][field] != sha((final if folder=='model' else workspace/folder)/name):
                raise ValueError('Stale independent grade: '+folder+'/'+name)
    (site/'review.css').write_text(CSS);(site/'review.js').write_text(JS)
    shutil.copyfile(ROOT/'tools/skill_evals/pose_review_feedback.js',site/'review-feedback.js')
    document='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>姿态引导 · 原图同画幅匹配</title></head><body>'+component()+'</body></html>'
    (site/'eval.html').write_text(document);(site/'index.html').write_text(document)
    manifest=dict(complete=complete,scope='Actual pose-guided candidate; historical functional scores are not photo-fit acceptance',grades=grades,rejected=rejected,registration=read(workspace/'targets/registration.json'),files={str(p.relative_to(site)):sha(p) for p in sorted(site.rglob('*')) if p.is_file() and p.name!='manifest.json'})
    write(site/'manifest.json',manifest)
    historical=ROOT/'web/garment-body/single-state-evals/eval.html'
    if historical.exists():
        historical.write_text(inject_history(historical.read_text()))
        historical_manifest=historical.parent/'manifest.json'
        if historical_manifest.exists():
            record=read(historical_manifest)
            record.setdefault('files',{})['eval.html']=sha(historical)
            write(historical_manifest,record)
    print(json.dumps(dict(complete=complete,files=len(manifest['files']),baseline=grades['baseline'].get('visual_alignment_2d',{}).get('verdict'),final=grades['final'].get('visual_alignment_2d',{}).get('verdict'))))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,default=WORK);p.add_argument('--site',type=Path,default=ROOT/'web/garment-body/pose-guided-fit');p.add_argument('--allow-pending',action='store_true');p.add_argument('--candidate',type=Path,help='Preview an iteration; still requires matching final grading for complete publication');a=p.parse_args();build(a.workspace,a.site,a.allow_pending,a.candidate)
