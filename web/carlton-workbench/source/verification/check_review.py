"""Independently check captured WebGPU/WASM meshes against CLO_RUST JSON and VTK."""
import argparse
import base64
import json
from html import escape
from pathlib import Path
import subprocess

import numpy as np
from prepare_meshes import unpack
from run_review import read_vtk

def load(path):
    document, blob, _ = unpack(path)
    arrays = []
    for primitive in document["meshes"][0]["primitives"]:
        def read(index, dtype, width):
            accessor = document["accessors"][index]
            view = document["bufferViews"][accessor["bufferView"]]
            arr = np.frombuffer(blob, dtype=dtype, count=accessor["count"]*width, offset=view["byteOffset"])
            return arr.reshape(-1,width).astype(float if dtype=="<f4" else int)
        xyz = read(primitive["attributes"]["POSITION"], "<f4", 3)
        uv = read(primitive["attributes"]["TEXCOORD_0"], "<f4", 2)
        faces = read(primitive["indices"], "<u4", 1).reshape(-1,3)
        arrays.append((xyz,uv,faces))
    return arrays

def weighted_p95(values, weights):
    order = np.argsort(values)
    x,w = values[order], weights[order]
    return float(np.interp(.95*w.sum(), np.r_[0.,w.cumsum()], np.r_[x[0], x]))

def strain_and_area(xyz, uv, faces):
    dx3 = xyz[faces[:,1:]]-xyz[faces[:,0,None]]
    dx2 = uv[faces[:,1:]]-uv[faces[:,0,None]]
    area = abs(np.linalg.det(dx2))/2
    ok = area>0.1
    # Solve the deformation matrix from the planar basis, then use the largest singular value.
    singular = np.linalg.svd(np.linalg.solve(dx2[ok],dx3[ok]), compute_uv=False)
    return (singular[:,0]-1)*100,area,ok

def stitch_gap(xyz, links, surface=False):
    gaps=[]
    for link in links:
        if surface:
            p,a,b,c,u,v,w=link
            target = u*xyz[a]+v*xyz[b]+w*xyz[c]
        else:
            p,a,b,t=link
            target = (1-t)*xyz[a]+t*xyz[b]
        gaps.append(np.linalg.norm(xyz[p]-target))
    return max(gaps,default=0.)

