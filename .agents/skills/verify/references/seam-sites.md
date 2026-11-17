# Hosted sewing inspector

This surface is the **actual authenticated production Site**, not a local
artifact. Start with [seam-inspector](seam-inspector.md) and keep its evidence
separate. Working directory is the selected existing Sites checkout; obtain it
through the installed Sites skill. Resolve its unchanged identity from
`.openai/hosting.json`, then read Site ownership/access and source provenance.
Do not create another Site or change audience to obtain a passing check.

## Source and publication

For the existing inspector, the observed source revision is
`4f9aef474d7d3e76ab3da0f0f3f329479d70c365` in its **Sites source repository**;
this is distinct from Pattern Agent's commit and the model generator commit.
The production entry is
`https://fitted-tshirt-seam-proof.liushiyuxjtu.chatgpt.site`.

Follow the Sites skill for credential-safe opening, build, synchronization and
packaging. Keep scoped credentials in session memory/hidden stdin, never source,
arguments or logs. Run `python scripts/build.py` in that checkout, then the
Pattern Agent inspector verifier against its actual `dist` and downloaded GLB.
Capture source HEAD, all packaged file digests and archive SHA. Confirm source
HEAD on the remote branch and archive bytes from that same commit.

Read saved-version provenance independently after saving. Keep the submitted tar
digest distinct from `archive_storage.content_hash`: the observed backend tar
has a different container digest/size. Do not assume that means corruption or
successful normalization. To establish stored payload equality, retrieve it
through an authorized supported route and compare every regular-file digest to
the checked candidate; container metadata/padding may differ. The attempted
`download_file` read of its returned Sediment ID was refused/unresolved, so the
stored payload readback remains BLOCKED. Do not substitute a local archive or
another connector's identity for that read.

Use owner-private publishing only after confirming owner-only access; otherwise
use the operation appropriate to the existing audience. Retain deployment and
saved-version IDs. Poll only nonterminal publication; continue an existing saved
version on recovery rather than duplicating it. Native `succeeded` plus returned
URL establishes **publication**, not browser usability or garment quality.

## Live user-flow gate

Use an authorized browser session as the intended owner. Verify the real URL,
page identity, meaningful model, absence of an auth/error overlay and console
health. Recheck the selected seam's measurements against the independently
accepted model/report, not just the page's own datasets. Exercise button, 2D
edge and 3D seam selection, camera/touch controls, reload, actual report/HTML
downloads and one rejected/failed action with recovery. Reopen downloaded files
and compare hashes against the published candidate. Save screenshots and raw
observations from this same production revision.

No local route fulfillment, disabled auth, changed audience, supplied bypass
header, disabled TLS checks or substituted login page can satisfy this boundary.
Do not request or use a bypass token to make browser QA pass. If owner sign-in
requires human action, use an authorized handoff when available.

## Known state and cleanup

The recorded publication succeeded and its archive matched the tested artifact.
The configured Playwright MCP connection failed **before navigation**. Therefore
the authenticated live interaction gate is **BLOCKED**. Earlier receipts used
`NOT_RUN` for the unexecuted flow; retain those raw receipts and record BLOCKED
for this required acceptance gate. Never relabel it because 12 local groups passed.

Save project/version/deployment IDs, commit/asset digests, native publication
receipt, driver failure and any later actual browser proof under dated evidence.
Report one verdict for this scoped gate. Close only task-created browser sessions;
preserve the Site, access, history and unrelated projects. Use
[seam-pages](seam-pages.md) for companion Page file persistence, not as a substitute.
