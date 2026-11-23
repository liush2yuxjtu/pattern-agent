#!/usr/bin/env bash
# Run one batch case in the dedicated CLO Wine worker. The editor is opened once
# during worker setup, then reused for all of that worker's jobs.
set -euo pipefail
export DISPLAY="${DISPLAY:-:0}"
boat_id="$1"
clo_version="$2"
test -s request.json
test -s clo_motion_native.py
test "$(xdotool getwindowfocus getwindowname)" = "CLO Standalone OnlineAuth"
mkdir -p result
test ! -e result/native.done
root="Z:$(pwd -P)"
# All paths here are generated from a case fingerprint.
launcher="import runpy; runpy.run_path('$root/clo_motion_native.py')['main']('$root','$boat_id','$clo_version')"
read -r width height < <(xdotool getdisplaygeometry)
# CLO Wine 2026.1.382 centers the Python editor in the full-screen desktop.
# Use the input/run anchors verified on the worker's standard desktop.
xdotool mousemove "$((width * 450 / 1200))" "$((height * 157 / 675))" click 1
xdotool key --clearmodifiers ctrl+a
# Paste the source as one edit. Simulated typing triggers bracket autoclose.
printf '%s' "$launcher" | xclip -selection clipboard -in -silent >/dev/null 2>&1
xdotool key --clearmodifiers ctrl+v
sleep .2
xdotool mousemove "$((width * 455 / 1200))" "$((height * 136 / 675))" click 1
for ((waited=0; waited<${CLO_CASE_TIMEOUT:-900}; waited++)); do
    if test -e result/native.done; then
        exit 0
    fi
    sleep 1
done
echo "CLO Python Editor did not finish the case" >&2
exit 2
