# CLO Local

Use this plugin when the task needs the real, local CLO 3D application. For live
work, use Codex on the machine running CLO with its existing community CLO MCP
bridge registered and running. Start by checking `clo_status` and
`scene_info`. The package supplies workflows and helper scripts.

| Skill | Role |
| --- | --- |
| [clo-seam-walk](skills/clo-seam-walk/SKILL.md) | Plan, run, and verify one batch of native seams per iteration. |
| [clo-dxf-fit-review](skills/clo-dxf-fit-review/SKILL.md) | Reconstruct or open a garment, simulate the chosen poses, and review fit and line art. |
| [clo-fit-export](skills/clo-fit-export/SKILL.md) | Analyze a saved cloth GLB and produce the four maps with matching CLO fit and stress screenshots. |

```sh
codex plugin marketplace add liush2yuxjtu/pattern-agent --ref main
codex plugin add clo-local@pattern-agent
```

The existing `clo-fit` package remains available for its users. Select one of
the two packages when both are installed because they expose overlapping skills.
