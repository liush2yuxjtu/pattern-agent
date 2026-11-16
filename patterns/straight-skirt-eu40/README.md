# Straight skirt — Burda reference size 40

The pattern was drafted through 117 real OpenSloper MCP calls using official
OpenSloper 0.2.0. This is a selected standard reference size, not a population
average or a made-to-measure garment.

- Body: waist 740 mm, hip 980 mm; Burda regular size 40, reference height 168 cm.
- Finished: waist 750 mm, hip 1020 mm, skirt body 600 mm plus 40 mm waistband.
- Waist-to-hip 200 mm and skirt length 600 mm are explicit drafting assumptions.
- Front: cut one on fold. Back: cut two mirrored. Waistband: cut one plus fusible.
- Included allowances: 10 mm main seams, 15 mm centre back, 30 mm hem, zero fold.
- Darts retain their fabric; internal stitch marks are not cutouts.
- Back zipper 200 mm; walking slit 180 mm; waistband overlap 30 mm.

Body measurements: https://www.burdastyle.com/how-to-take-measurements
Drafting reference: https://github.com/opensloper/opensloper/blob/v0.2.0/docs/tutorials/skirt-block.md

Print `print-a4.pdf` at actual size: 14 pages including the calibration cover.
Check both sides of the printed calibration square measure 100 mm. The one-page
`print-fullsize.pdf` measures 914 × 925 mm. Read `使用说明.pdf` or `使用说明.txt`
for Chinese cutting and sewing instructions. The preview is not a cutting master.

Keep `.sloper` and `.slm` together. Reproduce in this directory with:

```sh
OPENSLOPER_CLI=/path/to/opensloper-cli python3 build_pattern.py
python3 package_pattern.py  # optional; requires reportlab and recreates the guide
```

`mcp-calls.jsonl` preserves the original call sequence, including original workspace
paths; use the portable generator above to replay in another checkout.

The native pattern reopens without errors, corresponding side seams measure
603.190504 mm each, dart legs match, and the sewn waist is 750 mm. These are
digital geometry checks. Fabric calibration, a sewn toile and human fit remain
NOT_RUN. The existing repository's T-shirt physical findings are unchanged.
