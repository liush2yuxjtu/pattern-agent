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
input_x=$((width * 450 / 1200))
input_y=$((height * 157 / 675))
run_x=$((width * 455 / 1200))
run_y=$((height * 136 / 675))
if command -v wmctrl >/dev/null; then
    # Wine exposes the 630px-wide Python editor as a separate top-level window.
    editor=$(wmctrl -lG | awk '$5>=570 && $5<=730 && $6>=480 && $6<=800 && /CLO Standalone OnlineAuth/ {print $1,$3,$4; exit}')
    if test -n "$editor"; then
        read -r window left top <<<"$editor"
        wmctrl -i -a "$window"
        input_x=$((left+110))
        input_y=$((top+117))
        run_x=$((left+89))
        run_y=$((top+47))
    fi
fi
xdotool mousemove "$input_x" "$input_y" click 1
xdotool key --clearmodifiers ctrl+a
# Paste the source as one edit. Simulated typing triggers bracket autoclose.
printf '%s' "$launcher" | xclip -selection clipboard -in -silent >/dev/null 2>&1
xdotool key --clearmodifiers ctrl+v
sleep .4
xdotool mousemove "$run_x" "$run_y" click 1
for ((waited=0; waited<${CLO_CASE_TIMEOUT:-900}; waited++)); do
    if test -e result/native.done; then
        exit 0
    fi
    sleep 1
done
echo "CLO Python Editor did not finish the case" >&2
exit 2
