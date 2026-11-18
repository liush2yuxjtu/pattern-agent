#!/usr/bin/env python3
"""Build official review plus source-bound measurement evidence; never alter runs."""
import argparse, hashlib, html, json, shutil, zipfile
from pathlib import Path
import cv2
import numpy as np
from build_functional_review import build as official_review
from visual_gallery import stage
ROOT=Path(__file__).resolve().parents[2]
NAMES={1:'已保存人体模型',2:'目标残差与缓存污染',3:'不匹配网格拒绝'}
def load(p):return json.loads(p.read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc')
def archive(p,out):
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for f in files(p):
            i=zipfile.ZipInfo(str(f.relative_to(p)),(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o644<<16;z.writestr(i,f.read_bytes())
def read_mesh(path):
    """Review-only OBJ reader: no executor/exporter functions are imported."""
    vertices=[];faces=[]
    for line in path.read_text().splitlines():
        parts=line.split('#',1)[0].split()
        if not parts:continue
        if parts[0]=='v':vertices.append(tuple(map(float,parts[1:4])))
        elif parts[0]=='f':
            row=[int(p.split('/')[0]) for p in parts[1:]];assert len(row)==3
            faces.append(tuple(i-1 if i>0 else len(vertices)+i for i in row))
    return np.asarray(vertices),np.asarray(faces)
def replay_neutral(asset,weights):
    """Vector accumulation from asset sparse rows, solely for review projection."""
    vertices=np.asarray(asset['vertices'],dtype=float).reshape(-1,3).copy()
    for control,weight in zip(asset['controls'],weights):
        rows=np.asarray(control['incr' if weight>=0 else 'decr'])
        if len(rows):np.add.at(vertices,rows[:,0].astype(int),abs(weight)*rows[:,1:])
    compact=vertices[asset['bodyVertexIds']].copy();compact[:,1]-=compact[:,1].min();return compact

def project(vertices,view,lo,hi):
    axis=0 if view=='front' else 2
    scale=min(600/(hi[axis]-lo[axis]),750/(hi[1]-lo[1]))
    return np.column_stack((350+(vertices[:,axis]-(lo[axis]+hi[axis])/2)*scale,830-(vertices[:,1]-lo[1])*scale)).astype(np.int32)
def render(path,vertices,faces,tape,view,reconstructed=None,title='Actual supplied OBJ'):
    both=vertices if reconstructed is None else np.vstack((vertices,reconstructed));lo=both.min(0);hi=both.max(0)
    canvas=np.full((920,700,3),248,np.uint8);points=project(vertices,view,lo,hi)
    depth=2 if view=='front' else 0
    order=np.argsort(vertices[faces][:,:,depth].mean(1))
    for face in faces[order]:cv2.fillConvexPoly(canvas,points[face],(204,184,153),lineType=cv2.LINE_AA)
    cv2.polylines(canvas,[points[tape]],False,(30,90,225),3,cv2.LINE_AA)
    if reconstructed is not None:
        expected=project(reconstructed,view,lo,hi);mask=np.zeros(canvas.shape[:2],np.uint8)
        for face in faces:cv2.fillConvexPoly(mask,expected[face],255)
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);cv2.drawContours(canvas,contours,-1,(170,90,15),2,cv2.LINE_AA)
        cv2.putText(canvas,'Blue: saved neutral reconstruction',(28,880),cv2.FONT_HERSHEY_SIMPLEX,.55,(170,90,15),1,cv2.LINE_AA)
    cv2.putText(canvas,'REVIEW-DERIVED | '+view.upper(),(25,35),cv2.FONT_HERSHEY_SIMPLEX,.65,(50,50,50),1,cv2.LINE_AA)
    cv2.putText(canvas,title,(25,64),cv2.FONT_HERSHEY_SIMPLEX,.55,(50,50,50),1,cv2.LINE_AA)
    cv2.putText(canvas,'Red: actual OBJ waist tape',(28,905),cv2.FONT_HERSHEY_SIMPLEX,.55,(30,90,225),1,cv2.LINE_AA)
    path.parent.mkdir(parents=True,exist_ok=True);cv2.imwrite(str(path),canvas)

def normalize_measurements(output):
    p=next(iter(sorted(output.glob('measurements*.json'))),None)
    if not p:return None,{}
    d=load(p);rows=d.get('measurements',[]);values=d.get('measured_values_cm')
    if values is None:values={r['name']:r.get('value_cm',r.get('value')) for r in rows}
    return p,values

def build(workspace,site,allow_pending=False):
    origin=workspace/'iteration-1';runs=sorted(origin.glob('eval-*/*/run-*'));assert len(runs)==6
    complete=all((r/'grading.json').exists() for r in runs) and (origin/'benchmark.json').exists()
    if not complete and not allow_pending:raise ValueError('Independent grading/official benchmark required (use --allow-pending for NOT_GRADED preview)')
    if complete:
        for run in runs:
            grade=load(run/'grading.json');meta=load(run/'eval_metadata.json');expected={str(p.relative_to(run/'outputs')):digest(p) for p in files(run/'outputs')}
            assert grade.get('artifact_sha256')==expected, 'Graded output hashes changed: '+str(run)
            assert len(grade['expectations'])=={1:7,2:7,3:5}[meta['eval_id']]
            for name,sha in grade['source_hashes']['model_inputs'].items():assert digest(workspace/'inputs'/name)==sha, 'Graded input changed: '+name
            for name,sha in grade['source_hashes']['skill_snapshot'].items():assert digest(workspace/name)==sha, 'Graded skill changed: '+name
    site.mkdir(parents=True,exist_ok=True);review=workspace/'model-size-review-inputs'
    if review.exists():shutil.rmtree(review)
    inventory=[];gallery={};source={};asset=load(workspace/'inputs/human.json');compact={v:i for i,v in enumerate(asset['bodyVertexIds'])};tape=np.array([compact[i] for i in next(c for c in asset['controls'] if c['key']=='waist')['path']])
    def copy(p,name):
        dest=site/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);return name
    def item(name,label,caption):return dict(src=name,label=label,caption=caption,sha256=digest(site/name))
    for folder in ['inputs','skill-new','skill-old','grade-evidence','protocol','analysis']:
        name='source/'+folder+'.zip';archive(workspace/folder,site/name);source[folder]=dict(href=name,sha256=digest(site/name))
    for name in ['plan.json','evals.json','skill-new-manifest.json','skill-old-manifest.json']:
        href=copy(workspace/name,'source/'+name);source[name]=dict(href=href,sha256=digest(site/href))
    for name in ['build_model_size_review.py','aggregate_model_size_skill.py','grade_model_size_skill.py']:
        href=copy(ROOT/'tools/skill_evals'/name,'source/'+name);source[name]=dict(href=href,sha256=digest(site/href))
    for run in runs:
        meta=load(run/'eval_metadata.json');number=meta['eval_id'];case=meta['input_case'];config=run.parent.name;rel=run.relative_to(origin);key=str(rel).replace('/','-');base='artifacts/'+str(rel);thin=review/rel;(thin/'outputs').mkdir(parents=True)
        shutil.copyfile(run/'eval_metadata.json',thin/'eval_metadata.json')
        if (run/'grading.json').exists():shutil.copyfile(run/'grading.json',thin/'grading.json')
        for p in files(run/'outputs'):
            copy(p,base+'/'+str(p.relative_to(run/'outputs')))
            if p.suffix in {'.json','.csv','.md','.txt','.log'}:shutil.copyfile(p,thin/'outputs'/p.name)
        archive(run,site/(base+'.zip'))
        vertices,faces=read_mesh(workspace/f'inputs/{case}/neutral.obj');state=load(workspace/f'inputs/{case}/final-state.json');rebuilt=replay_neutral(asset,state['morphWeights'])
        maximum=float(np.linalg.norm(vertices-rebuilt,axis=1).max());views=[];overlays=[]
        for view in ['front','side']:
            name=f'visual/{case}/{view}.png';render(site/name,vertices,faces,tape,view);views.append(item(name,'实际输入 OBJ · '+view,'review-derived：由实际输入 neutral.obj 三角面和 asset/bodyVertexIds 绘制；红线是资源声明腰围 tape。非执行者产物，非 Image Gen。'))
            name=f'visual/{case}/overlay-{view}.png';render(site/name,vertices,faces,tape,view,rebuilt,'Actual OBJ vs saved neutral (same projection)');overlays.append(item(name,'独立重建对照 · '+view,f'review-derived：实际 OBJ 与 asset+morphWeights neutral 同一投影；无二维 warp。最大逐顶点差 {maximum:.9f} cm；正确拒绝不等于模型匹配成功。'))
        measurement,values=normalize_measurements(run/'outputs');rows=[]
        if number==2:
            chart=np.full((500,700,3),248,np.uint8);actual=values.get('waist');target=state['dimensions']['waist']
            cv2.putText(chart,'REVIEW-DERIVED | actual run JSON',(25,40),cv2.FONT_HERSHEY_SIMPLEX,.7,(45,45,45),1,cv2.LINE_AA)
            for j,(label,value,color) in enumerate([('Actual OBJ waist tape',actual,(160,120,55)),('Control target',target,(90,140,210))]):
                y=140+j*145;cv2.putText(chart,label,(25,y-30),cv2.FONT_HERSHEY_SIMPLEX,.75,(45,45,45),1,cv2.LINE_AA);cv2.rectangle(chart,(25,y),(25+int(value*4.9),y+45),color,-1);cv2.putText(chart,f'{value:.6f} cm',(25,y+80),cv2.FONT_HERSHEY_SIMPLEX,.75,(45,45,45),1,cv2.LINE_AA)
            cv2.putText(chart,'Measured - target: -8.916900 cm',(25,460),cv2.FONT_HERSHEY_SIMPLEX,.75,(45,45,45),1,cv2.LINE_AA)
            chartname=f'visual/{case}/{config}-waist-result.png';cv2.imwrite(str(site/chartname),chart)
            result_views=[item(chartname,'实际腰围 / 目标差值','review-derived：读取本执行原始 JSON 主值 99.083100 cm 与独立控制目标 108 cm。不是缓存，也不更改模型。'),*views]
        else:result_views=views
        for control in asset['controls']:
            k=control['key'];v=values.get(k);target=state['dimensions'].get(k);delta=v-target if v is not None and target is not None else None
            fmt=lambda x:'拒绝 / null' if x is None else f'{x:.6f}'
            rows.append('<tr><td>'+html.escape(k)+'</td><td>'+fmt(v)+'</td><td>'+fmt(target)+'</td><td>'+fmt(delta)+'</td></tr>')
        table='<section class="measurement-table"><h3>实际执行尺寸 · cm</h3><p>'+('对应关系拒绝：无成功测量值。' if number==3 else '表中主值读取实际执行 JSON；输入目标单列。')+'</p><table><thead><tr><th>尺寸</th><th>模型实测 cm</th><th>控制目标 cm</th><th>实测 − 目标 cm</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table><p>模型测量不等于真人实测；表面 tape 不等于平面截线周长。缓存 measuredNeutral 不是测量来源。</p>'
        links=[]
        for p in sorted((run/'outputs').glob('measurements*')):
            if p.suffix in {'.json','.csv'}:links.append(f'<a download href="{base}/{p.name}">{p.name}</a> SHA256 {digest(p)}')
        table+='<p>'+ '<br>'.join(links)+f'</p><p><a download href="{base}.zip">完整 run ZIP</a> SHA256 {digest(site/(base+".zip"))}</p></section>'
        if (run/'grading.json').exists():
            grading=load(run/'grading.json');table+='<details class="claim-audit"><summary>独立 grader：额外 claims 与评测反馈（非冻结断言）</summary><p>19/19 仅表示冻结任务断言通过，不表示下列所有 claim 成立。</p>'
            for claim in grading.get('claims',[]):
                table+='<p><strong>'+('VERIFIED' if claim.get('verified') else 'NOT VERIFIED')+' · '+html.escape(claim['claim'])+'</strong><br>'+html.escape(claim.get('evidence',''))+'</p>'
            feedback=grading.get('eval_feedback',{})
            table+='<p>'+html.escape(feedback.get('overall',''))+'</p>'
            for suggestion in feedback.get('suggestions',[]):table+='<p>'+html.escape(suggestion.get('reason',''))+'</p>'
            table+='</details>'

        gallery[key]=dict(title=NAMES[number]+' · '+('新版技能' if config=='with_skill' else '冻结旧版'),stages=[stage('input','1. 实际输入 OBJ',views,'review-derived projection'),stage('imagegen','2. Image Gen',status='NOT_REQUESTED',empty_title='本轮未调用 Image Gen',note='测量分支输入为保存状态、资源和实际网格。'),stage('simulation','3. 执行测量 JSON / CSV',result_views,'拒绝导出 · 非匹配成功' if number==3 else '12 项实际执行测量',note='渲染为 review-derived；原始 JSON/CSV 下载见下表。'),stage('overlay','4. 独立几何对照',overlays,'MISMATCH · expected rejection' if number==3 else '对应关系重建对照')],note='同 prompt / 同输入的独立执行，每配置每案例 N=1。PNG 为 review-derived，非执行者渲染或新 Image Gen。',table_html=table)
        inventory.append(dict(id=key,eval_id=number,case=case,config=config,archive=base+'.zip',sha256=digest(site/(base+'.zip')),measurement_file=base+'/'+measurement.name if measurement else None,measurement_values=values,maximum_geometry_error_cm=maximum,grading=load(run/'grading.json')['summary'] if (run/'grading.json').exists() else None,artifact_sha256={str(p.relative_to(run/'outputs')):digest(p) for p in files(run/'outputs')}))
    document,upstream=official_review(review,origin/'benchmark.json' if complete else None)
    document=document.replace('Executed synthetic controls. Not native Claude triggering, real anatomical validation, or full six-image generation quality.','Executed paired model measurement branch. N=1; native Claude BLOCKED; Image Gen NOT_REQUESTED; time/tokens unknown.')
    intro='<section id="model-size-intro"><h2>人体模型实际尺寸 · 测量分支评测</h2><p>3 案例 × 新版 / 冻结旧版技能，共 6 次真实独立子代理执行；每对使用相同 prompt 和输入，N=1。保留官方 Prompt、Output、Formal Grades、Feedback、Benchmark 和 Submit All Reviews 流程。</p><p>native Claude <strong>BLOCKED</strong> · Image Gen <strong>NOT_REQUESTED</strong> · tokens / time <strong>null（未知）</strong>。本轮只检验模型测量分支，不代表完整生成、人体照片精度或服装物理验证。</p><p><strong>'+('独立评分完成，正式对照结果见 Benchmark。' if complete else 'NOT_GRADED：独立评分待完成，当前预览不得解读为通过。')+'</strong></p><p>案例 2 腰围：控制目标 108 cm，真实网格 tape 99.083100 cm。案例 3：实际 supplied mesh 不对应保存的 neutral，正确行为是拒绝；拒绝成功不等于模型匹配成功。</p><details><summary>来源与技能下载（SHA256）</summary>'
    for name,value in source.items():intro+=f'<p><a download href="{value["href"]}">{name}</a> SHA256 {value["sha256"]}</p>'
    intro+='<p><a href="manifest.json">完整文件 manifest</a> · <a href="../skill/">当前技能</a></p></details></section>'
    css='<style>#model-size-intro{padding:20px 24px;font:15px/1.65 system-ui;max-width:1100px;overflow-wrap:anywhere}.measurement-table{margin:20px 0;overflow-wrap:anywhere;font:14px/1.6 system-ui}.measurement-table table{width:100%;border-collapse:collapse}.measurement-table td,.measurement-table th{padding:7px;text-align:left;border-bottom:1px solid #ddd}.measurement-table p{margin:10px 0}</style>'
    css+='<style>'+(ROOT/'tools/skill_evals/assets/visual-gallery.css').read_text()+'.evidence-stage p{font:12px/1.5 system-ui;overflow-wrap:anywhere}.model-size-context{padding:0 0 16px!important}.output-file-content:has(>#official-case-gallery){padding:0}</style>'
    document=document.replace('</head>',css+'<link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml"></head>',1)
    # Only enhance artifact rendering inside the official Output body. Prompt,
    # Formal Grades, Feedback, header, tabs and navigation remain upstream DOM.
    payload=json.dumps(gallery,ensure_ascii=False).replace('<',r'\u003c')
    intro_payload=json.dumps(intro,ensure_ascii=False).replace('<',r'\u003c')
    script=r'''(() => {
      const dialog=document.createElement('dialog');dialog.className='evidence-lightbox';dialog.setAttribute('aria-label','Evidence image viewer');
      dialog.innerHTML='<div class="lightbox-head"><strong id="lightbox-title"></strong><button id="lightbox-close">Close ×</button></div><img id="lightbox-image" class="lightbox-image" alt=""><p id="lightbox-caption"></p><div class="lightbox-controls"><button id="lightbox-prev">← Previous image</button><span id="lightbox-position"></span><button id="lightbox-next">Next image →</button><a id="lightbox-original" target="_blank" rel="noopener">Open original</a></div>';
      document.body.append(dialog);let images=[],position=0,opener;const find=s=>dialog.querySelector(s);
      function paint(){const im=images[position];find('#lightbox-title').textContent=im.label;find('#lightbox-image').src=im.src;find('#lightbox-image').alt=im.label;find('#lightbox-caption').textContent=im.caption;find('#lightbox-original').href=im.src;find('#lightbox-position').textContent=`${position+1} / ${images.length}`;find('#lightbox-prev').disabled=position===0;find('#lightbox-next').disabled=position===images.length-1;}
      function close(){dialog.close();opener?.focus();}find('#lightbox-close').onclick=close;
      find('#lightbox-prev').onclick=()=>{if(position>0){position--;paint();}};find('#lightbox-next').onclick=()=>{if(position<images.length-1){position++;paint();}};
      document.addEventListener('keydown',e=>{if(dialog.open&&['ArrowLeft','ArrowRight','Escape'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();if(e.key==='Escape')close();else find(e.key==='ArrowLeft'?'#lightbox-prev':'#lightbox-next').click();}},true);
      function button(im,index,thumbnail=false){const b=document.createElement('button');b.type='button';b.className=thumbnail?'':'evidence-image';b.setAttribute('aria-label','Open '+im.label);const img=document.createElement('img');img.src=im.src;img.alt=im.label;b.append(img);b.onclick=()=>{opener=b;position=index;paint();dialog.showModal();};return b;}
      const officialOutputs=renderOutputs;
      renderOutputs=function(run){
        officialOutputs(run);const data=VISUAL_EVIDENCE[run.id];if(!data)return;images=[];
        const block=document.createElement('section');block.id='official-case-gallery';block.className='output-file';
        const title=document.createElement('div');title.className='output-file-header';title.textContent=data.title+' · 测量分支实际执行证据';
        const content=document.createElement('div');content.className='output-file-content';
        const context=document.createElement('div');context.innerHTML=OUTPUT_CONTEXT;context.querySelector('#model-size-intro').removeAttribute('id');context.className='model-size-context';content.append(context);
        const grid=document.createElement('div');grid.className='evidence-grid';
        for(const stage of data.stages){const card=document.createElement('section');card.className='evidence-stage';card.dataset.stage=stage.key;const heading=document.createElement('h3');heading.textContent=stage.title;const status=document.createElement('p');status.className='stage-status';status.textContent=stage.status;card.append(heading,status);
          if(!stage.images.length){const empty=document.createElement('p');empty.className='evidence-empty';empty.textContent=stage.emptyTitle+' · '+stage.note;card.append(empty);}
          else{const start=images.length;images.push(...stage.images);card.append(button(stage.images[0],start));const caption=document.createElement('p');caption.textContent=stage.images[0].caption;card.append(caption);if(stage.images.length>1){const strip=document.createElement('div');strip.className='thumb-strip';stage.images.forEach((im,j)=>strip.append(button(im,start+j,true)));card.append(strip);}}grid.append(card);}
        const note=document.createElement('p');note.textContent=data.note;const results=document.createElement('div');results.id='measurement-results';results.innerHTML=data.table_html;content.append(grid,note,results);block.append(title,content);document.querySelector('#outputs-body').prepend(block);
      };
      const priorShow=showRun,selectionKey=STATIC_REVIEW_KEY+':official-case';showRun=function(i){priorShow(i);try{localStorage.setItem(selectionKey,String(i));}catch{}};
      let selected=0;try{const saved=localStorage.getItem(selectionKey);if(saved!==null&&Number.isInteger(Number(saved))&&Number(saved)>=0&&Number(saved)<EMBEDDED_DATA.runs.length)selected=Number(saved);}catch{}showRun(selected);
    })();'''
    document=document.replace('</body>','<script>const VISUAL_EVIDENCE='+payload+';const OUTPUT_CONTEXT='+intro_payload+';\n'+script+'</script></body>',1)
    document=document.replace('#model-size-intro{','.model-size-context{')
    (site/'eval.html').write_text(document)
    if complete:
        for name in ['benchmark.json','benchmark.md','benchmark-upstream-raw.json']:copy(origin/name,name)
    for name in ['analysis.json','posthoc-observations.json','posthoc-observations.md']:
        if (origin/name).exists():copy(origin/name,name)
    manifest=dict(review_projection=dict(derived=True,executor_artifact=False,imagegen=False,projection='orthographic front/side; shared bounds within each overlay; no 2D warp',renderer_sha256=digest(Path(__file__)),upstream_sha256=digest(ROOT/'tools/skill_evals/upstream/eval-viewer/generate_review.py')),complete=complete,status='GRADED' if complete else 'NOT_GRADED',scope='measurement-only paired subagent execution',runs=inventory,source=source,unknown=dict(native_claude_trigger='BLOCKED',imagegen='NOT_REQUESTED',tokens=None,duration=None),upstream=upstream)
    manifest['files']={str(p.relative_to(site)):digest(p) for p in files(site) if p.name!='manifest.json'};write(site/'manifest.json',manifest)
    return dict(complete=complete,runs=len(runs),out=str(site/'eval.html'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--site',type=Path,default=ROOT/'web/garment-body/model-size-evals');p.add_argument('--allow-pending',action='store_true');a=p.parse_args();print(json.dumps(build(a.workspace.resolve(),a.site.resolve(),a.allow_pending)))
