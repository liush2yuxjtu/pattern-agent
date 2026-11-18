# CLO fit export verification · 2026-11-18

**PASS** for the offline exporter. Native CLO UI execution and physical fit were outside this check.

Candidate parent: `8f8c061afee6e7f19611bc02a4d196b8548818e4`.
Verified source SHA-256:

| File | SHA-256 |
| --- | --- |
| `export_fit.py` | `75b7f7421f697d079ecde86b11efde7dc70b31f8e66f70f0b679ba2603833cdb` |
| `fold_preview.py` | `bb307f7fd7e0bdd6be85eadf856ba779da12e248702eefc1f5124de2f1f94929` |
| `test_fold_preview.py` | `0c034f4ac37ec934e7679e162f0e211832c0ad9e278c65d3a317bf6d77400582` |

- `python -B -m unittest discover -s .agents/skills/clo-fit-export/scripts -p test_fold_preview.py -v` passed both analytic tests, covering known hinge angles, winding, vertex splits and UV seams. Skill frontmatter validation passed.
- Ran `python -B .agents/skills/clo-fit-export/scripts/export_fit.py` against the saved six-piece CLO garment and matching native stress screenshots, as described in the [recipe](../../../.agents/skills/verify/references/clo-fit-export.md). Reopened JSON and CSV, checked the input hash, confirmed identical prior strain fields, and found 126,167 measurable interior edges with 4,333 edges at or above 15°. Unsupplied point stress remained missing.
- Reopened all three PNGs and byte-compared them with the visually inspected outputs from the same candidate. The CLI rejected a wrong piece-ID count and produced no output directory for that invocation.
- Verification used a local scratch directory. The garment and its render outputs are not included in the commit.
