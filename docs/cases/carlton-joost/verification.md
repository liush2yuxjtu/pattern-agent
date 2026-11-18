# Local case verification

Candidate parent `6d323edbcf3b13bbabfed18d72f4267c6eb465eb`. Staged case tree before this receipt `5b7abba1f43b1cce81018413a38a95cb93bdfa66`.

- Parsed the original embedded SVG and found 20 named seam contours. Reopened the two ASTM DXFs with ezdxf and verified 20 template and 28 assembly boundaries.
- Rechecked the maximum outline deviations from the two outline CSVs and the 28-piece collar round trip from CLO.
- Decoded all 24 PNG maps for six saved pose and revision combinations. Verified map availability, 28 per-piece CSV rows per combination, and local README links.
- Read all 174 payload entries of the local ZIP and recomputed their SHA-256 digests. Both archived HTML reports resolved their local links. The archive contained 10 ZPRJ files.
- Verdict **PASS** for the portable case and ZIP. Physical fit **NOT_RUN**.
