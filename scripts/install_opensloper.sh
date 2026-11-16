#!/usr/bin/env bash
# Install the official release inside the ignored project work directory.
set -euo pipefail
pattern_repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
pattern_tools="$pattern_repo/work/tools"
pattern_release="$pattern_tools/opensloper-0.2.0-linux-x86_64"
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo 'This helper supports Linux x86_64 only.' >&2; exit 1; }
mkdir -p "$pattern_tools"
if [[ ! -x "$pattern_release/opensloper-cli" ]]; then
  pattern_archive="$pattern_tools/opensloper-0.2.0-linux-x86_64.tar.gz"
  curl -fLsS --retry 2 https://github.com/opensloper/opensloper/releases/download/v0.2.0/opensloper-0.2.0-linux-x86_64.tar.gz -o "$pattern_archive"
  (cd "$pattern_tools" && sha256sum -c "$pattern_repo/scripts/opensloper-release.sha256")
  tar -xzf "$pattern_archive" -C "$pattern_tools"
fi
"$pattern_release/opensloper-cli" --version
printf 'Set OPENSLOPER_CLI=%q\n' "$pattern_release/opensloper-cli"
