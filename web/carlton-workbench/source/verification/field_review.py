"""Independent verification of captured browser fields and native CLO_RUST output."""
import argparse
import json
from html import escape
from pathlib import Path
import sys

import matplotlib
import numpy as np
from matplotlib.colors import Normalize
from check_review import load, weighted_p95, stitch_gap
from run_review import figure, plot, read_vtk

DT=1/120
LIMITS={"strain_atol_pp":.002, "strain_rtol":.0002, "stress_relative_p99":.001, "force_relative_error":.00005}

def verify_case(paths, native, case, links):
    stem=case["id"]
    parts=load(paths/(stem+".glb"))
    xyz=np.concatenate([x[0] for x in parts])
    uv=np.concatenate([x[1] for x in parts])
    f=np.concatenate([part[2]+sum(len(p[0]) for p in parts[:i]) for i,part in enumerate(parts)])
    triangles,datas=read_vtk(native/(stem+".vtk"))
    stats=json.loads((native/(stem+".json")).read_text())
    data=np.load(paths/(stem+"-fields.npz"))
    fields,pa,force,area,ln,lf,parents=[data[k] for k in (
        "fields","pressurePa","forceN","areaM2","nodeLambda","faceLambda","parents")]
    assert len(stats)==len(parts)==18 and len(f)==len(triangles)==5764 and len(xyz)==3331
    assert np.allclose(triangles,xyz[f],rtol=0,atol=1e-7)
    assert all(np.isfinite(array).all() for array in [triangles,fields,pa,force,area,ln,lf])
    assert np.all(pa>=0) and np.all(force>=0) and np.all(area>0) and np.all(ln>=0) and np.all(lf>=0)
    assert np.array_equal(parents[parents],parents)
    assert np.all(ln[np.arange(len(xyz))!=parents]==0)

    flat=uv[f[:,1:]]-uv[f[:,0,None]]
    shape=xyz[f[:,1:]]-xyz[f[:,0,None]]
    rest_area=np.abs(np.linalg.det(flat))/2
    assert (rest_area>.1).all() and datas["strain_is_valid"].all()
    # NumPy SVD verifies the engineering strain and QR yields an independent
    # tangent-plane representation of the spatial Cauchy stress tensor.
    F=np.linalg.solve(flat,shape).transpose(0,2,1)
    sv=np.linalg.svd(F,compute_uv=False)
    e=(sv[:,0]-1)*100
    native_strain_delta=float(abs(e-datas["engineering_strain_pct"]).max())
    assert native_strain_delta<.00001
    meters=data["positionsM"].astype(float)
    rest=data["uvM"].astype(float)
    assert np.allclose(meters*1000,xyz,rtol=2e-7,atol=1e-6)
    assert np.allclose(rest*1000,uv,rtol=2e-7,atol=1e-6)
    # The native GLB stores a separately rounded millimeter copy. Compare
    # the f32 WASM fields using the original meter arrays from the browser.
    F=np.linalg.solve(rest[f[:,1:]]-rest[f[:,0,None]],meters[f[:,1:]]-meters[f[:,0,None]]).transpose(0,2,1)
    sv=np.linalg.svd(F,compute_uv=False)
    wasm_expected=(sv[:,0]-1)*100
    strain_delta=float(abs(wasm_expected-fields[:,0]*100).max())
    assert np.allclose(wasm_expected,fields[:,0]*100,atol=LIMITS["strain_atol_pp"],rtol=LIMITS["strain_rtol"]), (stem,strain_delta)
    young, shear, poisson=550000.,90000.,.22
    FTF=F.transpose(0,2,1)@F
    E=(FTF-np.eye(2))*.5
    S=np.zeros_like(E)
    S[:,0,0]=young/(1-poisson**2)*(E[:,0,0]+poisson*E[:,1,1])
    S[:,1,1]=young/(1-poisson**2)*(E[:,1,1]+poisson*E[:,0,0])
    S[:,1,0]=S[:,0,1]=2*shear*E[:,0,1]
    _,R=np.linalg.qr(F)
    jac=sv[:,0]*sv[:,1]
    C=R@S@R.transpose(0,2,1)/np.maximum(jac[:,None,None],1e-8)
    principal=np.linalg.eigvalsh(C)[:,1]
    # The coarse mesh can develop extremely thin spatial triangles. Retain
    # the raw result, and report the verification subset explicitly.
    regular=jac>.025
    relative=abs(principal[regular]-fields[:,3][regular])/np.maximum(1000,abs(principal[regular]))
    p99=float(np.quantile(relative,.99))
    assert regular.sum()>5700 and p99<LIMITS["stress_relative_p99"], (stem,regular.sum(),p99)

    expected_area=np.zeros_like(area)
    shape_m=meters[f[:,1:]]-meters[f[:,0,None]]
    each_area=np.linalg.norm(np.cross(shape_m[:,0],shape_m[:,1]),axis=1)/6
    np.add.at(expected_area,f.ravel(),np.repeat(each_area,3))
    merged=np.bincount(parents,weights=expected_area,minlength=len(xyz))
    nodal=ln[parents]/DT**2 * expected_area/merged[parents]
    np.add.at(nodal,f.ravel(),np.repeat(lf/(3*DT**2),3))
    assert np.max(abs(area-expected_area))<1e-7
    assert np.max(abs(nodal-force))<1e-5 and np.max(abs(pa-nodal/expected_area))<.025
    total=float(force.sum())
    assert total>0 and abs(total-(ln.sum()+lf.sum())/DT**2)/total<LIMITS["force_relative_error"]
    assert stitch_gap(xyz,links["darts"])<2.0 and stitch_gap(xyz,links["pockets"],True)<.5
    settings=case["stats"]
    assert settings["steps"]==settings["gpuSteps"]=="480" and settings["selfEnabled"]=="true"
    lo,hi=xyz.min(axis=0),xyz.max(axis=0)
    pad=(hi[1]-lo[1])*.04
    limits=(lo-pad,hi+pad)
    views=[(0,2,1,1),(0,2,-1,-1)]
    pictures=[]
    for scalar,clip,title in [
        (np.maximum(0,fields[:,3])/1000,500,"最大主拉应力（kPa） · 示例面料"),
        (pa[f].mean(axis=1)/1000,.3,"人台法向接触压力（kPa） · 模型估算")]:
        norm=Normalize(0,clip,clip=True)
        cmap=matplotlib.colormaps["viridis"]
        pictures.append(figure(plot(triangles,views,cmap(norm(scalar)),limits,(norm,cmap)), title))
    return {
        "label":case["label"],"triangles":len(f),"strainWasmMaxDeltaPp":strain_delta,"strainNativeMaxDeltaPp":native_strain_delta,
        "stressRegularFaces":int(regular.sum()),"stressCheckJacobianMin":.025,"stressRelativeP99":p99,
        "strainP95Pct":weighted_p95(e,rest_area),"stressP95kPa":weighted_p95(np.maximum(0,fields[:,3])/1000,rest_area),
        "peakStressKPaRaw":float(fields[:,3].max()/1000),"pressurePeakKPa":float(pa.max()/1000),"normalForceN":total,
        "pressurePaMaxDelta":float(np.max(abs(pa-nodal/expected_area))),
        "dartGapMm":stitch_gap(xyz,links["darts"]),"pocketGapMm":stitch_gap(xyz,links["pockets"],True)
    }, pictures


