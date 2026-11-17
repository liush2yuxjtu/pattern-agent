from pathlib import Path
import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description='实际重复运行封闭案例CLI；不测LLM推理时间。')
p.add_argument('--runs',type=int,default=3);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if not 1<=a.runs<=20:p.error('runs须在1至20之间')
rounds=[];hashes={};timings={}
with tempfile.TemporaryDirectory(prefix='intent-edit-profile-') as tmp:
    for i in range(a.runs):
        out=Path(tmp)/str(i);started=time.perf_counter()
        r=subprocess.run([sys.executable,str(ROOT/'run_benchmark.py'),'--output',str(out)],capture_output=True,text=True)
        elapsed=time.perf_counter()-started
        if r.returncode:raise RuntimeError(r.stdout+r.stderr)
        rows=json.loads((out/'generation-results.json').read_text())
        actual=[v for v in rows if v.get('generation')=='PASS']
        if len(actual)!=4:raise ValueError('四个正向案例没有全部生成')
        for case in actual:
            cid=case['case'];pair=tuple(hashlib.sha256((out/cid/name).read_bytes()).hexdigest() for name in ['new-spec.yaml','output.dxf'])
            if cid in hashes and hashes[cid]!=pair:raise ValueError('重复运行结果不确定')
            hashes[cid]=pair;timings.setdefault(cid,[]).append(case['execution_seconds'])
        rounds.append({'round':i+1,'cli_wall_seconds':elapsed,'case_pipeline_seconds':{r['case']:r['execution_seconds'] for r in actual}})
result={'verdict':'PASS','runs':a.runs,'scope':'实际代码流水线耗时，含每例读取、变形、复算、规格补丁和DXF写出；不含子代理推理或独立审计。',
 'rounds':rounds,'cases':{cid:{'samples_seconds':values,'median_seconds':statistics.median(values),'min_seconds':min(values),'max_seconds':max(values),
   'deterministic_spec_sha256':hashes[cid][0],'deterministic_dxf_sha256':hashes[cid][1]} for cid,values in timings.items()},
 'model_inference_latency':'NOT_MEASURED','tokens_and_cost':'NOT_MEASURED','generalization':'四项单次子代理代码实现，不是开放任务统计成功率。'}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({cid:v['median_seconds'] for cid,v in result['cases'].items()},ensure_ascii=False))
