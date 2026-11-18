#!/usr/bin/env python3
"""Review cues from actual Y-up, cm FK joints; never a photo-fit or collision PASS."""
import argparse
import hashlib
import json
import math
from pathlib import Path

def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def length(a):return math.sqrt(dot(a,a))
def unit(a):
    n=length(a)
    if n<1e-8:raise ValueError('Degenerate skeletal direction')
    return [x/n for x in a]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def angle(a,b):return math.degrees(math.acos(max(-1,min(1,dot(unit(a),unit(b))))))

def audit(joint_data,state,profile='unconstrained',pocket_sides=('L','R')):
    if state.get('units')!='cm':raise ValueError('State must explicitly use cm')
    if profile not in ('unconstrained','standing-relaxed','front-pocket'):raise ValueError('Unknown observed gesture profile')
    rows=joint_data.get('joints')
    if not isinstance(rows,list):raise ValueError('Expected actual FK joints list')
    points={};parents={}
    for row in rows:
        p=row.get('position')
        if not isinstance(p,list) or len(p)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in p):raise ValueError('Invalid FK position')
        if row['name'] in points:raise ValueError('Duplicate joint name')
        points[row['name']]=p;parents[row['name']]=row.get('parent')
    needed=['root','neck01','upperleg01.L','upperleg01.R']+[name+side for side in ('L','R') for name in ('upperarm01.','lowerarm01.','wrist.')]
    if any(n not in points for n in needed):raise ValueError('Missing required Human Studio joints')
    up=[0,1,0];torso=sub(points['neck01'],points['root'])
    forward=unit(cross(sub(points['upperleg01.L'],points['upperleg01.R']),up))
    tilt=angle(torso,up); chain=[];node='neck01';seen=set()
    while node in points:
        if node in seen:raise ValueError('Cyclic FK hierarchy')
        seen.add(node);chain.append(node)
        if node=='root':break
        node=parents[node]
    if chain[-1]!='root':raise ValueError('Neck hierarchy must connect to root')
    chain.reverse();segment_tilts=[{'from':a,'to':b,'tilt_from_up_deg':angle(sub(points[b],points[a]),up)} for a,b in zip(chain,chain[1:]) if length(sub(points[b],points[a]))>1e-8]
    flags=[]
    if profile!='unconstrained':
        if tilt>15:flags.append('Standing torso leans over 15deg: inspect real side/back and source action.')
        if any(s['tilt_from_up_deg']>35 for s in segment_tilts):flags.append('Accumulated spine/neck chain has a segment tilted over 35deg; per-joint bounds alone are insufficient.')
    arms={}
    for side in ('L','R'):
        shoulder,elbow,wrist=[points[x+side] for x in ('upperarm01.','lowerarm01.','wrist.')]
        upper,lower=sub(elbow,shoulder),sub(wrist,elbow)
        arms[side]={'elbow_flexion_deg':angle(upper,lower),'upper_arm_posterior_sweep_cm':-dot(upper,forward),'wrist_anterior_from_pelvis_cm':dot(sub(wrist,points['root']),forward)}
        if profile=='standing-relaxed':
            if arms[side]['elbow_flexion_deg']>35:flags.append(side+': relaxed-arm prior conflicts with >35deg elbow flexion; verify against original visible arm.')
            if arms[side]['upper_arm_posterior_sweep_cm']>3:flags.append(side+': upper arm sweeps posteriorly >3cm in body frame; inspect side view, not just projected wrist.')
        if profile=='front-pocket' and side in pocket_sides and arms[side]['wrist_anterior_from_pelvis_cm'] < -3:flags.append(side+': wrist lies posterior to pelvis despite front-pocket profile; hidden precise location remains unknown.')
    nonsteps=[]
    for bone,values in state.get('poseDegrees',{}).items():
        if not isinstance(values,list) or len(values)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in values):raise ValueError('Invalid saved pose triple')
        for axis,value in enumerate(values):
            if abs(value-round(value*10)/10)>1e-7:nonsteps.append({'bone':bone,'axis':axis,'value':value})
    if nonsteps:flags.append('Pose is not on editor 0.1deg steps: normalize and rebuild all geometry before freezing generation inputs.')
    return {'scope':'Review heuristics, not detector truth, pose-fit acceptance or collision simulation. Thresholds are declared diagnostic priors, not evaluator gates.',
        'profile':profile,'pocket_sides':list(pocket_sides) if profile=='front-pocket' else [],'coordinate_system':'Human Studio Y-up; hip L minus R defines lateral axis, anterior is lateral cross up; cm',
        'torso_lean_deg':tilt,'spine_neck_chain':segment_tilts,'body_forward_axis':forward,'arms':arms,
        'non_editor_pose_values':nonsteps,'review_flags':flags,'acceptance':'NOT_ASSESSED',
        'limitations':['No original-photo landmark accuracy or true person measurements are evaluated.','Gesture profile must be selected from the actual reference, never automatically assumed.','No skin collision, cloth contact or balance/centre-of-mass proof.','Named joints avoid solver parameter-index ambiguity; source FK/mesh consistency still needs independent verification.']}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--joints',type=Path,required=True);parser.add_argument('--state',type=Path,required=True);parser.add_argument('--profile',choices=['unconstrained','standing-relaxed','front-pocket'],default='unconstrained');parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--pocket-side',choices=['L','R','both'],default='both',help='Subject side actually assigned the front-pocket prior, not image-left/right')
    args=parser.parse_args();result=audit(json.loads(args.joints.read_text()),json.loads(args.state.read_text()),args.profile,('L','R') if args.pocket_side=='both' else (args.pocket_side,))
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.joints,args.state)}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'review_flags':len(result['review_flags']),'acceptance':'NOT_ASSESSED'}))

if __name__=='__main__':main()
