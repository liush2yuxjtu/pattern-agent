#!/usr/bin/env python3
"""Fit articulated arm/pinch pose to case-supplied pixel and surface constraints.

Same saved anatomical mesh supplies every view. No photograph-specific coordinates
live here. This is conditional 3D pose fitting, not recovery of a person's truth.
"""
from pathlib import Path
import argparse,copy,hashlib,json,time
import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from runtime import Runtime,sha
import render_mesh


def write(p,v):
    Path(p).write_text(json.dumps(v,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item())+'\n')


def fit(case_path,initial_path,camera_path,out):
    case_path=Path(case_path);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    case=json.loads(case_path.read_text());
    if case.get('schema')!='pose-grip-case-v1':raise ValueError('Unsupported grip case schema')
    source=json.loads(Path(initial_path).read_text());camera=json.loads(Path(camera_path).read_text())
    c=np.asarray(camera['final'],float);width,height=camera['width'],camera['height'];R=Rotation.from_euler('YXZ',c[3:],degrees=True).as_matrix()
    r=Runtime()
    try:
        if case.get('asset_sha256') and case['asset_sha256']!=sha(r.asset):raise ValueError('Case asset does not match runtime')
        e=r.evaluate(source);shape=e['shape'];rest=shape['rest'];shape['tails']=np.array([rest[r.data['joints'][b['tail']]].mean(0) for b in r.bones])
        floor=float(e['floor_cm'])
        arm_bones=[i for i,n in enumerate(r.names) if n.startswith(('upperarm','lowerarm','wrist','finger'))]
        arm_ids=r.ids[(np.isin(r.skin,arm_bones)*r.weight).sum(1)[r.ids]>.5][::4]
        hand_ids={side:r.ids[(np.isin(r.skin,[i for i,n in enumerate(r.names) if n.endswith('.'+side) and n.startswith(('finger','wrist'))])*r.weight).sum(1)[r.ids]>.5][::3] for side in case['hands']}
        terminal_ids={(side,digit):r.ids[(r.weight*(r.skin==r.index[f'finger{digit}-3.{side}'])).sum(1)[r.ids]>.4] for side in case['hands'] for digit in [1,2]}
        sample_ids=np.unique(np.concatenate([arm_ids,*hand_ids.values(),*terminal_ids.values()]));sample_lookup={int(v):i for i,v in enumerate(sample_ids)};hand_idx={side:np.array([sample_lookup[int(v)] for v in ids]) for side,ids in hand_ids.items()}
        terminal_idx={key:np.array([sample_lookup[int(v)] for v in ids]) for key,ids in terminal_ids.items()}
        arm_idx=np.array([sample_lookup[int(v)] for v in arm_ids])
        containment=None
        if case.get('containment_mask'):
            maskpath=Path(case['containment_mask']);maskpath=maskpath if maskpath.is_absolute() else case_path.parent/maskpath;mask=cv2.imread(str(maskpath),0)
            if mask is None or mask.shape!=(height,width):raise ValueError('Containment mask size mismatch')
            containment=cv2.distanceTransform((mask==0).astype('uint8'),cv2.DIST_L2,5)
        pose0=np.array([source['poseDegrees'].get(n,[0,0,0]) for n in r.names]);vs=e['posed']@R.T
        trunkbones=[i for i,n in enumerate(r.names) if n.startswith(tuple(case.get('trunk_bone_prefixes',['spine','pelvis','root']))) ]
        trunkvertex=(np.isin(r.skin,trunkbones)*r.weight).sum(1)>float(case.get('trunk_skin_weight_min',.7))
        faces=r.faces[trunkvertex[r.faces].all(1)];tri=vs[faces]
        def project(p):
            q=np.asarray(p)@R.T
            return np.c_[width/2+(q[:,0]-c[1])*c[0],height/2-(q[:,1]-c[2])*c[0]]
        def unproject(uv,depth):return np.array([(uv[0]-width/2)/c[0]+c[1],(height/2-uv[1])/c[0]+c[2],depth])@R
        def depth_at(uv):
            xy=np.array([(uv[0]-width/2)/c[0]+c[1],(height/2-uv[1])/c[0]+c[2]])
            a=tri[:,0,:2];b=tri[:,1,:2]-a;cc=tri[:,2,:2]-a;d=xy-a;det=b[:,0]*cc[:,1]-b[:,1]*cc[:,0]
            with np.errstate(divide='ignore',invalid='ignore'):
                p=(d[:,0]*cc[:,1]-d[:,1]*cc[:,0])/det;q=(b[:,0]*d[:,1]-b[:,1]*d[:,0])/det
            good=(p>=0)&(q>=0)&(p+q<=1)&(abs(det)>1e-8)
            if not good.any():raise ValueError('MCP/pinch target ray misses real trunk surface: '+str(uv))
            z=tri[:,0,2]+p*(tri[:,1,2]-tri[:,0,2])+q*(tri[:,2,2]-tri[:,0,2]);return float(z[good].max())
        points={};pinchtargets={};surfaceaudit={}
        for side,info in case['hands'].items():
            dep=depth_at(info['mcp_surface_uv']);surfaceaudit[side]={'surface_camera_depth_cm':dep,'actual_triangle_hit':True}
            for name,uv in info['joint_uv'].items():
                offset=info['wrist_offset_cm'] if name=='wrist' else info['mcp_offset_cm'];points[name+'.'+side]=unproject(uv,dep+offset)
            pinchtargets[side]=unproject(info['pinch_uv'],depth_at(info['pinch_uv'])+info['pinch_offset_cm'])
        history=[]
        def optimize(input_pose,with_fingers,stage):
            stagepose=input_pose.copy()
            keys=[(n,i) for side in case['hands'] for n in ['upperarm01.'+side,'lowerarm01.'+side,'wrist.'+side] for i in range(3)]
            if with_fingers:keys += [(f'finger{digit}-{seg}.{side}',i) for side in case['hands'] for digit in [1,2] for seg in [1,2,3] for i in range(3)]
            initial=np.array([stagepose[r.index[n],i] for n,i in keys]);lo=[];hi=[]
            for n,i in keys:
                l,h=(-175,175)
                if n.startswith('lowerarm') and i==0:l,h=(-5,145)
                if n.startswith('wrist'):l,h=(-90,90)
                if n.startswith('finger1'):l,h=((0,115) if i==0 else (-70,70))
                if n.startswith('finger2'):l,h=((0,120) if i==0 else (-15,15))
                lo.append(l);hi.append(h)
            def fk(pp):
                angles=stagepose.copy()
                for (n,i),val in zip(keys,pp):angles[r.index[n],i]=val
                rot=shape['rest_rot']@Rotation.from_euler('XYZ',angles,degrees=True).as_matrix();g=np.zeros_like(rot);w=np.zeros_like(shape['heads'])
                for i in r.order:
                    parent=r.parent[i];g[i]=g[parent]@rot[i] if parent>=0 else rot[i];w[i]=w[parent]+g[parent]@shape['translations'][i] if parent>=0 else shape['translations'][i]
                w[:,1]-=floor
                return w,g
            def residual(pp):
                w,g=fk(pp);rr=[]
                # Actual LBS surface samples use the same floor-corrected world frame as exported skin.
                matrix=g@shape['frames'].transpose(0,2,1);offset=w-np.einsum('nij,nj->ni',matrix,shape['heads']);sv=np.zeros((len(sample_ids),3))
                for k in range(4):
                    si=r.skin[sample_ids,k];sv+=r.weight[sample_ids,k,None]*(np.einsum('nij,nj->ni',matrix[si],rest[sample_ids])+offset[si])
                if containment is not None:
                    q=project(sv[arm_idx]);dist=map_coordinates(containment,[q[:,1],q[:,0]],order=1,mode='nearest');rr.extend((np.maximum(0,dist-2)/4*np.sqrt(50/len(q))).tolist())
                if len(hand_idx)==2 and case.get('interhand_clearance_cm',0)>0:
                    sides=list(hand_idx);a=sv[hand_idx[sides[0]]];b=sv[hand_idx[sides[1]]];dd=cKDTree(a).query(b)[0];rr.extend((np.maximum(0,case['interhand_clearance_cm']-dd)/.2*np.sqrt(40/len(b))).tolist())
                if case.get('terminal_skin_clearance_cm',0)>0:
                    for side in case['hands']:
                        aa=sv[terminal_idx[(side,1)]];bb=sv[terminal_idx[(side,2)]];dd=cKDTree(aa).query(bb)[0];rr.extend((np.maximum(0,case['terminal_skin_clearance_cm']-dd)/.08*np.sqrt(20/len(bb))).tolist())
                for name,target in points.items():rr.extend((w[r.index[name]]-target)/(case.get('wrist_sigma_cm',.75) if name.startswith('wrist') else case.get('mcp_sigma_cm',.7)))
                pinches=[]
                for side,info in case['hands'].items():
                    if with_fingers:
                        tips=[]
                        for digit in [1,2]:
                            bi=r.index[f'finger{digit}-3.{side}'];local=shape['frames'][bi].T@(shape['tails'][bi]-shape['heads'][bi]);tips.append(w[bi]+g[bi]@local)
                        center=np.mean(tips,0);pinches.append(center);rr.append((np.linalg.norm(tips[0]-tips[1])-case.get('pinch_helper_tail_gap_cm',0))/case.get('pinch_gap_sigma_cm',.4));rr.extend((center-pinchtargets[side])/case.get('pinch_target_sigma_cm',.6))
                    wrist=w[r.index['wrist.'+side]];a=w[r.index['finger2-1.'+side]]-wrist;b=w[r.index['finger5-1.'+side]]-wrist;n=np.cross(a,b);n/=max(np.linalg.norm(n),1e-12)
                    # Sign is asset-specific and declared in the case, not inferred from hand label.
                    desired=R[2]*info['palm_cross_camera_sign'];rr.extend((n-desired)/case.get('normal_sigma',.2))
                    if info.get('elbow_uv') is not None:rr.extend((project([w[r.index['lowerarm01.'+side]]])[0]-info['elbow_uv'])/info.get('elbow_sigma_px',22))
                if len(pinches)==2:rr.append(max(0,np.linalg.norm(pinches[0]-pinches[1])-case.get('pinch_centers_soft_max_cm',6))/.5)
                rr.extend((pp-initial)/case.get('pose_regularizer_deg',120));return np.asarray(rr)
            best=None
            for seed in range(int(case.get('restarts',3))):
                x=initial.copy()
                if seed:x+=np.random.default_rng(seed).normal(0,float(case.get('restart_sigma_deg',15)),len(x))
                x=np.clip(x,np.array(lo)+1e-4,np.array(hi)-1e-4);t=time.time();res=least_squares(residual,x,bounds=(lo,hi),max_nfev=int(case.get('max_nfev',150)),ftol=1e-7,xtol=1e-7,diff_step=.001)
                loss=float(res.fun@res.fun);history.append({'stage':stage,'seed':seed,'loss':loss,'nfev':res.nfev,'seconds':time.time()-t});print(stage,seed,loss,res.nfev,flush=True)
                if best is None or loss<best.fun@best.fun:best=res
            for (n,i),val in zip(keys,best.x):stagepose[r.index[n],i]=val
            return stagepose
        pose=optimize(pose0,False,'surface-contact');pose=optimize(pose,True,'thumb-index-pinch')
        state=copy.deepcopy(source)
        for i,n in enumerate(r.names):state['poseDegrees'][n]=np.round(pose[i],1).tolist()
        state=r.canonical_state(state);result=r.evaluate(state)
        if abs(result['floor_cm']-floor)>1e-6:raise ValueError('Arm pose unexpectedly changed floor; fixed floor FK assumption invalid')
        write(out/'final-state.json',state);write(out/'camera.json',camera);write(out/'history.json',history)
        r.write_obj(out/'neutral.obj',result['shape']['rest']);r.write_obj(out/'posed.obj',result['posed'])
        viewcam=copy.deepcopy(case.get('render_camera',dict(width=768,height=1152,depth_range_cm=[-100,100],views={v:dict(axis=axis,px_per_cm=6,center_cm=[0,85]) for v,axis in [('front','front'),('side','side'),('back','back'),('closeup','front'),('pose','front'),('depth','front')]})));
        if 'closeup' in viewcam['views'] and 'render_camera' not in case:
            viewcam['views']['closeup'].update(px_per_cm=15,center_cm=[0,126])
        r.save(state,viewcam,out/'views')
        projections={}
        for view in viewcam['views']:
            uv=r.project(result['joints'],viewcam,view);rows=[]
            for i,name in enumerate(r.names):
                rows.append(dict(name=name,parent=r.bones[i]['parent'],world_cm=result['joints'][i].tolist(),pixel=uv[i].tolist(),inside_canvas=bool(0<=uv[i,0]<viewcam['width'] and 0<=uv[i,1]<viewcam['height']),occlusion='NOT_ESTIMATED: skeletal joint lies under skin; do not infer visible surface from bone depth'))
            projections[view]=dict(camera=viewcam['views'][view],canvas=[viewcam['width'],viewcam['height']],joints=rows,state_sha256=sha(out/'final-state.json'),posed_sha256=sha(out/'posed.obj'))
        write(out/'views/joint-projections.json',projections)
        pc=dict(width=width,height=height,depth_range_cm=[-100,100],views={'photo':dict(axis='front',px_per_cm=float(c[0]),center_cm=c[1:3].tolist())});mask,img,depth,z=render_mesh.raster(result['posed']@R.T,r.faces,pc,'photo');cv2.imwrite(str(out/'photo-render.png'),img);cv2.imwrite(str(out/'photo-mask.png'),mask)
        diagnostics={};centers=[]
        for side in case['hands']:
            tips=[]
            for digit in [1,2]:
                bi=r.index[f'finger{digit}-3.{side}'];tips.append(result['posed'][r.data['joints'][r.bones[bi]['tail']]].mean(0))
            centers.append(np.mean(tips,0));w=result['joints'][r.index['wrist.'+side]];a=result['joints'][r.index['finger2-1.'+side]]-w;b=result['joints'][r.index['finger5-1.'+side]]-w;n=np.cross(a,b);n/=np.linalg.norm(n)
            diagnostics[side]={'thumb_tip_cm':tips[0],'index_tip_cm':tips[1],'tip_gap_cm':float(np.linalg.norm(tips[0]-tips[1])),'palm_cross_world':n,'palm_cross_camera':n@R.T,'wrist_cm':w}
        write(out/'diagnostics.json',dict(hands=diagnostics,pinch_centers_distance_cm=float(np.linalg.norm(centers[0]-centers[1])) if len(centers)==2 else None,frame=dict(units='cm',axes='X lateral,Y up,Z front',source_floor_cm=floor,final_floor_cm=float(result['floor_cm']),fast_fk_and_lbs_apply_same_floor=True,floor_definition='subtract actual posed body minimumY; constant lower-body frame during arm-only solve'),fingertip_definition='Mean of skinned helper tail groups, not visible finger surface; terminal skin repulsion and independent triangle audit are separate',surface_depth_targets=surfaceaudit,world_targets_cm=points,pinch_targets_cm=pinchtargets,dimensions_unchanged=state['dimensions']==source['dimensions'],camera_unchanged=True,assumptions=case.get('assumptions',[])))
        write(out/'provenance.json',dict(case_sha256=sha(case_path),initial_state_sha256=sha(initial_path),camera_sha256=sha(camera_path),solver_sha256=sha(__file__),asset_sha256=sha(r.asset),state_sha256=sha(out/'final-state.json'),neutral_sha256=sha(out/'neutral.obj'),posed_sha256=sha(out/'posed.obj'),only_pose_changed=True,frame=dict(units='cm',axes='X lateral,Y up,Z front',source_floor_cm=floor,final_floor_cm=float(result['floor_cm']),fast_fk_and_lbs_apply_same_floor=True),external_mask=None if containment is None else dict(path=str(maskpath.resolve()),sha256=sha(maskpath))))
    finally:r.close()


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--case',required=True);ap.add_argument('--initial-state',required=True);ap.add_argument('--camera',required=True);ap.add_argument('--out',required=True);args=ap.parse_args();fit(args.case,args.initial_state,args.camera,args.out)
