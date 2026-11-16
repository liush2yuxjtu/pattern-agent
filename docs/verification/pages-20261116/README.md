# GitHub Pages verification

The latest result is **PASS** in [live/receipt.json](live/receipt.json).

- Public site: https://liush2yuxjtu.github.io/pattern-agent/
- Deployed product commit: `2a254fa7899bce5302aebbae87172ee29d837578`.
- GitHub Actions run `43819293093`, attempt 2: successful deployment.
- The unchanged public Python verifier passed against the live site with real
  downloads, hash comparisons, desktop/mobile, and native workbench roundtrip.
- [Operational project skill](../../../.agents/skills/verify/SKILL.md).
- [Exact remote command](live/remote-command.sh).
- [Live browser report](live/browser-report.json).
- [Desktop screenshot](live/desktop.png), [mobile screenshot](live/mobile.png).

`prepublication.json` and `postcommit.json` describe earlier states. The initial
run failed because Pages was disabled; that historical record remains intact.
The user then enabled GitHub Actions as the Pages source. The new receipt records
the actual successful rerun and independent live-browser acceptance.

Digital pattern geometry and website acceptance do not establish a printed,
sewn or human-fit approval; those remain NOT_RUN.
