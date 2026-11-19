# 独立字段复核

`evidence.tgz` 含 CLO_RUST 的逐片 JSON、VTK、用于复核的服装 GLB、浏览器字段 NPZ 和随每次模拟更新的裁片附着点。下列命令在 `source` 目录执行。使用 NumPy 2.5.5 和 Matplotlib 3.11.2。

```sh
audit="$(mktemp -d)"
tar -xzf ../evidence.tgz -C "$audit"
cp verification/coupon.json "$audit/"
python verification/field_review.py "$audit" "$audit" '独立复算' --summary-only
```

应变核对 CLO_RUST VTK 和 WASM 浮点数组。应力由独立 QR 分解和张量特征值检查。压力从接触乘子与独立计算的变形后面积复算，并核对反力守恒。压力平面载荷对照可运行 `node carlton-physics/verify-pressure.mjs`。

附着点核验独立检查贴袋与袋盖的缝合残差、袋口反折、七组领部裁片配对及六颗扣子和六个扣眼标记的前片绑定。
