#!/usr/bin/env python3
"""Exercise native Codex structured user input using ephemeral app-server sessions."""
import argparse
import asyncio
import json
from pathlib import Path
import re
import sys


EVALS = Path(__file__).resolve().parent
CASES = json.loads((EVALS / 'handoff-cases.json').read_text())['cases']
REFERENCES = ('SKILL.md', 'references/workflows.md', 'references/freesewing.md')
EVENT = 'item/tool/requestUserInput'
DISABLED = ('shell_tool', 'apps', 'plugins', 'skill_search', 'tool_search', 'multi_agent',
            'image_generation', 'view_image', 'sleep_tool')


def contains_all_groups(text, groups):
    return all(any(term.casefold() in text.casefold() for term in group) for group in groups)


class BoatFixture:
    """Model a disposable CLO project without touching Boat or garment files."""

    def __init__(self, data):
        self.data = data
        self.trace = []

    def tools(self):
        operations = [
            ('boat_compare', '在 Boat CLO 3D 用工作副本跑原生单变量对照，自动复用现有人台与面料。',
             {'project': {'enum': [self.data['project']]}, 'pose': {'enum': ['A', 'other']},
              'closure': {'enum': ['open', 'closed', 'not_applicable']},
              'change': {'enum': ['cuff_underarm', 'chest_ease', 'other']}}),
        ]
        if self.data.get('target'):
            operations.append((
                'boat_match_avatar', '在同一 Boat CLO 3D 工作副本按已给品牌人体尺码表核对人台。',
                {'project': {'type': 'string'}, 'size_table_id': {'type': 'string', 'description': '用户提供的尺码表 ID，例如 FitSpec-123。'}}))
        return [{'type': 'function', 'name': name, 'description': description,
                 'inputSchema': {'type': 'object', 'properties': properties,
                                 'required': list(properties), 'additionalProperties': False}}
                for name, description, properties in operations]

    def call(self, tool, args, answered):
        data = self.data
        expected_compare = dict(project=data['project'], pose='A', closure=data['closure'],
                                change=data['change'])
        if tool == 'boat_compare' and args == expected_compare:
            event, output = 'compare', data['compare']
        elif (tool == 'boat_match_avatar' and answered and 'compare' in self.trace
              and args == dict(project=data['project'] + '-comparison', size_table_id=data.get('target'))):
            event = 'match_avatar'
            output = f"已在同一工作副本按 {data['target']} 核对 M 码人台。其余姿势和整衣放行待验。"
        else:
            event, output = 'invalid', '参数、先前步骤或用户资料不符。请核对当前工程与验收范围。'
        self.trace.append(event)
        if event == 'compare':
            output += ' 工作副本 ID 为 ' + data['project'] + '-comparison。原工程没有改写。'
        return {'success': event != 'invalid',
                'contentItems': [{'type': 'inputText', 'text': output}]}


def grade(case, requests, final, final_before_request, completed, unexpected):
    questions = [question for event in requests for question in event['params']['questions']]
    text = '\n'.join(question['question'] + '\n' + '\n'.join(
        option['label'] for option in question.get('options') or []) for question in questions)
    checks = {'actual_request_count': len(requests) == case['expected_requests'],
              'turn_completed': completed and bool(final),
              'no_unrelated_tool_execution': not unexpected,
              'no_final_before_required_question': not final_before_request}
    transports = ['native' if request['method'] == EVENT else 'async' for request in requests]
    if case['expected_requests']:
        checks['requested_on_expected_transport'] = transports == [case['transport']]
        checks['only_current_decision'] = (
            len(questions) == case['question_limit']
            and contains_all_groups(text, case['question_terms'])
            and not any(term in text for term in case.get('question_excludes', ()))
        )
    if case.get('plain_question'):
        checks['asks_directly_when_unavailable'] = bool(re.search(
            r'(?:请[^。\n]{0,55}(?:发|提供|上传|贴|分享)|能否[^。\n]{0,55}|可以(?:发|提供|贴|分享)[^。\n]{0,55}|[？?])', final))
    elif not case['expected_requests']:
        # Verification questions in an explanation are not requests for user input.
        requests_user_input = re.search(
            r'请(?:你|您)?(?:先)?(?:告诉|告知|提供|上传|确认|选择|发给)'
            r'|(?:麻烦|需要)(?:你|您)(?:先)?(?:告诉|提供|上传|确认|选择|发)'
            r'|(?:你|您)(?:想|希望|打算|能否|可否)[^。！？?\n]*[？?]'
            r'|(?:你|您)?(?:要用|要选|先做|先用)(?:哪[一件个款份种]|什么)[^。！？?\n]*[？?]',
            final,
        )
        checks['no_question_instead_of_work'] = not requests_user_input
    checks['continues_with_required_scope_or_supplied_answer'] = contains_all_groups(
        final, case['resume_terms'])
    return {'passed': all(checks.values()), 'checks': checks, 'question': text,
            'final': final, 'requests': len(requests), 'observed_transports': transports}


