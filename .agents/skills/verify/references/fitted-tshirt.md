# Fitted T-shirt visual reconstruction and publication

Working directory: repository root. Source: `experiments/fitted_tshirt/`;
public surface: `web/fitted-tshirt/`. This verifies source preservation, a
parameterized visual reconstruction and its website, never physical fit,
calibrated fabric mechanics, seam tolerance or strict intersection release.

## Working local gate

Prerequisites: Python with NumPy, SciPy, Matplotlib, Pillow, Playwright and the
system `/usr/bin/chromium`. Blender 4.3.2 is needed to regenerate the scene and
renders, not to open the shipped browser surface. The Cloud browser used here
has no ego-browser executable; use the verified local Playwright route.

```sh
cd experiments/fitted_tshirt
python scripts/extract_patterns.py
MPLCONFIGDIR=../../work/mpl python scripts/prepare_mesh.py --output ../../work/rebuilt-tshirt-mesh.json
cd ../..
python scripts/build_fitted_tshirt_bundle.py
python scripts/build_pages.py
python scripts/verify_fitted_tshirt.py --output work/verify-fitted-tshirt
python -m unittest discover -s scripts -p test_verify_artifacts.py -v
python scripts/verify_pages.py --output work/verify-pages-fitted-tshirt
git diff --check
```

Compare the independently rebuilt mesh bytes with
`experiments/fitted_tshirt/data/tshirt_mesh.json`; do not infer equivalence from
an exit code. `extract_patterns.py` must preserve all 126 original polylines and
27 text entities; the original three files must retain their supplied hashes.
The binary engineering project remains unresolved, and DXF units undeclared.

The browser verifier launches the real project-prefixed ephemeral HTTP surface,
requires actual model pixels, and drives render selection, pointer and keyboard
rotation, wheel zoom, wireframe, reset and the eight-size table. It saves five
actual downloads and checks each against `build.json`, then checks every source
archive entry against its stored hash. Check 375px mobile for no page overflow,
contained table scrolling, plus a separate real `--disable-webgl` browser for
loaded image fallback. A missing model must return 404. Capture console/network,
PNG evidence and the JSON report. Servers and browsers close on exit.

Before committing, record the base commit, candidate file hashes, commands and
observations under `docs/verification/fitted-tshirt-20261117/`. Inspect desktop,
model and mobile screenshots and compare against the existing site's shared
colors, typography, gutters, buttons and native text. Preserve original historical
geometry FAILs. After committing, rebuild and rerun both browser verifiers with
`--expected-commit COMMIT`, then reconcile remote main and push without force.

## Live Pages

Use the existing publication-only workflow. Do not create a CI test workflow.
After a successful run for the pushed SHA, run the same verifiers against
`https://liush2yuxjtu.github.io/pattern-agent/` with `--expected-commit SHA` and
separate live output directories. A workflow result is not browser acceptance.
Reopen remote main and the public archive. Record network blockers explicitly;
use the public-only route in `github-pages.md` if the Pages domain is blocked.
The website can PASS while physical fit and strict garment release remain NOT_RUN.
