#!/usr/bin/env python3
"""Run paired, tool-enabled zero-draft tasks in isolated working directories."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


HERE = Path(__file__).resolve().parent
CASES = json.loads((HERE / 'zero-draft-cases.json').read_text())['cases']
CONTRACT = '''
请在本次工作目录实际执行工具，生成产物。没有任何现成母版，不引用网络或其他目录中的服装轮廓。可用 Node、已固定版本的 FreeSewing core 和环境变量 PATTERN_EVAL_PYTHON 指向的 Python（含 ezdxf、reportlab、PyMuPDF、Shapely），无需联网安装。只在本次工作目录写文件，不打开或改动共享制版软件。

交付约定：outputs/ 下放源码和 rebuild.sh。必须能用 `sh outputs/rebuild.sh <输入 JSON 绝对路径> <新输出目录绝对路径>` 重建。输入由评测器提供，长度单位为毫米；top_mm、hem_mm 分别是每个完整裁片的上口和下摆宽度。对围裙 transition_mm 是肩胸过渡达到全宽的深度，从最高点向下算。实际运行 rebuild.sh 处理 base.json 和 revision.json，分别写到 outputs/base/ 和 outputs/revision/。各版应有 pattern.dxf、full.pdf、a4.pdf。DXF 用毫米，以闭合 LWPOLYLINE 在每个裁片的 `<裁片名>_NET` 与 `<裁片名>_CUT` 图层提供净线、裁剪线。净线在 CAD 坐标中保持“顶部在上、下摆在下”。各 PDF 放一个可量测的一百毫米矢量校准方框，整幅 PDF 保留裁片真实大小，A4 文件附页码、裁片名和拼接标记。英文标记可用于避免字体依赖。最终简报说明材料、缝份、松紧带或系带交接及实际验证范围。不要把没有进行的实体打印或试穿判为通过。
'''


def prepare(folder, case, skill, modules):
    folder.mkdir(parents=True)
    (folder / 'node_modules').symlink_to(modules, target_is_directory=True)
    for variant in ['base', 'revision']:
        (folder / f'{variant}.json').write_text(json.dumps(case[variant], indent=2) + '\n')
    instructions = ('Read ' + str(skill / 'SKILL.md') + ' and the linked relevant references before working. '
                    'That is the only assigned skill version. Use the same available local tools and do not inspect sibling trial directories.')
    spec = '裁片图层名称：' + ', '.join(case['pieces']) + '。'
    return instructions + '\n\n' + case['prompt'] + '\n' + CONTRACT + '\n' + spec


def run(folder, prompt, model, python, timeout):
    command = [
        'codex', '-a', 'never', 'exec', '--ignore-user-config', '--ignore-rules',
        '--ephemeral', '--skip-git-repo-check', '--json', '-C', str(folder),
        '-s', 'workspace-write', '-m', model, '-c', 'model_reasoning_effort="low"',
        '-c', 'web_search="disabled"', '--enable', 'skip_host_skill_discovery',
        '--disable', 'plugins', '--disable', 'tool_search',
        '--output-last-message', str(folder / 'reply.md'), '-',
    ]
    env = dict(os.environ, PATTERN_EVAL_PYTHON=str(python))
    start = time.perf_counter()
    with (folder/'events.jsonl').open('w') as events, (folder/'run.err').open('w') as err:
        try:
            code = subprocess.run(command, input=prompt, text=True, stdout=events, stderr=err,
                                  env=env, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 124
    elapsed = time.perf_counter() - start
    usage = {}
    for line in (folder/'events.jsonl').read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get('type') == 'turn.completed':
            usage = event.get('usage', {})
    timing = {'total_duration_seconds': elapsed, 'duration_ms': round(elapsed*1000),
              'total_tokens': sum(usage.get(key, 0) for key in ['input_tokens', 'output_tokens']) if usage else None,
              'exit_code': code, 'model': model}
    (folder/'timing.json').write_text(json.dumps(timing, indent=2) + '\n')
    print(f'{folder.parent.name}/{folder.name}: {code}, {elapsed:.1f}s', flush=True)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--node-modules', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--model', default='gpt-6.2-sol')
    parser.add_argument('--timeout', type=int, default=400)
    args = parser.parse_args()
    if not shutil.which('codex') or not args.python.is_file():
        parser.error('Codex CLI and the evaluation Python executable are required.')
    modules = args.node_modules.resolve(strict=True)
    if not (modules / '@freesewing/core/package.json').is_file():
        parser.error('The dependency directory must include @freesewing/core.')
    workspace = args.workspace.resolve()
    workspace.mkdir(parents=True)
    jobs = []
    for case in CASES:
        for kind, skill in [('with_skill', HERE.parent), ('old_skill', args.baseline.resolve())]:
            folder = workspace / f'eval-{case["id"]}-{case["name"]}' / kind
            prompt = prepare(folder, case, skill, modules)
            jobs.append((folder, prompt))
        metadata = {'eval_id':case['id'], 'eval_name':case['name'], 'prompt':case['prompt'], 'assertions':[]}
        (folder.parent / 'eval_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        results = [pool.submit(run, folder, prompt, args.model, args.python.absolute(), args.timeout)
                   for folder, prompt in jobs]
        return max(future.result() for future in results)


if __name__ == '__main__':
    raise SystemExit(main())
