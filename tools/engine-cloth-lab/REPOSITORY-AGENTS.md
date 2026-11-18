# Pattern Agent — agent rules

## Required workflow
- Use `/verify`, then commit directly to `main` and push to `main`.
- Do not add, configure, run, or rely on CI for verification. Keep verification local through the repository `/verify` skill.

## Direct-to-main
- Do not create or use pull requests or GitHub Issues for this workflow. Do not open a PR or Issue as an intermediate or final delivery step.
- Work on the main branch using small, reviewable, non-force commits.
- Inspect latest remote main and reconcile concurrent changes before push. Never force-push.

## Verification contract
- Before each commit, invoke `/verify` using `.agents/skills/verify/SKILL.md` and record the candidate commit, commands, observations and verdict. After verification, commit and push directly; do not substitute CI or a PR for this step.
- Always preserve local runnable tests and independent physical/geometry validators. The Skill is the orchestration layer, not a substitute for assertions.
- Do not introduce CI workflows, including GitHub Actions CI. If existing branch protection requires a hosted status check, report the blocker; never bypass protection or silently enable CI.
- Verdicts: PASS, FAIL, BLOCKED, SKIP; never infer PASS from build, exit code, image or stale log alone.
- Historical T-shirt cloth result is FAIL: maximum seam gap 7.6455 mm (>2 mm) and 20 nonadjacent face intersections (>0). Physical fit remains NOT_RUN.
- No spending, subscriptions, new paid compute or permission/security changes without the user's approval.
