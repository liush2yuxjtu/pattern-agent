"""Strict native Claude trigger observations; adapted from the pinned Apache-2.0 runner.

The upstream scripts remain unmodified. This adapter saves actual routing events
and treats runtime failures as BLOCKED, never as successful non-trigger trials.
"""
import json
import os
import select
import subprocess
import time
import uuid
from pathlib import Path


class NativeTrialError(RuntimeError):
    pass


def decision(event, alias):
    """Inspect complete native assistant/result events. Text claims do not count."""
    if event.get('type') == 'result':
        if event.get('is_error') or event.get('subtype') not in (None, 'success'):
            raise NativeTrialError('Claude returned an error result')
        return False
    if event.get('type') != 'assistant':
        return None
    for item in event.get('message', {}).get('content', []):
        if item.get('type') != 'tool_use':
            continue
        args = item.get('input', {})
        if item.get('name') == 'Skill':
            return alias in str(args.get('skill', ''))
        if item.get('name') == 'Read':
            return alias in str(args.get('file_path', ''))
        return False
    return None


def guarded_query(query, skill_name, skill_description, timeout, project_root, model=None):
    root = Path(project_root)
    trial_id = uuid.uuid4().hex
    alias = f'{skill_name}-skill-{trial_id[:8]}'
    commands = root/'.claude'/'commands'
    commands.mkdir(parents=True, exist_ok=True)
    command_file = commands/f'{alias}.md'
    command_file.write_text('---\ndescription: |\n  '+skill_description.replace('\n','\n  ')+'\n---\n\n# '+skill_name+'\n\nThis skill handles: '+skill_description+'\n')
    records = Path(os.environ['PATTERN_SKILL_TRIAL_DIR'])
    records.mkdir(parents=True, exist_ok=True)
    record = {'trial_id':trial_id, 'query':query, 'model':model, 'alias':alias,
              'status':'error', 'triggered':None, 'event_types':[], 'routing_tools':[],
              'scope':'native metadata-routing probe; not full skill execution'}
    process = None
    started = time.perf_counter()
    try:
        cmd = ['claude','-p',query,'--output-format','stream-json','--verbose','--include-partial-messages']
        if model:
            cmd += ['--model', model]
        env = {k:v for k,v in os.environ.items() if k != 'CLAUDECODE'}
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=root, env=env)
        buffer = ''
        pending = None
        partial = ''
        while time.perf_counter()-started < timeout:
            ready,_,_ = select.select([process.stdout],[],[],.2)
            if ready:
                chunk = os.read(process.stdout.fileno(),65536)
                buffer += chunk.decode('utf-8',errors='replace')
            if process.poll() is not None:
                rest = process.stdout.read()
                if rest:
                    buffer += rest.decode('utf-8',errors='replace')
                if process.returncode != 0:
                    raise NativeTrialError(f'Claude process exit code {process.returncode}')
                if buffer and not buffer.endswith('\n'):
                    buffer += '\n'
            while '\n' in buffer:
                line,buffer = buffer.split('\n',1)
                try:
                    event = json.loads(line)
                except (ValueError,TypeError):
                    continue
                record['event_types'].append(event.get('type'))
                if event.get('type')=='system' and event.get('model'):
                    record['runtime_model']=event['model']
                answer = decision(event,alias)
                if answer is not None:
                    record.update(status='ok',triggered=answer)
                    return answer
                # Early native routing observation, matching the official protocol.
                if event.get('type') == 'stream_event':
                    stream=event.get('event',{});kind=stream.get('type')
                    if kind=='content_block_start':
                        block=stream.get('content_block',{})
                        if block.get('type')=='tool_use':
                            pending=block.get('name');partial='';record['routing_tools'].append(pending)
                            if pending not in ['Skill','Read']:
                                record.update(status='ok',triggered=False)
                                return False
                    elif kind=='content_block_delta' and pending:
                        delta=stream.get('delta',{})
                        if delta.get('type')=='input_json_delta':
                            partial+=delta.get('partial_json','')
                            if alias in partial:
                                record.update(status='ok',triggered=True)
                                return True
                    elif kind=='content_block_stop' and pending:
                        record.update(status='ok',triggered=alias in partial)
                        return record['triggered']
            if process.poll() is not None:
                raise NativeTrialError('Process ended without a native routing/final result event')
        raise NativeTrialError('Native routing probe timed out')
    except Exception as exc:
        record['error_type']=type(exc).__name__
        record['error']=str(exc)[:200]
        raise
    finally:
        if process is not None and process.poll() is None:
            process.kill();process.wait()
        if process is not None:
            process.stdout.close();process.stderr.close()
        command_file.unlink(missing_ok=True)
        record['duration_seconds']=round(time.perf_counter()-started,4)
        (records/f'{trial_id}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))


def install():
    from scripts import run_eval,run_loop
    original=run_eval.run_eval
    def strict_eval(*args,**kwargs):
        result=original(*args,**kwargs)
        bad=[]
        for path in Path(os.environ['PATTERN_SKILL_TRIAL_DIR']).glob('*.json'):
            value=json.loads(path.read_text())
            if value.get('status')!='ok':bad.append(path.name)
        if bad:
            raise NativeTrialError(f'{len(bad)} failed trials: no valid aggregate trigger score')
        return result
    run_eval.run_single_query=guarded_query
    run_loop.run_eval=strict_eval
