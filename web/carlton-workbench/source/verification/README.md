# 独立字段复核

`evidence.tgz` 含 Boat 的逐片 JSON、VTK、用于复核的服装 GLB 和浏览器字段 NPZ。下列命令在 `source` 目录执行。使用 NumPy 2.5.5 和 Matplotlib 3.11.2。

```sh
audit="$(mktemp -d)"
tar -xzf ../evidence.tgz -C "$audit"
cp verification/coupon.json "$audit/"
python verification/field_review.py "$audit" "$audit" '独立复算' --summary-only
```

应变核对 CLO_RUST VTK 和 WASM 浮点数组。应力由独立 QR 分解和张量特征值检查。压力从接触乘子与独立计算的变形后面积复算，并核对反力守恒。压力平面载荷对照可运行 `node carlton-physics/verify-pressure.mjs`。