async def execute(case, skill, model, dest):
    dest.mkdir(parents=True, exist_ok=False)
    cwd = dest / 'empty'
    cwd.mkdir()
    transport = case['transport']
    native_flag = '--enable' if transport == 'native' else '--disable'
    async_flag = '--enable' if transport == 'async' else '--disable'
    cmd = ['codex', 'app-server', native_flag, 'default_mode_request_user_input',
           async_flag, 'send_message_to_user_async', '--enable', 'skip_host_skill_discovery',
           '-c', 'mcp_servers={}',
           '-c', 'web_search="disabled"', '-c', 'suppress_unstable_features_warning=true']
    for item in DISABLED:
        cmd.extend(('--disable', item))
    fixture = BoatFixture(case['cad']) if case.get('cad') else None
    instructions = ('用中文完成给出的服装任务。环境中没有服装、文件或 shell 工具，'
                    '只根据已给资料和当前可用的对话能力推进。\n\n')
    if fixture:
        instructions = ('用中文完成范围内的服装任务。客户端提供隔离的 Boat CLO 3D 操作工具，'
                        '以工具返回为本轮观察。除这些工具和客户端提问接口外无其他可用工具。遇到真正依赖用户的决定时使用客户端提问。\n\n')
    if not case['tool_available']:
        instructions += ('本客户端只交付纯文字答复，无法显示或接收结构化提问。'
                         '这条用例中请停止尝试任何工具调用，并直接在答复中与用户交互。\n\n')
    elif transport == 'native':
        instructions += ('本客户端通过原生 request_user_input 接收结构化提问。'
                         '当前决策确实需要提问时，调用该原生接口等待答复。\n\n')
    elif transport == 'async':
        instructions += ('本客户端通过 request_user_input_async 接收结构化提问。'
                         '当前决策确实需要提问时，调用该异步接口。\n\n')
    instructions += '\n\n'.join((skill / ref).read_text() for ref in REFERENCES)
    with (dest/'transport.stderr').open('wb') as errors:
        proc = await asyncio.create_subprocess_exec(*cmd, stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE, stderr=errors)

        async def write(message):
            proc.stdin.write((json.dumps({"jsonrpc": "2.0", **message},
                                          ensure_ascii=False) + '\n').encode())
            await proc.stdin.drain()

        async def request(num, method, params):
            await write({'id': num, 'method': method, 'params': params})

        events = []
        questions = []
        final = ''
        final_before_request = False
        completed = False
        pending_async = None
        answered_async = False
        answered = False
        unexpected = []
        try:
            await request(1, 'initialize', {
                'clientInfo': {'name': 'design-cloth-handoff-evals', 'version': '1.0.0'},
                'capabilities': {'experimentalApi': True}})
            deadline = asyncio.get_running_loop().time() + 100
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                line = await asyncio.wait_for(proc.stdout.readline(), remaining)
                if not line:
                    raise RuntimeError('app-server closed before turn completed')
                message = json.loads(line)
                mid, method = message.get('id'), message.get('method')
                params = message.get('params', {})
                if method in (EVENT, 'serverRequest/resolved', 'item/completed', 'turn/completed', 'item/tool/call'):
                    events.append(message)
                if method is None and mid in (1, 2, 3, 4, 5) and 'error' in message:
                    raise RuntimeError(message['error'])
                if method is None and mid == 1 and 'result' in message:
                    await write({'method': 'initialized', 'params': {}})
                    await request(5, 'config/read', {'cwd': str(cwd.resolve()), 'includeLayers': False})
                elif method is None and mid == 5 and 'result' in message:
                    servers = message['result']['config'].get('mcp_servers') or {}
                    # An empty table merges with user config. Disable each configured server.
                    disabled_mcp = {f'mcp_servers.{name}.enabled': False for name in servers}
                    await request(2, 'thread/start', {'cwd': str(cwd.resolve()),
                        'ephemeral': True, 'model': model, 'approvalPolicy': 'never',
                        'sandbox': 'read-only', 'environments': [], 'config': disabled_mcp,
                        'developerInstructions': instructions,
                        **({'dynamicTools': fixture.tools()} if fixture else {})})
                elif method is None and mid == 2 and 'result' in message:
                    thread = message['result']['thread']['id']
                    await request(3, 'turn/start', {'threadId': thread, 'effort': 'low',
                        'input': [{'type': 'text', 'text': case['prompt'], 'text_elements': []}]})
                elif method == 'item/tool/call' and fixture:
                    result = fixture.call(params['tool'], params['arguments'], answered)
                    events.append({'method': 'fixture/boatResult', 'result': result})
                    await write({'id': mid, 'result': result})
                elif method == EVENT:
                    if fixture:
                        fixture.trace.append('question')
                    questions.append(message)
                    answers = {q['id']: {'answers': [case.get('answer', '无额外资料')]}
                               for q in params['questions']}
                    response = {'id': mid, 'result': {'answers': answers}}
                    events.append({'sent': response, 'method': 'fixture/answered'})
                    await write(response)
                    answered = True
                elif method and mid is not None:
                    unexpected.append(method)
                    await write({'id': mid, 'error': {'code': -32601, 'message': 'Unavailable in eval'}})
                elif method == 'item/completed':
                    item = params['item']
                    if item['type'] == 'agentMessage' and item.get('delivery') == 'async' and item.get('questions'):
                        if fixture:
                            fixture.trace.append('question')
                        items = item['questions']
                        normalized = [{'question': q['title'], 'options': [
                            {'label': label} for label in q.get('options') or []]} for q in items]
                        questions.append({'method': 'codex/asyncQuestion',
                                          'params': {'questions': normalized}})
                        if not answered_async and case.get('answer'):
                            pending_async = [{
                                'questionItemId': json.dumps(
                                    ['request_user_input_async', item['id'], i], separators=(',', ':')),
                                'question': q['title'], 'answer': case['answer']}
                                for i,q in enumerate(items)]
                    elif item['type'] == 'agentMessage' and item.get('phase') == 'final_answer':
                        if case['expected_requests'] and not questions:
                            final_before_request = True
                        final = item['text']
                    elif fixture and item['type'] == 'dynamicToolCall':
                        pass
                    elif item['type'] not in ('userMessage', 'agentMessage', 'reasoning', 'plan'):
                        unexpected.append(item['type'])
                elif method == 'turn/completed':
                    completed = params['turn']['status'] == 'completed'
                    if completed and pending_async is not None:
                        text = ('<send_user_message_question_reply>\n'
                                + json.dumps(pending_async, ensure_ascii=False)
                                + '\n</send_user_message_question_reply>')
                        events.append({'method': 'fixture/asyncAnswered', 'answers': pending_async})
                        pending_async = None
                        answered_async = True
                        answered = True
                        final = ''
                        await request(4, 'turn/start', {'threadId': thread, 'effort': 'low',
                            'input': [{'type': 'text', 'text': text, 'text_elements': []}]})
                    else:
                        break
        finally:
            (dest/'events.jsonl').write_text(''.join(
                json.dumps(e, ensure_ascii=False) + '\n' for e in events))
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), 8)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
    result = dict(id=case['id'], name=case['name'], **grade(
        case, questions, final, final_before_request, completed, unexpected))
    if fixture:
        expected = ['compare', 'question', 'match_avatar'] if fixture.data.get('target') else ['compare']
        result['boat_trace'] = fixture.trace
        result['checks']['boat_actions_in_scope_and_in_order'] = fixture.trace == expected
        result['passed'] = all(result['checks'].values())
    (dest/'grading.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(case['id'], dest.name, 'PASS' if result['passed'] else 'FAIL',
          ', '.join(k for k,v in result['checks'].items() if not v), flush=True)
    return result


async def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    cases = [c for c in CASES if not args.ids or c['id'] in args.ids]
    if not cases:
        raise ValueError('No cases selected')
    arms = {'current': EVALS.parent}
    if args.baseline:
        arms['baseline'] = args.baseline.resolve()
    limit = asyncio.Semaphore(5)
    async def limited(case, arm, skill):
        async with limit:
            try:
                return await execute(case, skill, args.model, args.output/f"eval-{case['id']}"/arm)
            except (TimeoutError, RuntimeError, OSError) as exc:
                print(case['id'], arm, type(exc).__name__, str(exc), flush=True)
                return {'id': case['id'], 'passed': False, 'infra_error': str(exc)}
    keys = [(c, arm, s) for c in cases for arm,s in arms.items()]
    values = await asyncio.gather(*(limited(*key) for key in keys))
    report = {arm: [v for (_,name,_),v in zip(keys,values) if name == arm] for arm in arms}
    (args.output/'benchmark.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    return all(r['passed'] for r in report['current'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--model', default='gpt-6.2-sol')
    parser.add_argument('--ids', nargs='+', type=int)
    args = parser.parse_args()
    return 0 if asyncio.run(run(args)) else 1


if __name__ == '__main__':
    sys.exit(main())
