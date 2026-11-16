# Recovered motion surface

Working directory: `experiments/oneshot_motion`. Follow its README for launch
commands and prerequisites. Use a fresh output directory; retain evidence and
remove only disposable test state after closing Blender.

For `experiments/oneshot_motion`, follow its README. Execute both recovered source
generators unchanged, legacy geometry CLI, `verify_motion.py --workers 4`,
`inspect_caps.py`, and `adjudicate.py` on all121 saved meshes. Run the3 containment
pruning tests before publication. Geometry FAIL exits2 are expected diagnostic
outcomes. A cap-sensitive frame must remain UNKNOWN rather than being upgraded.
Generate portable replay with `../full_arm/simulation/replay_and_render.py`, then
use `../full_arm/verification/verify_replay.py` on the independently reopened file.
Require121/121 full-array matches and inspect actual stills. Record candidate,
source hashes, commands, exit status, findings and cleanup before direct main push.
