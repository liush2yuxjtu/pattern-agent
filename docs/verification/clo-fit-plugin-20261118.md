# CLO Fit Review plugin verification

Candidate base `75340d7efd908ce8b33fa45cd49d534fdf9429b3`. Plugin tree `9cbc7505a2fb9a8d5798e8bc73dcbdead60e051b`. Local verdict **PASS** for the packaged workflows and reference material.

- Registered the checkout with `codex plugin marketplace add <checkout>` in a fresh profile. Ran `codex plugin add clo-fit@pattern-agent --json` and inspected the installed 0.1.0 cache. Both skill entrypoints and the example were present.
- Ran `python -B -m unittest discover -s .agents/skills/clo-fit-export/scripts -p test_fold_preview.py -v`. Both geometry controls passed. The bundled exporter and fold implementation matched the repository versions byte for byte.
- Ran the installed `export_fit.py` on the relaxed-pose garment GLB with its ZPRJ and two stress screenshots. Six output records matched the earlier DXF run; independently checked CSV area shares against JSON, confirmed numeric stress unavailable, and inspected all three plots. A one-label/six-primitive input was rejected before output creation.
- Ran the installed `compare_poses.py` on four saved garment meshes. The 24-row CSV matched the source comparison byte for byte.
- Read the native ChatGPT Page and checked the independent Markdown copy's five sections and all eleven local image files. Installed input DXF SHA-256 `1f82b2c4ca094983657ce49fc73cf06aec24d3329a53dcc3472dd5ca2cee87f4` matched the original bytes.

A second live CLO simulation was outside this packaging check. Physical fit: NOT_RUN.
