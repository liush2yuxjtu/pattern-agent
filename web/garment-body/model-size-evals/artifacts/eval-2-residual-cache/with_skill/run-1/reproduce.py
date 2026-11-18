#!/usr/bin/env python3
"""Reproduce only this run's read-only mesh export and provenance evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if p.name == 'model-size-skill-evals-20261118')
INPUTS = {'state': ROOT/'inputs/residual-cache/final-state.json',
          'asset': ROOT/'inputs/human.json', 'neutral_mesh': ROOT/'inputs/residual-cache/neutral.obj'}
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
before = {key: sha(path) for key, path in INPUTS.items()}
command = [sys.executable, str(OUT/'export_body_measurements.py'),
           '--state', str(INPUTS['state']), '--asset-json', str(INPUTS['asset']),
           '--neutral-mesh', str(INPUTS['neutral_mesh']),
           '--out', str(OUT/'measurements.model.json'), '--csv', str(OUT/'measurements.model.csv')]
started = datetime.now(timezone.utc).isoformat()
process = subprocess.run(command, text=True, capture_output=True)
(OUT/'command.stdout.txt').write_text(process.stdout)
(OUT/'command.stderr.txt').write_text(process.stderr)
after = {key: sha(path) for key, path in INPUTS.items()}
assert before == after, 'Input content changed during export'
trace = {'started_utc': started, 'command': command, 'exit_code': process.returncode,
         'input_hashes_before': before, 'input_hashes_after': after,
         'inputs_unchanged': before == after, 'total_tokens': None, 'total_time_seconds': None,
         'actions': ['Read saved state, matching asset and actual OBJ.',
                     'Verify version, centimetres, asset fingerprint, compact mapping, vertex count, topology and winding.',
                     'Replay saved morph coefficients only and compare every neutral vertex; no target fitting.',
                     'Measure actual neutral OBJ Y extent, declared closed tapes and two-landmark straight distances.',
                     'Compare measured results to control targets and separately inspect untrusted cached claims.'],
         'script_sha256': sha(OUT/'export_body_measurements.py')}
if process.returncode:
    (OUT/'TRACE.json').write_text(json.dumps(trace, indent=2)+'\n')
    raise SystemExit(process.returncode)
report = json.loads((OUT/'measurements.model.json').read_text())
state = json.loads(INPUTS['state'].read_text())
rows = report['measurements']
max_residual = max(abs(r['input_target_delta_cm']) for r in rows)
comparison = {'delta_definition': 'actual OBJ measurement minus control target, cm',
              'maximum_absolute_target_delta_cm': max_residual,
              'claimed_maximumTargetErrorCm_ignored': state.get('maximumTargetErrorCm'),
              'cached_measuredNeutral_ignored': state.get('measuredNeutral'),
              'measurements': [{k:r[k] for k in ('name','value_cm','body_parameter_target_cm','input_target_delta_cm')} for r in rows]}
(OUT/'control-comparison.json').write_text(json.dumps(comparison, indent=2)+'\n')
provenance = {'input_paths': {k:str(v) for k,v in INPUTS.items()}, 'input_sha256': before,
              'state_version': state['version'], 'asset_declared_sha256':state['asset'],
              'coordinates': {'axes':'X left/right, Y up, Z front/back', 'units':'cm'},
              'parameter_basis':'Saved supplied morph coefficients; original fitting/prior origin not independently known.',
              'measurement_definitions': [{k:r[k] for k in ('name','method','definition','source_vertices','source_mesh_vertex_indices')} for r in rows],
              'geometry_verification':report['geometry_verification'],
              'pose_degrees_sha256':hashlib.sha256(json.dumps(state['poseDegrees'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),
              'pose_joint_entries':len(state['poseDegrees']), 'pose_handling':'Unmodified input. Neutral dimensions do not use posed extent.',
              'source_script_sha256':sha(ROOT/'skill-new/scripts/export_body_measurements.py'),
              'executed_script_sha256':sha(OUT/'export_body_measurements.py')}
(OUT/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
trace['geometry_verification'] = report['geometry_verification']
trace['maximum_absolute_target_delta_cm'] = max_residual
trace['output_sha256'] = {p.name:sha(p) for p in [OUT/'measurements.model.json', OUT/'measurements.model.csv', OUT/'control-comparison.json', OUT/'provenance.json']}
(OUT/'TRACE.json').write_text(json.dumps(trace, indent=2)+'\n')
labels = {'height':'站立身高','bust':'胸围','waist':'腰围','hips':'臀围','shoulders':'肩峰标志点间距','upperArm':'上臂围','thigh':'大腿围','neck':'颈围','upperArmLength':'上臂标志点直线长','forearmLength':'前臂标志点直线长','thighLength':'大腿标志点直线长','calf':'小腿围'}
lines = ['# 已保存人体模型的实际复量', '',
'已从所给 neutral.obj 的实际顶点导出12项尺寸。资产指纹、顶点映射、三角面拓扑/绕序及逐顶点形变重建均验证对应。没有重新拟合、修改形体或姿态，也没有生成图像。', '',
f"独立重建最大逐顶点误差 {report['geometry_verification']['neutral_reconstruction_max_error_cm']:.10g} cm，允许误差 {report['geometry_verification']['tolerance_cm']} cm。实际表面含 {report['geometry_verification']['vertices']} 顶点、{report['geometry_verification']['triangles']} 三角形。", '',
'缓存 measuredNeutral 的12项均为1000，maximumTargetErrorCm 自报为0；两者均未用作测量来源。目标未完全达到，保留已保存形体的真实残差。差值定义为实测减控制目标。', '',
'| 尺寸 | 实测 cm | 控制目标 cm | 差值 cm |', '|---|---:|---:|---:|']
for row in rows:
    lines.append(f"| {labels[row['name']]} | {row['value_cm']:.6f} | {row['body_parameter_target_cm']:.6f} | {row['input_target_delta_cm']:+.6f} |")
lines += ['', f'最大绝对目标残差为 {max_residual:.6f} cm（腰围）。这不构成网格与状态不对应，而是保存形变没有达到控制目标。', '',
'身高取中性表面Y轴跨度；围度取资源声明的闭合表面带尺折线；肩部及肢体长取资源声明的两个表面标志点直线距离。带尺围度并非平面截面周长，肢体标志点长并非骨段长。完整顶点路径、compact映射和定义见 measurements.model.json / provenance.json。', '',
'模型实测不能证明照片中真人的尺寸准确性。所给状态的姿态保持不变；没有提供 posed 网格，因此未验证摆姿蒙皮。胸点距、下胸围、肩斜、前后腰节长和裆弧不属于本次12项资源定义，不另行推断。', '',
'复现：在任何目录执行 `python '+str(OUT/'reproduce.py')+'`。该脚本只在本 outputs 目录写入产物，输入文件哈希执行前后核对一致。实际执行命令、退出状态、来源哈希见 TRACE.json；stdout/stderr分别留存。总token和总耗时不可知，均记录null。', '']
(OUT/'report.md').write_text('\n'.join(lines))
print(json.dumps({'exported_measurements':len(rows),'geometry_verification':report['geometry_verification'],'maximum_absolute_target_delta_cm':max_residual,'inputs_unchanged':before==after},indent=2))