def main():
    root,out=map(Path,sys.argv[1:3])
    browser=root/"browser"
    cases=json.loads((browser/"cases.json").read_text())
    links=json.loads((browser/"assembly-stitches.json").read_text())
    assert len(cases)==4
    coupon=json.loads((root/"coupon.json").read_text())
    assert coupon["verdict"]=="PASS" and abs(coupon["stationary"][0]["mean"]-3.924)<.025
    assert len(json.loads((out/"connectivity.json").read_text())["components"])==1
    summary=[]
    cards=[]
    for i,case in enumerate(cases,1):
        audit=json.loads((out/f"draft-audit-{i:02}.json").read_text())
        assert audit==json.loads((out/f"reopen-{i:02}.json").read_text()) and audit["pieces"]==20 and not audit["errors"]
        row,images=verify_case(browser,out,case,links)
        summary.append(row)
        cards.append(f'<section><h2>{escape(row["label"])} · 应力与压力</h2>{"".join(images)}</section>')
    results={"verdict":"PASS","runner":sys.argv[3],"cases":summary,"coupon":coupon,"limits":LIMITS}
    (out/"summary.json").write_text(json.dumps(results,ensure_ascii=False,indent=2))
    if "--summary-only" in sys.argv:
        print(json.dumps(results,ensure_ascii=False))
        return
    rows="".join(f'<tr><th scope="row">{escape(x["label"])}</th><td>{x["strainP95Pct"]:.2f}%</td>'
                 f'<td>{x["stressP95kPa"]:.1f} kPa</td><td>{x["pressurePeakKPa"]:.3f} kPa</td>'
                 f'<td>{x["normalForceN"]:.2f} N</td></tr>' for x in summary)
    content=(out/"CLO_RUST-试穿评估.html").read_text()
    header=f'''<header><h1>Carlton 试穿字段验收</h1>
<p><a href="index.html">返回编辑器</a> · <a href="evidence.tgz" download>下载逐片 JSON、字段与 VTK</a></p>
<p>{escape(sys.argv[3])} · 四组第 480 步网格。每组 18 片外层和 5,764 个三角面。</p></header>
<section><h2>求解字段</h2><table><thead><tr><th scope="col">设置</th><th scope="col">应变 P95</th><th scope="col">应力 P95</th><th scope="col">峰值压力</th><th scope="col">合计法向力</th></tr></thead><tbody>{rows}</tbody></table>
<p>CLO_RUST 独立复算主工程应变和折角。独立 NumPy 校验应力张量及接触乘子、受力面积和总反力。四组纸样均写入 Rust 工程并重开，18 片外层的严格连通检查通过。</p>
<p>应力 P95 按净样面积加权。形变后面积极小的三角面可能产生数值尖峰，原始值保存在数据中。压力是示例面料与刚性人台的数值估算，实际应力和舒适性仍待实测标定。</p>
<p>设计线稿和模拟网格均从正面观看。线稿垂臂，浏览器使用固定斜展人台。图像等比适配，现场扣合和面料会改变外观。</p></section>'''
    content=content.replace('<title>CLO_RUST 多姿势评估</title>','<link rel="icon" href="data:,"><title>Carlton CLO_RUST 试穿验收</title>')
    content=content.replace("</style>","table{width:100%;border-collapse:collapse;font-size:clamp(10px,2.5vw,15px)}th,td{text-align:left;border-bottom:1px solid #d4ded7;padding:.4em;overflow-wrap:anywhere}</style>")
    content=content.split("<main><header>",1)[0]+"<main>"+header+content.split("</header>",1)[1]
    content=content.replace('<section><h2>缝合与工程核查</h2><ul><li>没有提供既有缝合定义。</li></ul>', '<section><h2>逐片数据</h2>')
    content=content.replace("</main>","".join(cards)+"</main>")
    (out/"review.html").write_text(content)
    print(json.dumps(results,ensure_ascii=False))

if __name__=="__main__":
    main()
