# Style3D motion fit evidence

This template records or samples a native Style3D fitting and saves images and statistics for agent review. It takes the selected project, avatar, and main cloth pieces from the current desktop session. It has no account, garment, file path, size, pose names, or animation range tied to the original test.

## Set up on another machine

Keep both Python scripts together. Use Python 3.9 or later, a licensed Style3D desktop installation, and an enabled local Style3D Streamable HTTP MCP endpoint with the native solver, mesh, fitting map, and snapshot APIs used below. No Python packages are required. Run the script on the same machine as Style3D for shared project and image paths. Supply a different loopback address with `--endpoint` if configured. The default is `http://127.0.0.1:57281/mcp`. Live validation used Style3D Studio 10.1.258 on macOS. Native capabilities and snapshot export must be available on the target build.

Open the correct project with simulation and recording stopped. Use a working copy whenever changing the timeline or recording. For motion, dress the model in a valid starting pose first and check garment coverage from at least two views.

    python style3d-motion-verify.py inspect-output --inspect
    python style3d-motion-verify.py fit-evidence --config style3d-motion.example.json

Use `python3` or the platform's Python launcher as appropriate. Both commands require fresh output directories. Read `inspect-output/summary.json` for the project name, native pose names, and available avatar and cloth selectors. Use exact names or IDs when narrowing the review. IDs are specific to the open project session. Select an avatar explicitly when several are present. All main cloth pieces are used by default. Secondary piece IDs are listed so they can be reviewed separately if required.

## Configure a capture

- Use `"mode": "current"` for the currently stopped fit. Use `"mode": "timeline"` for a saved, simulated animation. Timeline sampling restores the initial frame before exit. Open the intended animation take and use `"expectedProject"` to bind the capture to its project name.
- Omit `frames` to sample the first and last available frame plus even intervals. `samples` defaults to 5. Use `"frames": [0, 24, 48]` to select exact native frame indices, or `"frames": "all"` to use the entire reported timeline range. Use a saved recorded clip or explicitly bound frames because some Style3D builds report a default track length for empty projects.
- Optional fields include `case`, `avatar`, `pieces`, `views`, `width`, `height`, `maxCrossings`, `maps`, and `saveRaw`. `views` supports Front, Back, Left, Right, Upward and Downward. An empty list requests statistics only. Native snapshots include all available colorways. `maps` supports strain, stress, cloth-pressure and avatar-pressure. The default is strain. `saveRaw` retains compressed geometry, face pairs, and native map results, including invalid reads.

To record instead of sampling an existing clip, replace the example config with the following and substitute the actual project and pose names listed by inspect. Provide a working project without pose or animation entries on the selected avatar. The first pose must match the dressed starting state. The script adds a native pose sequence, waits for a committed recording, samples it, and can save the resulting project in the output folder. Recording edits the open working copy and leaves it on the last sampled frame. The original file is opened or restored separately through the normal Style3D workflow.

```json
{
  "mode": "record",
  "expectedProject": "Working copy name",
  "case": "Arm movement",
  "pieces": ["Exact cloth-piece name"],
  "samples": 5,
  "saveProject": "recorded-fit.sproj",
  "record": {
    "timeoutSeconds": 300,
    "poses": [
      {"name": "Exact native starting pose", "holdSeconds": 0.3},
      {"name": "Exact native target pose", "transitionSeconds": 2.2, "holdSeconds": 0.6}
    ]
  }
}
```

## Read the outputs

- `summary.json` has revision and case identifiers, software, selected pieces, frame range, issues, output image names, and per-piece native statistics. Open each reported image under its frame directory. `statistics.csv` is one row per sampled frame and piece, with crossing count, truncation, strain and stress P95, units, and relative image paths. Optional pressure statistics are in JSON.
- `captured` is a collection result. `needs_review` and exit code 2 flag missing, invalid, truncated, or otherwise incomplete evidence. Inspect positive crossing counts even on a successful capture. The script records visibly unverified coverage as pending. Missing counts are null. A count capped by `maxCrossings` is a lower bound.
- The crossing metric counts noncoplanar cloth/body triangle pairs. It varies with mesh density, excludes coplanar contact and full containment, and is neither a pressure value nor a coverage measurement. Zero intersections can occur when a limb has left the garment. Use the automatically captured views to confirm limb coverage throughout the sampled action, especially at cuffs and openings. Use the project-specific fit criteria from the design-cloth finish verification for a garment verdict.
- Native fitting readouts are accepted only when units, value counts, and matching mesh data check out. A body pressure sample set of all zeros is held for review.
