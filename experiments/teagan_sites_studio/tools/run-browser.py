"""Run unchanged browser assertions with a portable output directory."""
from pathlib import Path
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--app', type=Path, required=True)
parser.add_argument('--suite', choices=['state', 'views'], required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
filename, old = {
    'state': ('verify-studio-state-browser.py', "WORK = Path('/workspace/work/state-machine-audit') / ('live' if LIVE else 'local')"),
    'views': ('verify-four-views-browser.py', "WORK = Path('/workspace/work/fold-color-audit') / ('live' if LIVE else 'local')"),
}[args.suite]
script = args.app.resolve() / 'scripts' / filename
source = script.read_text()
assert source.count(old) == 1, 'Upstream output assignment changed; inspect before adapting.'
source = source.replace(old, 'WORK = Path(' + repr(str(args.out.resolve())) + ')', 1)
exec(compile(source, str(script), 'exec'), {'__name__': '__main__', '__file__': str(script)})
