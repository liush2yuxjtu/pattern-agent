# Existing-engine cloth laboratory

This is a new artifact; it does not replace pattern-lab or inherit another studio's verdict.

The browser owns one Garment Artifact revision. Pattern, designer, physics, debugger and timeline read that revision. Editing invalidates mesh, frames and reports. An asynchronous job must match both revision and job token before committing a frame.

Golden Garment YAML 1.1 is byte preserved (SHA256 `88a84e697273724cdb5b4a05116c00cd53b0cb75a4d7e6bdfa5d0b7fd34f181e`). All original lines and texts can be displayed in U. U→mm, seam/cut contours, quantities, orientation and material approvals remain unknown. Golden physical simulation and physical-size printing are blocked.

A separate ENGINE_CONFORMANCE source uses the official FreeSewing model and Teagan 4.10.2. A clearly recorded proportional demonstration mapping can be applied to the generic MakeHuman chest section; it is not an approved body measurement set. Teagan has two expanded body panels and two short sleeves, without a native neckband. It is not a reconstruction of the Golden long-sleeve design.

Rapier 0.21.0 WASM supplies structural and bending constraints, gravity, native self-contact, native triangle-surface/body collision, and single-particle cluster proxies with spherical joints for sewing. Structural rest metrics are established in flat panel coordinates before assembly. No self-written PBD corrector is used. The new native-joint fixture demonstrates convergence, independently of garment fit.

Three.js supplies display. A software depth-buffer renderer is available when WebGL is unavailable. This fallback does not change the WASM solver. Display and collision share exactly the same MakeHuman positions, indices and transform. Real-time GPU rendering is reported only if the browser actually creates WebGL.

Dimensionless principal stretch and adjacent-face fold angles are geometric diagnostics. Rapier tear-threshold ratios are not material stress in Pa. Physical stress and pressure stay UNKNOWN. Independent BVH vertex/face/self-intersection audits report their instantaneous limits. A passing engine fixture cannot override a failed garment or missing production input.

Python GarmentCode/Warp remains a possible separate reference computation. It is not embedded Python, a backend, or a browser-native live solve in this deliverable.
