# CLO Fit Review

Install the three skills together in Codex:

```sh
codex plugin marketplace add liush2yuxjtu/pattern-agent --ref main
codex plugin add clo-fit@pattern-agent
```

Use **clo-dxf-fit-review** for the full DXF-to-CLO workflow, including [fabric selection and substitution](skills/clo-dxf-fit-review/references/fabric-selection.md) before setting the fitting baseline and [matched-view design line-art comparison](skills/clo-dxf-fit-review/references/line-art.md) when a reference is supplied. Use **clo-fit-export** for offline strain and fold analysis of an existing garment GLB. The default report is a standalone HTML with inline figures. Live simulation and pressure capture require CLO and a working CLO bridge. The exporter needs Python 3.10+ and the packages in [requirements.txt](skills/clo-fit-export/scripts/requirements.txt). Creating a native ChatGPT Page requires Pages access.

Use [**clo-seam-walk**](skills/clo-seam-walk/SKILL.md) to plan, batch, and verify native CLO sewing. Start with the [reference script and example](skills/clo-seam-walk/references/batch-workflow.md).

Try “用 clo-dxf-fit-review 从原始 DXF 生成多姿势试穿报告，让我选择下一步改版方案。”

[Reference input and illustrated report](skills/clo-dxf-fit-review/assets/examples/fitted-knit-tee/report.md)
