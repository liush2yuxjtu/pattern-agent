#!/usr/bin/env python3
"""Reconstruct shape without fitting; verify supplied OBJ then measure OBJ vertices.
Run from any directory: python /absolute/path/to/outputs/measure.py
All input files are read only. Outputs are confined to this script's directory.
"""
import csv, hashlib, json, platform, sys
from pathlib import Path
import numpy as np
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
INPUTS = {'state': ROOT/'inputs/residual-cache/final-state.json', 'asset': ROOT/'inputs/human.json', 'mesh': ROOT/'inputs/residual-cache/neutral.obj'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name, data): (OUT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
hashes = {k:sha(p) for k,p in INPUTS.items()}
s = json.loads(INPUTS['state'].read_text()); a = json.loads(INPUTS['asset'].read_text())
assert a['schema']==1 and a['unit']=='cm' and s['units']=='cm'
assert s['version']=='makehuman-cm-rig-v1'
assert hashes['asset']==s['asset'], 'Resource SHA256 differs from saved state'
controls = a['controls']; ids = np.array(a['bodyVertexIds'], dtype=int)
rest = np.array(a['vertices'],dtype=float).reshape(-1,3)
assert len(controls)==len(s['morphWeights'])==12
for c,w in zip(controls,s['morphWeights']):
    assert np.isfinite(w) and -2<=w<=2
    d=np.array(c['incr' if w>=0 else 'decr'],dtype=float)
    np.add.at(rest,d[:,0].astype(int),abs(w)*d[:,1:])
expected = rest[ids].copy(); expected[:,1] -= expected[:,1].min()
vertices=[]; faces=[]
for l in INPUTS['mesh'].read_text().splitlines():
    t=l.split()
    if not t: continue
    if t[0]=='v': vertices.append([float(x) for x in t[1:4]])
    if t[0]=='f': faces.append([int(x.split('/')[0])-1 for x in t[1:]])
v=np.array(vertices); f=np.array(faces,dtype=int)
assert v.shape==expected.shape and np.isfinite(v).all()
assert len(set(ids.tolist()))==len(ids)
remap={int(original):compact for compact,original in enumerate(ids)}
expected_faces=np.array([[remap[int(i)] for i in tri] for tri in np.array(a['indices']).reshape(-1,3)])
assert np.array_equal(f,expected_faces), 'OBJ topology/order differs from authored surface'
errors=np.linalg.norm(v-expected,axis=1)
# 0.0001 cm accommodates Float32 vertex export and nine decimal OBJ precision.
tolerance=1e-4
assert float(errors.max()) < tolerance, 'OBJ does not match independently reconstructed neutral surface'
rows=[]
lengths={'shoulders','upperArmLength','forearmLength','thighLength'}
for c in controls:
    k=c['key']; path=c['path']; compact=[remap[int(i)] for i in path]
    if k=='height':
        value=float(np.ptp(v[:,1])); definition='Neutral standing height: max surface Y minus min surface Y'; method='standing_height'; recon=float(np.ptp(expected[:,1]))
    else:
        q=v[compact]; r=expected[compact]
        value=float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum());recon=float(np.linalg.norm(np.diff(r,axis=0),axis=1).sum())
        method='landmark_distance' if k in lengths else 'surface_tape_path'
        definition=('Euclidean straight distance between authored surface landmarks' if k in lengths else 'Sum of consecutive Euclidean mesh landmark tape segments; closed authored nonplanar path, not a plane-intersection circumference')
    rows.append(dict(name=k,value=value,unit='cm',method=method,definition=definition,asset_path_vertex_ids=path,obj_path_vertex_indices_zero_based=compact,target_cm=s['dimensions'][k],difference_cm=value-s['dimensions'][k],reconstructed_cm=recon,obj_minus_reconstruction_cm=value-recon,basis='mesh_parameter',mesh_checked=True,source='supplied neutral.obj actual vertex coordinates',mesh_sha256=hashes['mesh'],cached_reported_cm=s['measuredNeutral'].get(k),cache_used=False,limitations=['Model dimensions, not measurements of a photographed human.']))
