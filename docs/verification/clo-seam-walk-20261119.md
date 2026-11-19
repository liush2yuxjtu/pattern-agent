# CLO batch seam verification

Candidate base `f4357fe9e3ba84745990179693c8987c4a8e5eeb`. Verified
`clo-fit` 0.3.0 plugin tree `3c3900cd0218934f4378c8b3de2df888af1daac9`.
Verdict **PASS** for plugin discovery, batch planning, and the native sewing
group workflow on a test project.

- Registered this checkout with `codex plugin marketplace add <checkout> --json`
  in an isolated profile, ran `codex plugin add clo-fit@pattern-agent --json`,
  and used app-server `skills/list`. All three namespaced skills were enabled.
  The installed seam skill matched the candidate files byte for byte.
- Ran the installed `seam_batch.py` with its bundled plan and catalog. It
  produced two groups to apply and complete coverage. Ran the same CLI with
  Carlton's original side-seam plan and CLO edge lengths. It exited 1 and
  reported **78.262558 mm** of uncovered front hem despite both routes measuring
  820.799988 mm. The revised plan passed coverage with three planned groups.
- Ran the installed script in CLO 2026.1.382 using one `clo_run_python` call.
  Added two groups on a disposable three-piece project, found each new group on
  both pieces, and saved and reopened it with two groups. Replaying the plan
  added zero groups. Restored the saved Carlton checkpoint and read back 28
  patterns and 203 seam groups. Carlton was queried in read-only mode for the
  live preflights. [Raw receipts](clo-seam-walk-20261119.json).
- Ran `python -B -m unittest discover -s .agents/skills/clo-fit-export/scripts
  -p test_fold_preview.py -v`. Both controls passed. The installed
  `compare_poses.py` reproduced 84 records across three saved CLO GLBs.
  The installed `export_fit.py` accepted the saved relaxed-pose CLO GLB,
  project and native stress screenshots through its existing CLI. Its JSON and
  CSV both contained 28 matching pieces, and the heat and fold previews existed.
  The packaged CLI uses its existing argument set.

This check establishes native group creation and persistence. The synthetic
sewing smoke test did not request cloth simulation. Physical fit and the
functional button closure of the line-art version were outside this run.
