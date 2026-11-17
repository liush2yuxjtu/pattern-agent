# Prototype package reference page and publication

Working directory: repository root. Runtime source: `web/prototype-package/`.
Public URL: `https://liush2yuxjtu.github.io/pattern-agent/prototype-package/`.
This verifies a source-bound reference package and its website. It does not
certify semantic compilation, edited DXF output, new 3D generation or physical fit.

Prerequisites: Python, Playwright and `/usr/bin/chromium`; the existing artifact
tests also require PyMuPDF. The Cloud host has no ego-browser executable; follow
the repository's observed local Playwright path. Do not disable HTTPS verification.

```sh
python scripts/build_pages.py
python web/prototype-package/package/verify_baseline.py
python scripts/verify_prototype_package.py --output work/verify-prototype-package
python -m unittest discover -s scripts -p test_verify_artifacts.py -v
python scripts/verify_pages.py --output work/verify-pages-prototype-package
git diff --check
```

The page verifier uses the actual project-prefixed local HTTP surface. It opens
and closes the source preview, observes both responsive diagrams and their
readable labels, switches real JSON-backed examples with pointer and keyboard,
checks that the ambiguous comfort request retains an empty operation list,
saves five real downloads, verifies their build hashes and every archived file,
checks the three original source digests, drives 375px and 320px layouts, and
requires a missing archive to return 404. Browser and HTTP server close on exit.

Record the base HEAD, candidate tree and changed file hashes before each commit.
Save source checks, browser results and selected screenshots under a dated
`docs/verification/` directory. Preserve the old website by comparing all
pre-existing `web/` file bytes with the base commit. No existing page, shared
asset, builder or publication workflow needs to change for this route.

After the verified direct commit, rebuild and rerun the page verifiers with
`--expected-commit $(git rev-parse HEAD)`, then reconcile remote main and push
without force. Use the existing publication-only Pages workflow; do not add CI.

Observe the deployment for the pushed SHA, then run:

```sh
python scripts/verify_prototype_package.py \
  --base-url https://liush2yuxjtu.github.io/pattern-agent/ \
  --expected-commit DEPLOYED_SHA --output work/verify-prototype-package-live
python scripts/verify_pages.py \
  --base-url https://liush2yuxjtu.github.io/pattern-agent/ \
  --expected-commit DEPLOYED_SHA --output work/verify-pages-prototype-package-live
```

When local live TLS/network access is blocked, use the documented public-only
Firecrawl Bash route in `github-pages.md`, downloading these unchanged scripts
from the public pinned commit and verifying their reviewed digests before
execution. A deployment receipt does not replace live browser verification.
