from pathlib import Path
import argparse
import importlib.util
import json
import re
import time
import traceback
import engine

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
INPUT=REPO/'patterns/fitted-tshirt'

def preflight(intent):
    model=engine.yaml.safe_load((INPUT/'input-spec.yaml').read_text())
    if ('厘米' in intent or 'cm' in intent.lower() or '毫米' in intent) and model['单位与坐标']['实际比例']['状态']!='已标定':
        return 'BLOCKED','基准每U毫米数未标定，不能把物理长度转换为U。'
    match=re.search(r'袖口.*减少\s*([0-9.]+)\s*U',intent)
    if match:
        target=model['关键尺寸']['项目']['袖口展开线长']['数值']-float(match[1])
        if target<=0:return 'REJECTED',f'计算所得目标袖口宽为{target:.6f}U，不大于零。'
    if ('舒服' in intent or '舒适' in intent) and not re.search(r'\d',intent):
        return 'BLOCKED','缺少动作、受限位置、允许改变范围和量化目标。'
    return 'BLOCKED','请求不在本次已实现的封闭案例目录内，需先生成和审核具体编辑代码。'

def main():
    parser=argparse.ArgumentParser(description='运行子代理编写的明确U单位设计案例；不是通用自然语言解析器。')
    parser.add_argument('--case',default='all')
    intent_group=parser.add_mutually_exclusive_group()
    intent_group.add_argument('--intent',help='已实现意图文本可执行；未支持请求经过预检后阻塞。')
    intent_group.add_argument('--intent-file',type=Path,help='读取自然语言意图文件，使用本次子代理已实现的封闭案例目录。')
    parser.add_argument('--output',type=Path,default=REPO/'work/intent-edit-benchmark/results')
    args=parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('输出目录必须为空，避免失败或阻塞案例误用上次生成的DXF。')
    args.output.mkdir(parents=True,exist_ok=True)
    results=[]
    if args.intent_file:args.intent=args.intent_file.read_text(encoding='utf-8').strip()
    if args.intent:
        selected=None
        for path in sorted((ROOT/'cases').glob('*.py')):
            spec=importlib.util.spec_from_file_location(path.stem,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            if args.intent.strip()==module.CASE['intent'].strip():selected=path.stem;break
        if selected:args.case=selected
        else:
            status,reason=preflight(args.intent)
            result={'intent':args.intent,'status':status,'reason':reason,'output_dxf':None,'new_spec':None}
            (args.output/'case-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(result,ensure_ascii=False));return
    for path in sorted((ROOT/'cases').glob('*.py')):
        if args.case!='all' and path.stem!=args.case:continue
        started=time.perf_counter()
        try:
            spec=importlib.util.spec_from_file_location(path.stem,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            result=engine.emit(module,INPUT/'input-spec.yaml',INPUT/'input.dxf',args.output/path.stem)
        except Exception as error:
            result={'case':path.stem,'generation':'FAIL','error':str(error),'traceback':traceback.format_exc()}
        result['execution_seconds']=round(time.perf_counter()-started,6);results.append(result)
        print(json.dumps(result,ensure_ascii=False),flush=True)
    if args.case=='all':
        controls=[('05_uncalibrated_cm','把袖子加长2厘米，其他保持。'),
          ('06_ambiguous_comfort','抬手更舒服，外观尽量保持。'),('07_invalid_cuff','袖口展开宽减少1000U。')]
        for cid,intent in controls:
            status,reason=preflight(intent)
            dest=args.output/cid;dest.mkdir(exist_ok=True)
            verdict={'case':cid,'intent':intent,'status':status,'reason':reason,'output_dxf':None,'new_spec':None}
            (dest/'case-result.json').write_text(json.dumps(verdict,ensure_ascii=False,indent=2)+'\n');(dest/'intent.txt').write_text(intent+'\n')
            results.append(verdict)
    (args.output/'generation-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    if any(x.get('generation')=='FAIL' for x in results):raise SystemExit(1)

if __name__=='__main__':main()