max_error=max(abs(x['difference_cm']) for x in rows)
cache_diff=max(abs(x['value']-x['cached_reported_cm']) for x in rows)
check=dict(status='verified_neutral_mesh',asset_fingerprint_matches=True,vertex_count=len(v),triangle_count=len(f),topology_matches=True,correspondence='Authored original bodyVertexIds to compact OBJ index; exact face array and all corresponding vertices checked',neutral_reconstruction='asset vertices + abs(saved morph weight) * corresponding incr/decr sparse delta; translate surface minimum Y to zero',maximum_vertex_distance_cm=float(errors.max()),mean_vertex_distance_cm=float(errors.mean()),vertex_tolerance_cm=tolerance,maximum_absolute_measurement_reconstruction_difference_cm=max(abs(x['obj_minus_reconstruction_cm']) for x in rows),bounds_cm={'min':v.min(0).tolist(),'max':v.max(0).tolist()},nonzero_saved_pose={k:t for k,t in s['poseDegrees'].items() if any(t)},pose_note='The state contains nonzero pose rotations. Dimensions deliberately use independently verified neutral geometry; no pose was applied, modified or inferred from the filename.',cached_maximumTargetErrorCm=s['maximumTargetErrorCm'],cached_values_reliable=False,maximum_cache_discrepancy_cm=cache_diff,maximum_actual_target_error_cm=max_error,target_tolerance_cm=0.2,all_targets_within_tolerance=max_error<=0.2,cache_reason='Saved 12 measuredNeutral entries are 1000 cm while maximumTargetErrorCm is 0; neither is used for measurement or correspondence.')
provenance=dict(inputs={k:{'path':str(p.relative_to(ROOT)),'sha256':hashes[k]} for k,p in INPUTS.items()},model_version=s['version'],asset_name=a['name'],asset_license=a['license'],coordinate_system='X left/right, Y up, Z front/back; cm. No scaling or rotation applied.',state_unchanged=True,shape_and_pose_unchanged=True,python=sys.version,numpy=np.__version__,platform=platform.platform(),script_sha256=sha(Path(__file__)),total_tokens=None,total_time_seconds=None)
write('correspondence.json',check);write('provenance.json',provenance)
write('measurements.json',dict(status='success',scope='12 actual neutral model dimensions; corrupt saved measurement cache rejected',units='cm',measurements=rows,maximumTargetErrorCm=max_error,all_targets_within_0_2_cm=max_error<=0.2,source_fingerprints=hashes,limitations=['Morph targets are control requests, not attained dimensions.','Surface tape definitions are authored model paths, not VTK planar sections.','Neutral dimensions do not certify posed skinning or real human accuracy.']))
fields=['name','value','unit','method','target_cm','difference_cm','basis','mesh_checked','source','mesh_sha256','definition','asset_path_vertex_ids','obj_path_vertex_indices_zero_based','cached_reported_cm','cache_used']
with (OUT/'measurements.csv').open('w',newline='') as h:
    writer=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
assert {k:sha(p) for k,p in INPUTS.items()}==hashes, 'Input mutated during execution'
write('TRACE.json',dict(events=[{'step':'read_and_hash_inputs','sha256':hashes},{'step':'resource_fingerprint','matched':True},{'step':'reconstruct_from_saved_weights','refit':False,'pose_modified':False},{'step':'parse_and_compare_actual_obj','maximum_vertex_distance_cm':float(errors.max()),'topology_matches':True},{'step':'measure_actual_obj','measurement_count':len(rows),'cache_used':False},{'step':'compare_targets','maximum_residual_cm':max_error},{'step':'rehash_inputs','unchanged':True}],total_tokens=None,total_time_seconds=None))
report=['# 实际模型尺寸交付','', '已从提供的 neutral.obj 实际顶点计算12项尺寸，并用 human.json 与保存的 morphWeights 独立重建全部中性表面顶点及拓扑，证明对应关系。没有拟合、修改原始形体/姿态或生成图片。','',f"资源指纹匹配；{len(v)} 顶点、{len(f)} 三角形逐一对应。最大顶点差 {float(errors.max()):.10f} cm，小于事先采用的 {tolerance} cm 导出数值容差。",'', '缓存不可信：measuredNeutral 的12项均为1000 cm，且 maximumTargetErrorCm=0。全部忽略，仅在表中保留供审计。旧技能检查脚本会因自报字段矛盾而拒绝该状态；这不阻止用有效资源、权重和实际网格独立证明形体对应。','',f'实际尺寸相对控制目标的最大绝对差为 {max_error:.6f} cm；控制范围上限不代表能全部达到。以下差值定义为实际网格值减控制目标。','', '| 尺寸 | 实际 cm | 目标 cm | 差值 cm |','|---|---:|---:|---:|']
report += [f"| {r['name']} | {r['value']:.6f} | {r['target_cm']:.1f} | {r['difference_cm']:+.6f} |" for r in rows]
report += ['', '身高使用中性表面 Y 跨度；肩宽和四肢长度为资源指定表面标志点直线距离，其余为资源指定闭合表面带尺路径。每项路径索引、单位、定义、来源和指纹见 measurements.json；没有把截面围长与带尺混用。','', '状态有非零 poseDegrees，但本次提供的网格经数值核验为 neutral；中性尺寸不表示所存姿势下的包围盒或体段投影。原始完整姿态仍保存在输入文件，未改变；无需重拟合或清零原状态。','', '运行：在本 outputs 目录执行 `python measure.py`。`commands.txt` 保存了完整命令；TRACE.json、correspondence.json 与 provenance.json 记录复算步骤、容差、运行环境及输入哈希。','', '这些尺寸属于该人体模型，不等于真人实测；没有评价照片拟合、姿态蒙皮或衣物物理表现。总 tokens 与总时间无法可靠取得，记为 null。']
(OUT/'report.md').write_text('\n'.join(report)+'\n')
print(json.dumps({'status':'success','maximum_target_error_cm':max_error,'maximum_vertex_error_cm':float(errors.max()),'input_unchanged':True,'values':{r['name']:r['value'] for r in rows}},ensure_ascii=False))
