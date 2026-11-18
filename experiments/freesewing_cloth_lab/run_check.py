"""Run an unchanged verifier within the CPU quota actually allocated to it.

Some managed hosts expose many CPUs while the container has a four-core quota.
Software rendering can otherwise oversubscribe that quota. Affinity applies
only to this process and its children; it grants no additional resources.
"""
import json
import math
import os
from pathlib import Path
import sys

checks = {'browser': 'verify_browser.py', 'dynamics': 'verify_dynamics.py',
          'independent': 'independent.py', 'gpu': 'verify_heatmap_gpu.py',
          'support':'verify_free_waist.py', 'variant': 'verify_variants.py', 'ab': 'verify_allocation_ab.py'}
if len(sys.argv) < 2 or sys.argv[1] not in checks:
    raise SystemExit('Usage: run_check.py ' + '|'.join(checks) + ' [original verifier arguments]')

metadata = {'reason': 'Match software-rendering concurrency to the actual container CPU allocation'}
if hasattr(os, 'sched_getaffinity'):
    allowed = sorted(os.sched_getaffinity(0))
    count = len(allowed)
    quota_file = Path('/sys/fs/cgroup/cpu.max')
    if quota_file.exists():
        quota, period = quota_file.read_text().split()
        metadata['cpuMax'] = [quota, period]
        if quota != 'max':
            count = max(1, min(count, math.floor(int(quota) / int(period))))
    selected = allowed[:count]
    os.sched_setaffinity(0, selected)
    metadata.update(visibleCpuCount=os.cpu_count(), availableAffinityCount=len(allowed), selectedCpuCount=count, selectedCpuIds=selected)
print(json.dumps({'verificationEnvironment': metadata}), flush=True)
script = Path(__file__).with_name(checks[sys.argv[1]])
os.execv(sys.executable, [sys.executable, str(script), *sys.argv[2:]])
