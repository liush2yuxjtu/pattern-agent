# Full-arm synthetic T-shirt experiment

Run commands from this directory. The pipeline performs actual Blender physics,
independent mesh checks and negative controls, then creates and reloads a portable
measured replay. Video renders the actual exported geometry.

```sh
python3 run_pipeline.py --out runs/full-arm --frames 241 --render-video
```

Exit 0 means the defined synthetic geometry gate passes; exit 2 means quality
FAIL; exit 3 means execution or coverage error. Physical fit stays NOT_RUN.
The default builder is the frozen failing baseline; full_arm_scene_v2.py is an
unsuccessful later quad experiment.

```sh
python3 -m unittest discover -s verification -p test_pipeline_gate.py -v
blender -b -t 1 --python-exit-code 2 --python verification/test_geometry.py
```

For a short caller smoke, --frames 3 covers only the initial A-pose prefix. It
does not replace the 241-frame motion acceptance run. Arm routing follows marked
loops and skeletal paths; sizing, actual donning and physical fit are separate.
