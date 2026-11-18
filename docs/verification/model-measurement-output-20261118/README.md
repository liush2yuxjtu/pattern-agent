# Model-measured dimensions are the primary output

The user clarified that body sizes must come out of the human model. This change
adds a dedicated actual-geometry export and makes it the primary review output.
Existing states already contained calibration measurements; prior/control targets
and saved reported fields are no longer a possible substitute for the new output.

## Input and output

Input: final saved Human Studio state, matching asset and actual neutral OBJ.
Output: model-derived-measurements-v1 JSON/CSV, with measured_values_cm and
per-row value_cm computed directly from the actual mesh. Input targets are
separate target_dimensions_cm. Twelve definitions include neutral Y height,
closed authored surface tapes and two-landmark straight distances; tape lengths
are not relabelled as plane sections, nor landmark distances as bone lengths.

The standard-library exporter maps full asset indices to compact OBJ vertices,
checks asset/unit/topology and independently replays saved morph weights to
verify geometry. It never refits to targets and never reads measuredNeutral as
a value source. Source state, asset, neutral and optional posed hashes are bound.
Posed mesh is fingerprinted only; photo accuracy is not certified.

The editor recomputes from the current real Float32 rest buffer. Model measured
values are always shown below control inputs. Export measurements, CSV and
Neutral OBJ capture the same state/geometry; pending shape updates reject export.
Pose edits leave neutral dimensions unchanged. Save model/posed OBJ/GLB retain
their existing contracts.

## Actual verification

- 37 skill tests, including8 new meaningful geometry/false-target/cache/mapping/
  tamper/unit/topology/readback controls, PASS. Existing20 eval-tool tests PASS.
- All10 historical real neutral meshes independently remeasured, with maximum
  saved-morph reconstruction difference about5.03e-9cm.
- Actual linked-case measurement UI22 checks PASS, including real JSON/CSV/OBJ
  downloads, false cached1000 values, pending65ms update, cm edits preserving
  all163 pose values, joint edits preserving neutral sizes, reimport, wrong-unit
  rejection, an unreachable target combination and375px mobile.
- Counterexample: all controls at their supported maxima give waist target108cm
  but actual geometry99.0830995cm. The output correctly keeps the latter. This
  is a numeric capability-boundary test, not a size claim about a retail model.
- Initial, edited and residual actual browser neutral downloads reopen in the
  independent Python exporter. All12 sizes differ from actual browser outputs
  by at most1.83e-9cm; the bound OBJ/state hashes agree.
- Original editor36 browser regression checks PASS, plus independent decoded
  OBJ/GLB/skin/unit validation and3 genuine fault rejections.
- Official latest6-run reviewer587 checks PASS, retained4-run reviewer308 PASS.
  The verifier independently parses actual OBJ and remeasures all displayed
  primary values, checks source hashes, table numbers and real JSON/CSV downloads.
- Actual skill download20 entries match canonical source bytes/ZIP CRC. Skill
  guide/browser21 checks PASS.

New reports live under each case review/model-measurements.json and.csv, labelled
post-run geometry remeasurement. The primary table/downloads are inside native
Output. Old measurements are labelled historical. All10 raw grade JSONs, run ZIPs
and official EMBEDDED_DATA hashes are unchanged from historical-before.json.
Native viewer format/feedback/navigation/Benchmark stay intact.

The first new probe clicked a hidden Body-tab button while on Pose and timed
out; its raw report is retained. Correcting actual tab navigation fixed the
probe; no model data was repaired to pass.

This is measurement-export verification, not a fresh six-image/pose-fit skill
benchmark. No new ImageGen calls or photo refits were run. Existing photo/pose
FAIL results remain; model measurements do not establish real-person accuracy.
Native Claude triggering remains BLOCKED and physical garment fit NOT_RUN.

## Publication and live boundary

The existing Pages publisher completed commit
7c7df4127f5a0369a048b769e63de968fefe7bf4. GitHub independently read back the
fixed public helper/verifier sources and primary model-measurement report,
byte-identical with local files. This is SOURCE_READBACK PASS, not a Pages
interactive runtime result.

Live browser verification remains BLOCKED: the VM's Pages HTTPS proxy returns
CONNECT403; Firecrawl has insufficient credits and created no session; the
Playwright and separate sandbox MCP providers are unavailable; Ego CLI is absent;
root's cloud-browser bootstrap reports that its sandbox cannot be disabled.
No subscriptions, network/security changes or replacement screenshots were used.
The live22/587/308 suites, live screenshots and live measurement downloads were
NOT_RUN. Local actual browser/file tests above remain PASS. Full errors and
publication/source receipts are under live/. Account-specific billing links
are redacted from public evidence; raw responses are retained in ignored work.
