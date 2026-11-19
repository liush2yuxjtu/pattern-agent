# Carlton 工作台源码

Rust/WASM 布料求解器、Three.js WebGPU 查看器、FreeSewing 2D 输入和同视角线稿都在这里。法向接触移植自 Pattern Agent 的 Cloth Lab。线稿来自 FreeSewing Carlton。

在本目录执行以下命令。构建需要 Node.js、npm、Rust 和 wasm32-unknown-unknown 目标。生成的 `../index.html` 可离线运行。

```sh
npm ci
cargo build --release --target wasm32-unknown-unknown --manifest-path carlton-physics/rust/Cargo.toml
node carlton-physics/verify-pressure.mjs
node carlton-physics/build.mjs
```

`diagnostics.mjs` 从同一求解实例读取应变、应力和压力。应力依据示例面料参数。压力是基于法向接触和受力面积的模型估算。
