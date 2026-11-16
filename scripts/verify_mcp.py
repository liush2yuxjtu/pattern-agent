#!/usr/bin/env python3
"""Launch the repository MCP configuration and independently reopen its pattern."""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'.mcp.json').read_text())['mcpServers']['opensloper']
messages=[
    {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'pattern-agent-verify','version':'1'}}},
    {'jsonrpc':'2.0','method':'notifications/initialized'},
    {'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}},
    {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'open','arguments':{'path':str(ROOT/'patterns/straight-skirt-eu40/straight-skirt-eu40.sloper')}}},
    {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'evaluate','arguments':{}}},
]
p=subprocess.run([config['command'],*config['args']],cwd=ROOT,input=''.join(json.dumps(m)+'\n' for m in messages),text=True,capture_output=True,timeout=30,check=True)
answers={r['id']:r for r in [json.loads(line) for line in p.stdout.splitlines()]}
assert all('error' not in r and not r.get('result',{}).get('isError') for r in answers.values()),answers
tools=answers[2]['result']['tools']
expected=json.loads((ROOT/'patterns/straight-skirt-eu40/mcp-tools.json').read_text())['tools']
assert {t['name'] for t in tools}=={t['name'] for t in expected}
assert len(tools)==56
evaluation=json.loads(next(c['text'] for c in answers[4]['result']['content'] if c['type']=='text'))
assert evaluation['problems']==[] and evaluation['blocked']==0,evaluation
print(json.dumps({'verdict':'PASS','server':answers[1]['result']['serverInfo'],'tools':len(tools),'evaluation':evaluation},ensure_ascii=False,indent=2))
