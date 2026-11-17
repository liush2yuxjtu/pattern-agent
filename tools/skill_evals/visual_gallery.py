"""Add visual case evidence to generated review HTML without changing its grades."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import cv2
import numpy as np

ASSETS=Path(__file__).resolve().parent/'assets'


def stage(key,title,images=(),status='',empty_title='',note=''):
    return dict(key=key,title=title,images=list(images),status=status,emptyTitle=empty_title,note=note)


def collect(workspace,site,origin):
    data={}
    for run in sorted(origin.glob('eval-*/*/run-*')):
        metadata=json.loads((run/'eval_metadata.json').read_text());case=metadata['eval_name'];config=run.parent.name
        relative=run.relative_to(origin);key=str(relative).replace('/','-')
        target=site/'visual'/origin.name/relative;target.mkdir(parents=True,exist_ok=True)
        def item(source,name,label,caption):
            dest=target/name;shutil.copyfile(source,dest)
            return dict(src=str(dest.relative_to(site)),label=label,caption=caption,sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
        inputs=[];simulations=[];overlays=[]
        output=run/'outputs'
        for view in ['front','side','back','close-up','pose','depth']:
            source=output/'renders'/(view+'.png')
            if source.is_file():simulations.append(item(source,'simulation-'+view+'.png','Simulation '+view,'Actual saved anatomical mesh render · '+view+' · not a cloth physics simulation'))
        if case=='anatomical-fit':
            fixture=workspace/'fixtures/anatomical-fit'
            for view in ['front','side']:
                inputs.append(item(fixture/f'reference-{view}.png','input-'+view+'.png','Input '+view,'Supplied synthetic anatomical reference · '+view+' · not an e-commerce photograph'))
                overlays.append(item(output/'overlays'/(view+'.png'),'overlay-'+view+'.png','Overlay '+view,'Executed OpenCV fit overlay · green overlap, pink reference only, cyan model only'))
        elif case in ['pose-depth-evidence','camera-transfer']:
            fixture=workspace/'fixtures'/('camera-transfer-holdout' if case=='camera-transfer' else case)
            if case=='pose-depth-evidence':
                for view in ['front','side']:
                    inputs.append(item(fixture/'reference-renders'/(view+'.png'),'input-'+view+'.png','Input '+view,'Supplied source mesh reference render · '+view+' · not Image Gen'))
            # Render the source OBJ under the run camera for a valid replay overlay.
            spec=importlib.util.spec_from_file_location('gallery_raster',workspace/'fixtures/render_mesh.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
            vertices,faces=renderer.obj(fixture/'source-posed.obj');camera=json.loads((output/'camera.json').read_text())
            for view in ['front','side']:
                reference,render,_,_=renderer.raster(vertices,faces,camera,view)
                refpath=target/('source-projection-'+view+'.png');cv2.imwrite(str(refpath),render)
                if case=='camera-transfer':inputs.append(dict(src=str(refpath.relative_to(site)),label='Input '+view,caption='Review-derived source mesh projection under the supplied new camera · '+view,sha256=hashlib.sha256(refpath.read_bytes()).hexdigest()))
                projected=cv2.imread(str(output/'renders'/(view+'-mask.png')),0)
                if projected is None:continue
                a=reference>0;b=projected>0;image=np.full((*a.shape,3),245,np.uint8);image[a&b]=[65,175,45];image[a&~b]=[155,45,235];image[b&~a]=[225,195,20]
                path=target/('overlay-'+view+'.png');cv2.imwrite(str(path),image)
                overlays.append(dict(src=str(path.relative_to(site)),label='Overlay '+view,caption='Review-derived raster replay overlay · source OBJ vs saved output · '+view+' · green agreement is consistency, not real-person accuracy',sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        name={'state-audit':'Saved-state audit','anatomical-fit':'Silhouette fit','pose-depth-evidence':'Pose & depth','camera-transfer':'New-camera transfer'}[case]
        data[key]=dict(title=name+' · '+('Updated skill' if config=='with_skill' else 'Original skill'),stages=[
            stage('input','1. Input reference',inputs,'Synthetic reference' if inputs else 'Not applicable','No input image','This case audits saved JSON states and an OBJ, rather than an image. Use the case selector for image-fitting evidence.'),
            stage('imagegen','2. Image Gen output',status='NOT RUN',empty_title='Image Gen was not run',note='These evaluations did not generate clothed photos. Simulation renders are shown separately and are not substituted here.'),
            stage('simulation','3. Simulation / 3D render',simulations,'Saved mesh render' if simulations else 'Not run in this case','No simulation image output','This audit checks numerical saved-state measurements. It did not produce simulation images.'),
            stage('overlay','4. Overlay comparison',overlays,'OpenCV comparison' if overlays else 'Not applicable','No image overlay','This is a state-data audit, so no image fit or overlay was executed.')],note='Synthetic anatomical component evaluation. Image Gen, real-person measurement accuracy and cloth physics were not tested. '+('Source projections and replay overlays marked “review-derived” were created for this gallery; they do not change the original run files or grades.' if case in ['pose-depth-evidence','camera-transfer'] else 'Input and output file hashes are retained; original scores and raw artifacts remain available below.'))
    return data


def inject(document,data):
    payload=json.dumps(data,ensure_ascii=False).replace('<',r'\u003c')
    css=(ASSETS/'visual-gallery.css').read_text();script=(ASSETS/'visual-gallery.js').read_text()
    document=document.replace('</head>','<style>'+css+'</style>\n</head>',1)
    return document.replace('</body>','<script>const VISUAL_EVIDENCE = '+payload+';\n'+script+'</script>\n</body>',1)
