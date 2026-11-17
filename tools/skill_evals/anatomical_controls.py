#!/usr/bin/env python3
"""Frozen anatomical control fixture builder and independent artifact grader.
The grader reads raw OBJ triangles and private truth, never an executor verifier.
"""
import argparse,hashlib,importlib.util,json,subprocess,sys,zipfile
from pathlib import Path
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'work/anatomical-skill-evals-20261117'

def read(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def renderer():
    spec=importlib.util.spec_from_file_location('anatomical_raster',WORK/'fixtures/render_mesh.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def meshwrite(path,v,f):
    with Path(path).open('w') as out:
        out.write('# MakeHuman CC0 actual anatomical surface, centimetres, Y-up\n')
        for p in v:out.write('v '+' '.join(f'{x:.7f}' for x in p)+'\n')
        for t in f:out.write('f '+' '.join(str(int(x)+1) for x in t)+'\n')

def fit(values):
    js="""const fs=await import('node:fs');const mod=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync('web/human-studio/body-engine.js','utf8')).toString('base64'));const d=JSON.parse(fs.readFileSync('web/human-studio/assets/human.json','utf8'));const r=mod.fitDimensions(d,JSON.parse(process.argv[1]));console.log(JSON.stringify({vertices:d.bodyVertexIds.map(i=>Array.from(r.positions.slice(i*3,i*3+3))),faces:Array.from({length:d.indices.length/3},(_,i)=>d.indices.slice(i*3,i*3+3)),joints:{units:'cm',joints:d.bones.map(b=>({name:b.name,parent:b.parent,position:mod.jointPosition(d,r.positions,b.head)}))},state:{version:mod.MODEL_VERSION,units:'cm',dimensions:r.targets,morphWeights:r.weights,measuredNeutral:r.measurements,poseDegrees:{}}}));"""
    return json.loads(subprocess.check_output(['node','--input-type=module','-e',js,json.dumps(values)],cwd=ROOT,text=True))

def camera():
    views={name:{'axis':axis,'center_cm':[0,92],'px_per_cm':2.4} for name,axis in [('front','front'),('side','side'),('back','back'),('close-up','front'),('pose','side'),('depth','side')]}
    views['close-up']={'axis':'front','center_cm':[0,142],'px_per_cm':4.8}
    return {'projection':'orthographic','source_up':'Y','units':'cm','width':384,'height':512,'depth_range_cm':[-90,90],'views':views}

def build():
    r=renderer();oracle=WORK/'private-oracle';oracle.mkdir(exist_ok=True)
    initial=fit({'height':170,'bust':90,'waist':70,'hips':96});target=fit({'height':172,'bust':94,'waist':73,'hips':101});c=camera()
    d=WORK/'fixtures/anatomical-fit';meshwrite(d/'initial.obj',initial['vertices'],initial['faces']);write(d/'initial-state.json',initial['state']);write(d/'camera.json',c);write(d/'initial-joints.json',initial['joints'])
    meshwrite(oracle/'fit-target.obj',target['vertices'],target['faces']);write(oracle/'fit-target-state.json',target['state']);write(oracle/'fit-target-joints.json',target['joints']);r.render(oracle/'fit-target.obj',c,oracle/'fit-reference-renders',target['joints']);r.render(d/'initial.obj',c,d/'initial-renders',initial['joints'])
    for view in ['front','side']:
        for suffix in ['.png','-mask.png']:(d/('reference-'+view+suffix)).write_bytes((oracle/'fit-reference-renders'/(view+suffix)).read_bytes())
    z=zipfile.ZipFile(ROOT/'docs/verification/human-studio-20261117/live/evidence.zip');d2=WORK/'fixtures/pose-depth-evidence';(d2/'source-posed.obj').write_bytes(z.read('human-posed-cm.obj'));state=json.loads(z.read('human-model.json'));write(d2/'source-state.json',state);write(d2/'camera.json',c)
    neutral=fit(state['dimensions']);meshwrite(d2/'source-neutral.obj',neutral['vertices'],neutral['faces']);g=json.loads(z.read('export-geometry.json'));parents={b['name']:b['parent'] for b in read(ROOT/'web/human-studio/assets/human.json')['bones']};joints={'units':'cm','joints':[dict(b,parent=parents[b['name']]) for b in g['bones']]};write(d2/'source-joints.json',joints);r.render(d2/'source-posed.obj',c,d2/'reference-renders',joints);write(oracle/'pose-source-state.json',state)
    specs={
      'anatomical-fit':{'fixture':'fixtures/anatomical-fit','prompt':"Fit the existing anatomical MakeHuman body to reference-front.png and reference-side.png and binary masks, using the supplied fixed orthographic cameras and centimetre scale. This is a synthetic anatomical control, not a photograph. Start from initial-state.json and initial.obj; use web/human-studio/assets/human.json and body-engine.js. Preserve source topology, Y-up centimetres and neutral pose. Save final.obj (13380 body vertices in source order), state.json (dimensions, morphWeights, poseDegrees), camera.json copied from fixture, metrics.json documenting fit metrics, overlays/front.png and overlays/side.png showing reference and candidate, and renders/{front,side,back,close-up,pose,depth}.png with corresponding {view}-mask.png. Render actual triangles; pose view uses this fixture's neutral source pose. Generic raster utility fixtures/render_mesh.py is available. Do not use image generation or claim recovered person measurements.", 'assertions':['valid_source_topology','fixed_camera','both_silhouettes_improve','state_mesh_consistency','six_actual_triangle_renders','aligned_geometry_depth','metrics_and_overlays']},
      'pose-depth-evidence':{'fixture':'fixtures/pose-depth-evidence','prompt':"Produce reproducible six-view evidence for this existing posed MakeHuman anatomical surface. This is a synthetic control, not a photograph. source-posed.obj was exported from the genuine skinned app with source-state.json; source-neutral.obj records the same body's neutral dimensions. Preserve the seated legs and flexed arms exactly, with Y-up centimetres and source vertex order. Save final.obj matching the posed source, neutral.obj matching the neutral source, state.json preserving dimensions and poseDegrees, camera.json copied from fixture, metrics.json reporting separate neutral and posed heights and the neutral tape measurements, and renders/{front,side,back,close-up,pose,depth}.png plus corresponding {view}-mask.png. Generic actual-triangle raster utility fixtures/render_mesh.py is available. Depth must correspond to the same projected posed triangles. Do not reconstruct from silhouette, substitute a standing pose, use image generation, or claim measurements of a photographed person.", 'assertions':['valid_source_topology','fixed_camera','posed_surface_preserved','neutral_dimensions_pose_state','six_actual_triangle_renders','aligned_geometry_depth','neutral_and_posed_height_metrics']}}
    limits={'valid_source_topology':'13380 finite vertices; exact 26756 source triangles and vertex order','fixed_camera':'camera.json exactly equals supplied metadata; no auto-fit','six_actual_triangle_renders':'Use supplied deterministic render_mesh.py; each six masks IoU >=0.99 against independent raw-OBJ projection; each render mean absolute pixel error <=2 against fixed triangle lighting; pose annotation colored pixels also have mean absolute error <=2','aligned_geometry_depth':'Single-channel uint8; 0 background, 1..254 maps fixed depth_range_cm; mean absolute error <=1 pixel; rawdepth.npy finite triangle depth within 0.001cm and depth-valid.png equals finite mask','both_silhouettes_improve':'Both front and side IoU >=0.97 and each improves >=0.01 from supplied initial body','state_mesh_consistency':'Neutral tape measures within 0.3 cm of state dimensions; vertices within 0.05 cm of engine fit for state dimensions; poseDegrees empty','metrics_and_overlays':'Nonempty metrics.json and front/side overlays of 384x512','posed_surface_preserved':'Every posed coordinate within 0.003 cm of actual source skinned surface','neutral_dimensions_pose_state':'Neutral coordinates within 0.003 cm and tapes within 0.03 cm; dimensions and poseDegrees exactly preserved','neutral_and_posed_height_metrics':'Both heights and all neutral tape metrics within 0.03 cm of independent geometry; neutral height exceeds seated height by >20 cm'}
    for spec in specs.values():
        spec['criteria']={key:limits[key] for key in spec['assertions']}
        spec['prompt']+=' Save joints.json with units cm and joints entries name,parent,position for all actual rig bones. For pose-depth preserve source-joints.json; for fit derive each bone head using body-engine jointPosition on the final full rest buffer (not compact surface). Render pose.png with actual projected skeleton points and parent lines, using render_mesh.py --joints joints.json. Also save renders/pose-joints.json (joints entries name,world_cm,pixel,visible and parent-child edges; visible means inside canvas), renders/depth.npy and renders/rawdepth.npy float32 nearest triangle camera-space depth (signed source X for side, larger is nearer, not camera distance) with -inf background, and renders/depth-valid.png uint8 finite mask. Use the supplied render_mesh.py for deterministic renders. Depth encoding: 0 background; 1..254 maps depth_range_cm. Frozen checks: '+json.dumps(spec['criteria'])
    write(WORK/'case-specs-anatomical.json',specs)
    for name,spec in specs.items():
        (WORK/spec['fixture']/'README.md').write_text(spec['prompt']+'\n\nAsset: web/human-studio/assets/human.json; source engine: web/human-studio/body-engine.js.\n')
    write(oracle/'provenance.json',{'asset_sha256':hashlib.sha256((ROOT/'web/human-studio/assets/human.json').read_bytes()).hexdigest(),'pose_archive':'docs/verification/human-studio-20261117/live/evidence.zip','scale':'fixed 2.4 pixels/cm at 384x512; close-up 4.8 pixels/cm','raster':'OpenCV triangle union, barycentric triangle depth; no loft'})

def iou(a,b):return float(np.logical_and(a,b).sum()/max(1,np.logical_or(a,b).sum()))
def image(path):
    a=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
    if a is None:raise ValueError('Missing/unreadable '+str(path))
    return a

def measures(v,data):
    out={}
    for c in data['controls']:
        p=v[np.array(c['path'],int)] if c['key']!='height' else v
        out[c['key']]=float(np.ptp(p[:,1])) if c['key']=='height' else float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
    return out

def grade(case,output,fixture_override=None):
    r=renderer();output=Path(output);fixture=Path(fixture_override) if fixture_override else WORK/'fixtures'/case;c=read(fixture/'camera.json');data=read(ROOT/'web/human-studio/assets/human.json');checks=[];evidence={};cache={}
    def check(name,fn):
        try:
            ok,detail=fn();checks.append({'text':name,'passed':bool(ok),'evidence':detail})
        except Exception as e:checks.append({'text':name,'passed':False,'evidence':type(e).__name__+': '+str(e)})
    def geometry():
        v,f=r.obj(output/'final.obj');expected=np.asarray(data['indices']).reshape(-1,3);cache.update(v=v,f=f)
        return len(v)==13380 and np.array_equal(f,expected),{'vertices':len(v),'triangles':len(f),'expected_triangles':len(expected)}
    check('valid_source_topology',geometry)
    check('fixed_camera',lambda:(read(output/'camera.json')==c,'Camera must equal supplied fixed camera including centimetre scale'))
    def rasters():
        expected=read(fixture/'source-joints.json') if case=='pose-depth-evidence' else fit(read(output/'state.json')['dimensions'])['joints']
        actual=read(output/'joints.json');ej=expected['joints'];aj=actual['joints']
        if actual['units']!='cm' or len(ej)!=len(aj):raise ValueError('Wrong joint schema/count')
        for a,b in zip(aj,ej):
            if a['name']!=b['name'] or a['parent']!=b['parent'] or np.max(np.abs(np.asarray(a['position'])-b['position']))>.003:raise ValueError('Joint mismatch '+b['name'])
        cache['raster']={view:r.raster(cache['v'],cache['f'],c,view,expected) for view in c['views']};return cache['raster']
    def six():
        rr=rasters();scores={};errors={}
        for view,(m,im,d,z) in rr.items():
            actual=image(output/'renders'/(view+'.png'));mask=image(output/'renders'/(view+'-mask.png'));scores[view]=iou(mask>127,m>127)
            expect=d if view=='depth' else im
            if actual.shape!=expect.shape:raise ValueError('Wrong image shape '+view)
            errors[view]=float(np.abs(actual.astype(float)-expect).mean())
            if view=='pose':
                annotated=(im[:,:,2]>240)&(im[:,:,0]<40)
                errors['pose_annotation']=float(np.abs(actual[annotated].astype(float)-im[annotated]).mean()) if annotated.any() else 999.0
        evidence.update(render_mask_iou=scores,render_mae=errors)
        return min(scores.values())>=.99 and max(errors.values())<=2,{'mask_iou':scores,'mean_absolute_pixel_error':errors}
    def depth():
        rr=cache.get('raster') or rasters();expected=rr['depth'][2];actual=image(output/'renders/depth.png')
        if actual.ndim!=2:raise ValueError('Depth must be single-channel uint8 fixed-range depth')
        error=float(np.abs(actual.astype(float)-expected.astype(float)).mean());raw=np.load(output/'renders/depth.npy',allow_pickle=False);truth=rr['depth'][3];valid=np.isfinite(truth);vm=image(output/'renders/depth-valid.png')>127
        if raw.shape!=truth.shape or not np.array_equal(np.isfinite(raw),valid) or not np.array_equal(vm,valid):raise ValueError('Raw depth validity mismatch')
        rawerr=float(np.max(np.abs(raw[valid]-truth[valid])));return actual.shape==expected.shape and error<=1 and rawerr<=.001,{'mean_absolute_depth_pixel_error':error,'encoding':'0 background; 1..254 fixed depth_range_cm'}
    if case=='anatomical-fit':
        def silhouettes():
            rr=rasters();iv,iff=r.obj(fixture/'initial.obj');vals={}
            for view in ['front','side']:
                ref=image(fixture/('reference-'+view+'-mask.png'))>127;before=iou(r.raster(iv,iff,c,view)[0]>127,ref);after=iou(rr[view][0]>127,ref);vals[view]={'initial_iou':before,'final_iou':after,'improvement':after-before}
            evidence['silhouettes']=vals;return all(x['final_iou']>=.97 and x['improvement']>=.01 for x in vals.values()),vals
        check('both_silhouettes_improve',silhouettes)
        def consistent():
            state=read(output/'state.json');actual=measures(cache['v'],data);delta={k:abs(actual[k]-float(state['dimensions'][k])) for k in actual};expected=fit(state['dimensions']);err=float(np.max(np.abs(cache['v']-np.asarray(expected['vertices']))));return max(delta.values())<=.3 and err<=.05 and not state.get('poseDegrees'),{'max_neutral_measure_error_cm':max(delta.values()),'max_engine_vertex_error_cm':err}
        check('state_mesh_consistency',consistent)
        check('six_actual_triangle_renders',six);check('aligned_geometry_depth',depth)
        def reports():
            metrics=read(output/'metrics.json');a=image(output/'overlays/front.png');b=image(output/'overlays/side.png');return bool(metrics) and a.shape[:2]==(512,384) and b.shape[:2]==(512,384),{'metrics_keys':list(metrics),'overlay_shapes':[list(a.shape),list(b.shape)]}
        check('metrics_and_overlays',reports)
    else:
        def pose():
            v,f=r.obj(fixture/'source-posed.obj');err=float(np.max(np.abs(cache['v']-v)));return err<=.003,{'max_source_vertex_error_cm':err}
        check('posed_surface_preserved',pose)
        def neutral():
            v,f=r.obj(output/'neutral.obj');source,sf=r.obj(fixture/'source-neutral.obj');state=read(output/'state.json');truth=read(fixture/'source-state.json');m=measures(v,data);cache['neutral_measure']=m;err=float(np.max(np.abs(v-source)));delta=max(abs(m[k]-truth['dimensions'][k]) for k in m)
            return err<=.003 and delta<=.03 and state['dimensions']==truth['dimensions'] and state['poseDegrees']==truth['poseDegrees'] and np.array_equal(f,sf),{'max_neutral_vertex_error_cm':err,'max_neutral_measure_error_cm':delta}
        check('neutral_dimensions_pose_state',neutral);check('six_actual_triangle_renders',six);check('aligned_geometry_depth',depth)
        def metrics():
            m=read(output/'metrics.json');nh=cache['neutral_measure']['height'];ph=float(np.ptp(cache['v'][:,1]));err=max(abs(float(m['neutral_height_cm'])-nh),abs(float(m['posed_height_cm'])-ph));tape=max(abs(float(m['neutral_measurements_cm'][k])-val) for k,val in cache['neutral_measure'].items());return err<=.03 and tape<=.03 and nh-ph>20,{'neutral_height_cm':nh,'posed_height_cm':ph,'reported_height_error_cm':err,'reported_tape_error_cm':tape}
        check('neutral_and_posed_height_metrics',metrics)
    result={'case':case,'checks':checks,'summary':{'passed':sum(x['passed'] for x in checks),'total':len(checks),'all_passed':all(x['passed'] for x in checks)},'evidence':evidence};output.mkdir(parents=True,exist_ok=True);write(output/'grading.json',result);return result
if __name__=='__main__':
    p=argparse.ArgumentParser();sp=p.add_subparsers(dest='command',required=True);sp.add_parser('build');g=sp.add_parser('grade');g.add_argument('--case',choices=['anatomical-fit','pose-depth-evidence'],required=True);g.add_argument('--output',type=Path,required=True);g.add_argument('--fixture',type=Path);a=p.parse_args()
    if a.command=='build':build()
    else:print(json.dumps(grade(a.case,a.output,a.fixture),indent=2))
