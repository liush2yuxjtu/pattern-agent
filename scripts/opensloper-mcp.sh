#!/usr/bin/env bash
set -euo pipefail
pattern_repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
pattern_cli=${OPENSLOPER_CLI:-"$pattern_repo/work/tools/opensloper-0.2.0-linux-x86_64/opensloper-cli"}
[[ -x "$pattern_cli" ]] || { echo 'Run bash scripts/install_opensloper.sh first, or set OPENSLOPER_CLI.' >&2; exit 1; }
exec "$pattern_cli" serve "$@"
