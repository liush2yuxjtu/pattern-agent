# Pattern Agent — agent rules

## Direct-to-main
- NO new Pull Requests and NO new GitHub Issues for this repository.
- Work on the main branch using small, reviewable, non-force commits.
- Inspect latest remote main and reconcile concurrent changes before push. Never force-push.
- Existing PRs must be reviewed for conflicts, authorship, branch freshness and tests before merge; do not blindly merge. Close superseded Issues with a factual resolution and a commit reference.

## Verification contract
- Before each commit, invoke `.agents/skills/verify/SKILL.md` and record the candidate commit, commands, observations and verdict.
- Always preserve local runnable tests and independent physical/geometry validators. The Skill is the orchestration layer, not a substitute for assertions.
- Do not add GitHub Actions CI for generic code verification. If deployment or branch rules require a hosted status check, report the dependency rather than bypassing a safety requirement.
- Verdicts: PASS, FAIL, BLOCKED, SKIP; never infer PASS from build, exit code, image or stale log alone.
- Historical T-shirt cloth result is FAIL: maximum seam gap 7.6455 mm (>2 mm) and 20 nonadjacent face intersections (>0). Physical fit remains NOT_RUN.
- No spending, subscriptions, new paid compute or permission/security changes without the user's approval.