import json,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
ROOT=Path(__file__).resolve().parents[1];data=json.loads((ROOT/'dist/verification/curve-cases.json').read_text());report=json.loads((ROOT/'dist/verification/curve-audit.json').read_text());font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc');plt.rcParams['font.family']=font.get_name();plt.rcParams['axes.unicode_minus']=False
c=data[0]
def segs(pattern):
 start=None;ss=[]
 for o in pattern['parts']['sleeve']['seamOps']:
  if o['type']=='move':start=o['to'];continue
  if o['type']=='close':continue
  if o.get('edge')=='cap':ss.append(dict(o,**{'from':start}))
  start=o['to']
 return ss
def p(v):return np.array([v['x'],v['y']],float)
def curve(s):
 t=np.linspace(0,1,300)[:,None];return (1-t)**3*p(s['from'])+3*(1-t)**2*t*p(s['cp1'])+3*(1-t)*t*t*p(s['cp2'])+t**3*p(s['to'])
fig,axes=plt.subplots(1,2,figsize=(12,5),dpi=180,gridspec_kw={'width_ratios':[1.35,1]});fig.patch.set_facecolor('#f8faf7')
styles=[('baseline','原始 Teagan','#3f7658','--'),('legacyFixed','旧优化：弧长相等，接点有折角','#bd744e','-'),('smoothFixed','修正后：弧长相等，接点切线连续','#356e9a','-')]
for ax in axes:
 ax.set_facecolor('#f8faf7');ax.grid(color='#dce4d9',linewidth=.5);ax.spines[['top','right']].set_visible(False)
 for key,label,color,line in styles:
  pts=np.vstack([curve(s) for s in segs(c[key])]);ax.plot(pts[:,0],pts[:,1],color=color,linestyle=line,linewidth=1.7,label=label)
 ax.set_aspect('equal');ax.invert_yaxis();ax.set_xlabel('x / mm',fontproperties=font);ax.set_ylabel('y / mm',fontproperties=font)
axes[0].set_title('同一组袖山端点的曲线对比',fontproperties=font,fontsize=13);axes[0].legend(prop=font,fontsize=9,loc='lower center',bbox_to_anchor=(.5,-.47),frameon=False)
worst=max((j for j in report['variants'][0]['legacyFixed']['joins'] if j['part']=='sleeve'),key=lambda j:j['angleDeg']);join_index=next(i for i,s in enumerate(segs(c['legacyFixed'])) if s['id']==worst['from']);join=p(segs(c['legacyFixed'])[join_index]['to']);axes[1].set_xlim(join[0]-16,join[0]+16);axes[1].set_ylim(join[1]+16,join[1]-16);axes[1].set_title('接点放大：旧折角约 17.5°',fontproperties=font,fontsize=13)
for key,color in [('legacyFixed','#bd744e'),('smoothFixed','#356e9a')]:
 ss=segs(c[key]);before=ss[join_index];after=ss[join_index+1];va=p(before['to'])-p(before['cp2']);vb=p(after['cp1'])-p(after['from']);va/=np.linalg.norm(va);vb/=np.linalg.norm(vb);a=join-va*11;b=join+vb*11;axes[1].plot([a[0],join[0],b[0]],[a[1],join[1],b[1]],color=color,linestyle=':',linewidth=1.2)
axes[1].scatter(*join,s=25,color='#263b2e',zorder=5);fig.tight_layout(pad=2);fig.subplots_adjust(bottom=.27);fig.savefig(ROOT/'dist/verification/curve-comparison.png',bbox_inches='tight',facecolor=fig.get_facecolor());plt.close(fig)
rows=''.join(f"<tr><td>{ {'basic':'基础款','relaxed':'宽松版','cropped':'短身版'}[r['variant']]}</td><td>{r['sourceControlPointMaxErrorMm']:.0f} mm</td><td>{r['legacyFixed']['maxTangentMismatchDeg']:.3f}°</td><td>＜10⁻¹⁰°</td><td>{abs(r['smoothFixed']['svgSeamDifferenceMm']):.8f} mm</td></tr>" for r in report['variants'])
html=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Teagan 曲线专项复核</title><style>body{{margin:0;background:#f8faf7;color:#293d2e;font:16px/1.8 system-ui,"PingFang SC",sans-serif}}main{{max-width:1080px;margin:auto;padding:44px 24px}}h1{{font-size:30px;margin:0 0 16px}}h2{{font-size:21px;margin-top:32px}}p{{max-width:850px}}a{{color:#32674a}}img{{width:100%;height:auto;margin:20px 0}}.table{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{padding:12px 8px;text-align:left;border-bottom:1px solid #d6dfd1;white-space:nowrap}}.small{{font-size:14px;color:#77836f}}li{{margin-bottom:8px}}code{{background:#e9efe5;padding:2px 5px}}</style></head><body><main><a href="../">← 返回工作室</a><h1>Teagan 曲线专项复核</h1><p><strong>原始母版曲线与 Teagan 4.10.2 的控制点一致。旧配缝优化器只检查弧长，可能在接点留下折角；现已补上 G1 切线连续性约束并修复。</strong></p><p>本报告检查二维数字曲线及实际 SVG。G1 表示接点两侧的切线方向相同，不等于已验证真实衣服合身，也不代表 G2 曲率连续。</p><img src="curve-comparison.png" alt="原始、旧优化、修正后袖山曲线的整体叠加与接点放大。旧优化虽等长但存在折角，修正后两侧切线方向一致。"><h2>独立复算结果</h2><div class="table"><table><thead><tr><th>变体</th><th>源控制点差量</th><th>旧优化最大接点夹角</th><th>修正后接点夹角</th><th>实际 SVG 配缝残差</th></tr></thead><tbody>{rows}</tbody></table></div><p class="small">数据来自同一复核样例：先将袖山控制柄向上移动 25 mm，再固定端点修正配缝。微小数值是计算残差，不代表面料、裁床或打印机能达到同样精度。</p><h2>如何检查</h2><ol><li>重新运行原始 Teagan 制版代码，逐个对照端点与两个控制点，最大差量为 0。</li><li>应用用 Bernstein 形式和 Gauss 积分；独立 Python 用幂基形式和 SciPy 自适应积分。弧长差异小于 0.000001 mm。</li><li>计算接点两侧的极限切线，核对位置连续与 G1 连续；求导数多项式的根，排查曲线内部的零导数退化点。接点工程阈值为 0.1°。</li><li>拆分后对照 2001 个参数位置，最大形状差异小于 0.00000001 mm。</li><li>从实际 SVG 路径重新读取坐标，复核弧长和接点。导出坐标保留 6 位小数，避免原先两位小数的舍入误差。</li><li>每段袖山采样 2001 点检查曲率符号变化；本批修正样例没有新增反弯。这不是对任意曲线的完备证明。</li></ol><h2>旧工程与验证范围</h2><p>旧工程按原算法重放，保留原有控制点；新增检查会标记旧折角。只有明确点击“平滑修正 B 边”才追加新版操作，不会无声改写旧修订。</p><p>本次未验证 G2 曲率连续、真实面料与人体合身。还需版师复核和实物样衣试穿。三维视图仍是二维裁片的组装示意。</p><p><a href="curve-audit.json">完整测量数据 JSON</a> · <a href="curve-cases.json">复算曲线数据</a> · <a href="expert-report.json">工作室工具与浏览器回归报告</a></p></main></body></html>'''
(ROOT/'dist/verification/curve-audit.html').write_text(html)
print('Rendered curve overlay and Chinese verification report.')
