#!/usr/bin/env python3
"""Build the pinned Anthropic review viewer with explicit static-host adaptations.

The upstream files remain byte-preserved. This adapter calls their discovery,
previous-iteration loader and generate_html functions, then changes only the
generated standalone document: safe embedding, comparison order, honest unknown
token reporting, and browser-local feedback plus a real feedback.json download.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
UPSTREAM_VIEWER = HERE / 'upstream/eval-viewer/generate_review.py'


def load_upstream():
    spec = importlib.util.spec_from_file_location('pinned_anthropic_eval_viewer', UPSTREAM_VIEWER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def config_order(value):
    match = re.search(r'(with_skill|new_skill|without_skill|old_skill)', str(value))
    return 0 if match and match.group(1) in {'with_skill', 'new_skill'} else 1 if match else 2


def eval_order(value):
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, str(value))


def positive_number(value):
    return type(value) in {int, float} and math.isfinite(value) and value > 0


def normalize_benchmark(source):
    """Do not turn absent or zero-placeholder model tokens into a measurement."""
    result = copy.deepcopy(source)
    runs = result.get('runs', [])
    counts = {}
    token_known = {}
    for run in runs:
        config = run.get('configuration', 'unknown')
        key = (str(run.get('eval_id')), config)
        counts[key] = counts.get(key, 0) + 1
        metrics = run.setdefault('result', {})
        known = positive_number(metrics.get('tokens'))
        token_known.setdefault(config, []).append(known)
        if not known:
            metrics['tokens'] = None
    summary = result.get('run_summary', {})
    for config, values in list(summary.items()):
        if config == 'delta':
            continue
        if not token_known.get(config) or not all(token_known[config]):
            values.pop('tokens', None)
    if not token_known or not all(all(values) for values in token_known.values()):
        summary.get('delta', {}).pop('tokens', None)
    result['run_summary'] = dict(sorted(summary.items(), key=lambda item: (item[0] == 'delta', config_order(item[0]))))
    runs.sort(key=lambda run: (eval_order(run.get('eval_id')), config_order(run.get('configuration')), run.get('run_number', 0)))
    if counts:
        repetitions = sorted(set(counts.values()))
        result.setdefault('metadata', {})['runs_per_configuration'] = repetitions[0] if len(repetitions) == 1 else f'{repetitions[0]}–{repetitions[-1]} per eval'
    return result


STATIC_FEEDBACK = r'''    // Static-only adaptation: no server endpoint or credential-bearing request.
    function persistStaticFeedback() {
      try {
        localStorage.setItem(STATIC_REVIEW_KEY, JSON.stringify(feedbackMap));
        document.getElementById("feedback-status").textContent = "Saved in this browser; submit to download";
      } catch {
        document.getElementById("feedback-status").textContent = "Browser storage unavailable; submit to download";
      }
    }

    function saveCurrentFeedback() {
      const run = EMBEDDED_DATA.runs[currentIndex];
      const text = document.getElementById("feedback").value;
      if (text.trim() === "") delete feedbackMap[run.id];
      else feedbackMap[run.id] = text;
      persistStaticFeedback();
    }

    function showDoneDialog() {
      saveCurrentFeedback();
      const timestamp = new Date().toISOString();
      const reviews = EMBEDDED_DATA.runs.map(run => ({run_id: run.id, feedback: feedbackMap[run.id] || "", timestamp}));
      const payload = JSON.stringify({reviews, status: "complete"}, null, 2);
      const url = URL.createObjectURL(new Blob([payload], {type: "application/json"}));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "feedback.json";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      document.getElementById("done-overlay").classList.add("visible");
    }

'''


def build(workspace, benchmark_path=None, previous_workspace=None):
    upstream = load_upstream()
    runs = upstream.find_runs(workspace.resolve())
    if not runs:
        raise ValueError('No outputs/ run directories found')
    runs.sort(key=lambda run: (eval_order(run.get('eval_id')), config_order(run['id']), run['id']))
    benchmark = normalize_benchmark(json.loads(benchmark_path.read_text())) if benchmark_path else None
    previous = upstream.load_previous_iteration(previous_workspace.resolve()) if previous_workspace else {}
    name = (benchmark or {}).get('metadata', {}).get('skill_name') or workspace.parent.name.replace('-workspace', '')
    document = upstream.generate_html(runs, name, previous, benchmark)
    if benchmark and benchmark.get('metadata', {}).get('protocol'):
        # A scope label is visible before the user reaches the quantitative tab.
        document = document.replace('<h1>Eval Review: <span id="skill-name"></span></h1>',
                                    '<h1>Eval Review: <span id="skill-name"></span></h1>'
                                    '<p id="functional-scope" style="font-size:0.8rem;max-width:40rem;margin-top:0.5rem">'
                                    'Executed synthetic controls. Not native Claude triggering, real anatomical validation, '
                                    'or full six-image generation quality.</p>', 1)
    # JSON is on one generated line. Escaping '<' also protects literal </script>
    # inside HTML deliverables without changing the displayed or downloaded text.
    marker = re.search(r'const EMBEDDED_DATA = (.+);', document)
    if marker is None:
        raise ValueError('Pinned viewer embedded-data marker not found')
    payload = marker.group(1)
    json.loads(payload)
    safe_payload = payload.replace('<', r'\u003c')
    document = document[:marker.start(1)] + safe_payload + document[marker.end(1):]
    key = 'pattern-agent:eval-review:' + hashlib.sha256(payload.encode()).hexdigest()[:24]
    document = document.replace('let feedbackMap = {};', 'const STATIC_REVIEW_KEY = ' + json.dumps(key) + ';\n    let feedbackMap = {};', 1)
    start = document.index('      // Load saved feedback from server')
    end = document.index('      document.getElementById("skill-name")', start)
    loading = '''      // Restore this exact review build only; prior iterations have separate keys.
      try {
        const stored = JSON.parse(localStorage.getItem(STATIC_REVIEW_KEY) || "{}");
        const ids = new Set(EMBEDDED_DATA.runs.map(run => run.id));
        for (const [id, value] of Object.entries(stored)) {
          if (ids.has(id) && typeof value === "string") feedbackMap[id] = value;
        }
      } catch { /* browser storage may be disabled */ }

'''
    document = document[:start] + loading + document[end:]
    start = document.index('    function saveCurrentFeedback()')
    end = document.index('    function closeDoneDialog()', start)
    document = document[:start] + STATIC_FEEDBACK + document[end:]
    document = document.replace('Your feedback has been saved. Go back to your Claude Code session and tell Claude you\'re done reviewing.', 'Your feedback was downloaded as feedback.json. Keep the file and share it with your agent to continue the review.')
    document = document.replace('When done, copy feedback and paste into Claude Code.', 'Submit All Reviews downloads feedback.json for your next review round.')
    # Font fallbacks make the scientific controls review usable offline. SheetJS
    # is needed only for actual XLSX outputs; retain that optional dependency then.
    document = re.sub(r'^  <link[^\n]+(?:fonts\.googleapis\.com|fonts\.gstatic\.com)[^\n]*\n', '', document, flags=re.M)
    if not any(item.get('type') == 'xlsx' for run in runs for item in run.get('outputs', [])):
        document = re.sub(r'^  <script src="https://cdn\.sheetjs\.com/[^\n]+\n', '', document, flags=re.M)
    runtime_document = document.replace('const EMBEDDED_DATA = ' + safe_payload + ';', '')
    if '/api/feedback' in runtime_document:
        raise ValueError('Static adaptation left a feedback API reference')
    return document, dict(runs=len(runs), storage_key=key, benchmark_tokens='unknown values omitted/null; no zero placeholders', upstream='Anthropic pinned generate_review.py and viewer.html; generated document adapted only')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--benchmark', type=Path)
    parser.add_argument('--previous-workspace', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    document, summary = build(args.workspace, args.benchmark, args.previous_workspace)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(document)
    print(json.dumps(dict(output=str(args.out), **summary), ensure_ascii=False))


if __name__ == '__main__':
    main()
