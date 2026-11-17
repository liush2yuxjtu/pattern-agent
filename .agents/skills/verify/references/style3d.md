# Style3D MCP discovery and desktop integration

Working directory: repository root. The dependency-free client is
`tools/style3d/probe_mcp.py`; it must run on the **same machine as Studio**.
The current Boat experiment installed 8.0.513 and reached the login screen;
V10.1 login, real MCP and garment simulation remain unverified.

## Local client gate

```sh
python3 -m unittest discover -s tools/style3d/tests -v
python3 tools/style3d/probe_mcp.py --help
git diff --check
```

The test suite drives the public CLI over real loopback HTTP sockets. Require
JSON and SSE initialization/listing, 202 initialized notification, session and
protocol header propagation, multi-page enumeration, no tools/call, refusal
of remote/credential URLs and redirects, bounded pagination, and BLOCKED reports
for connection/protocol failures. Test servers are protocol fixtures: their
PASS is **not** a real Style3D integration or simulation PASS. They stop and
remove temporary output when the test finishes.

## Real Studio gate

Prerequisites: install the official target V10.1, finish account login, verify
the appropriate DXF license, and enable the local MCP service in the top-right
MCP control. Never bypass account, credential, license or browser restrictions.
Keep the service local; do not expose its port or commit connection secrets.

From the machine running Studio:

```sh
python3 tools/style3d/probe_mcp.py \
  --url http://127.0.0.1:57281/mcp \
  --output work/style3d-mcp-discovery.json
```

Use the address actually displayed in Studio. Require exit 0 and the full
initialize/tools/list report. Then, using the returned schemas, independently
match one read to the visible project. A `connected` discovery report cannot
establish that pattern editing, sewing, export or cloth simulation works.

On a project copy, verify known DXF units/length/count, one measured 2D edit with
readback, sewing identity/direction, a fixed avatar/material CPU simulation,
save/reopen and licensed export/reopen. Retain missing capabilities explicitly;
do not invent tool names or numeric fit results. CPU simulation is documented,
but Wine compatibility and speed must be measured. Use the user's authorized
desktop modality for the actual running machine and capture fresh GUI evidence.

Store source manifest, command output, screenshots, versions, expected/observed
values and scoped verdicts under `docs/verification/style3d-YYYYMMDD/`. Record
candidate base and exact source hashes before commit. If account/version blocks
the real surface, retain integration **BLOCKED** and garment/physical-fit
**NOT_RUN**, even when local client tests pass. Preserve existing garment FAILs.

Cleanup: close only test-created local services. Return the Boat machine to its
prior archived state after verifying a restorable snapshot; never delete the
installed software or project. Do not spend on new compute or subscriptions.

Sources and current installation evidence: [integration record](../../../../docs/style3d-integration.md).