def check_cases(inputs, reports, use_pockets):
    cases=json.loads((inputs/"cases.json").read_text())
    outputs=[]
    assert len(cases)==4
    links=json.loads((inputs/"assembly-stitches.json").read_text()) if use_pockets else {}
    for case in cases:
        stem = case["id"]
        parts = load(inputs/(stem+".glb"))
        metrics=json.loads((reports/(stem+".json")).read_text())
        triangles,fields=read_vtk(reports/(stem+".vtk"))
        assert len(parts)==len(metrics)==len(case["pieces"])==18
        assert len(triangles)==5764 and np.isfinite(triangles).all()
        start=0
        main_values,main_weights=[],[]
        invalid=0
        delta=0.
        for i,((xyz,uv,faces),metric) in enumerate(zip(parts,metrics)):
            assert metric["triangle_count"]==len(faces) and metric["vertex_count"]==len(xyz)
            assert np.allclose(xyz[faces],triangles[start:start+len(faces)],rtol=0,atol=1e-7)
            values, area, ok = strain_and_area(xyz,uv,faces)
            invalid+=len(ok)-int(ok.sum())
            vals=fields["engineering_strain_pct"][start:start+len(faces)][ok]
            delta=max(delta,float(np.max(abs(vals-values))))
            assert np.array_equal(ok, fields["strain_is_valid"][start:start+len(faces)].astype(bool))
            assert metric["analysed_triangles"]==ok.sum()
            assert abs(metric["strain_p95_pct"]-weighted_p95(values,area[ok]))<1e-7
            assert 0<=metric["fold_p95_deg"]<=180
            main_values.extend(values)
            main_weights.extend(area[ok])
            start+=len(faces)
        assert start==5764 and delta<0.001 and invalid==0, (stem,delta,invalid)
        stats=case["stats"]
        assert stats["finite"]==stats["selfEnabled"]=="true" and stats["steps"]==stats["gpuSteps"]=="480"
        assert float(stats["dartGap"])<2.0
        if use_pockets:
            xyz=np.concatenate([x[0] for x in parts])
            for key, surface, limit in [("darts", False, 2.0), ("pockets", True, 0.5)]:
                measured=stitch_gap(xyz,links[key],surface)
                reported=float(stats["dartGap" if key=="darts" else "pocketGap"])
                assert abs(measured-reported)<0.001 and measured<limit, (stem,key,measured,reported)
        outputs.append({
            "label":case["label"],"valid":5764-invalid,
            "strain_p95_pct":weighted_p95(np.array(main_values),np.array(main_weights)),
            "worst_piece":[case["pieces"][max(range(len(metrics)),key=lambda i:metrics[i]["strain_p95_pct"])],
                           max(m["strain_p95_pct"] for m in metrics)],
            "max_fold_p95_deg":max(m["fold_p95_deg"] for m in metrics),
            "dart_gap_mm":float(stats["dartGap"]),"pocket_gap_mm":float(stats["pocketGap"]) if use_pockets else None,
            "same_mesh_check_max_delta_pct":delta,
        })
    return outputs

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("input",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("environment",type=Path)
    args=parser.parse_args()
    inputs,out=args.input,args.output
    env=json.loads(args.environment.read_text())
    before=check_cases(inputs/"before",out/"before",False)
    after=check_cases(inputs/"browser",out/"browser",True)
    for name, expected in (("before",4),("browser",1),("reference",1)):
        assert len(json.loads((out/name/"connectivity.json").read_text())["components"])==expected
    ref=[json.loads((out/"reference"/f"pose-{i:02}.json").read_text()) for i in range(1,4)]
    assert all(len(p)==28 and sum(m["triangle_count"] for m in p)==84750 for p in ref)
    assert len({tuple(m["triangle_count"] for m in p) for p in ref})==1
    assert len(json.loads((out/"reference"/"constraints.json").read_text()))==1983
    rows=[]
    for i,(a,b) in enumerate(zip(before,after),1):
        r=out/"browser"
        assert json.loads((r/f"draft-audit-{i:02}.json").read_text()) == json.loads((r/f"reopen-{i:02}.json").read_text())
        audit=json.loads((r/f"reopen-{i:02}.json").read_text())
        assert audit["pieces"]==20 and audit["errors"]==[]
        case_settings=json.loads((inputs/"browser"/f"settings-{i:02}.json").read_text())
        stored=json.loads((r/f"draft-{i:02}.pattern.json").read_text())["draft_settings"]
        assert all(case_settings[k]==stored[k] for k in ("sa","measurements","options"))
        rows.append(f'<tr><th scope="row">{escape(b["label"])}</th><td>{a["strain_p95_pct"]:.1f}% → {b["strain_p95_pct"]:.1f}%</td>'
                    f'<td>{b["dart_gap_mm"]:.2f} mm</td><td>{b["pocket_gap_mm"]:.2f} mm</td></tr>')
    evidence={"environment":env,"browser_before":before,"browser_after":after,"reference_poses":len(ref),
              "browser_components":{"before":4,"after":1},"reference_seam_constraints":1983}
    (out/"summary.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    app=(out/"browser"/"CLO_RUST-试穿评估.html").read_text()
    reference=(out/"reference"/"CLO_RUST-试穿评估.html").read_text().split('</header>',1)[1].split('</main>',1)[0]
    screenshots=''
    for i in (1,3):
        data=base64.b64encode((out/"browser"/f"draft-{i:02}.svg").read_bytes()).decode()
        screenshots+=f'<figure><img src="data:image/svg+xml;base64,{data}" alt="实际浏览器纸样"><figcaption>{escape(after[i-1]["label"])}</figcaption></figure>'
    intro=f'''<header><h1>Carlton 试穿验收</h1>
<p>{escape(env["platform"])} · {escape(env["rust"])} · {escape(env["runner"])}</p>
<p>编辑器运行真实 WebGPU / Rust/WASM 至第 480 步。CLO_RUST 用导出的服装网格独立复算。纸样、缝合与网格核查通过。</p></header>
<section><h2>浏览器试穿结果</h2><p>18 片外层原有 4 个连通组件，接回口袋和袋盖后合为 1 个。42 个口袋约束沿用原 CLO 的前片配对，着力点由参考网格投影得到。</p>
<table><thead><tr><th scope="col">设置</th><th scope="col">全衣主应变 P95</th><th scope="col">后省最大间距</th><th scope="col">口袋最大间距</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<p>每组 5,764 面。主应变 P95 按纸样面积加权。每组的逐面主应变、三角面数和实际缝合间距均交叉核对。主要应变和折角反映导出的几何状态，面料仍为示例材质。未生成接触压力、材料应力或量产合体判定。</p></section>
<section><h2>编辑器实际纸样</h2><div class="pair">{screenshots}</div><p>四组编辑器输入均使用 FreeSewing 4.10.2 重出 20 款裁片，并写入 CLO_RUST 工程重新打开。</p></section>'''
    app=app.replace("<title>CLO_RUST 多姿势评估</title>","<title>Carlton CLO_RUST 试穿验收</title>")
    app=app.replace("</style>","table{width:100%;border-collapse:collapse;font-size:.9em}th,td{padding:.45em;border-bottom:1px solid #d4ded7;text-align:left}summary{font-weight:700;cursor:pointer}details{padding:14px 0}</style>")
    app=app.split("<main><header>",1)[0]+"<main>"+intro+app.split("</header>",1)[1]
    app=app.replace('<section><h2>缝合与工程核查</h2><ul><li>没有提供既有缝合定义。</li></ul>', '<section><h2>浏览器几何说明</h2>')
    app=app.replace("</main>",'<details><summary>原 CLO 三姿势与原工程缝合核查</summary><p>此处为原版保存的 CLO 网格，与上面的固定姿势浏览器模拟分开核查。</p>'+reference+'</details></main>')
    (out/"Carlton-CLO_RUST-验收.html").write_text(app)
    print(f'PASS · 4 × 5764 browser triangles, 3 × 84750 CLO reference triangles, 4 exact drafts, connectivity 4 → 1, native geometry comparison.')

if __name__=="__main__":
    main()
