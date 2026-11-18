"""Independent numeric audit: this file imports no application geometry functions."""
import json,math,re,hashlib
from pathlib import Path
import numpy as np
from scipy.integrate import quad
ROOT=Path(__file__).resolve().parents[1];cases=json.loads((ROOT/'dist/verification/curve-cases.json').read_text());results=[]
def segments(part):
 result=[];start=None
 for op in part['seamOps']:
  if op['type']=='move':start=op['to'];continue
  if op['type']=='close':continue
  result.append(dict(op,**{'from':start}));start=op['to']
 return result
def vector(p):return np.array([p['x'],p['y']],float)
def coefficients(s):
 p=np.array([vector(s[k]) for k in ['from','cp1','cp2','to']]);return np.array([p[0],3*(p[1]-p[0]),3*(p[2]-2*p[1]+p[0]),p[3]-3*p[2]+3*p[1]-p[0]])
def at(s,t):
 if s['type']=='line':return vector(s['from'])*(1-t)+vector(s['to'])*t
 c=coefficients(s);return np.polynomial.polynomial.polyval(t,c)
def derivative(c,t):return c[1]+2*c[2]*t+3*c[3]*t*t
def length(s):
 if s['type']=='line':return float(np.linalg.norm(vector(s['to'])-vector(s['from'])))
 c=coefficients(s);return float(quad(lambda t:np.linalg.norm(derivative(c,t)),0,1,epsabs=1e-9,epsrel=1e-11,limit=200)[0])
def direction(s,end):
 points=[vector(s[k]) for k in ['from','cp1','cp2','to']] if s['type']=='curve' else [vector(s['from']),vector(s['to'])]
 vectors=[points[-1]-p for p in points[-2::-1]] if end else [p-points[0] for p in points[1:]]
 return next((v for v in vectors if np.linalg.norm(v)>1e-10),np.array([0.,0.]))
def joins(part):
 ss=segments(part);out=[]
 for a,b in zip(ss,ss[1:]):
  if a.get('edge')!=b.get('edge') or a.get('edge') not in ['cap','armhole','side','neck']:continue
  va,vb=direction(a,True),direction(b,False);angle=math.degrees(math.atan2(abs(va[0]*vb[1]-va[1]*vb[0]),float(np.dot(va,vb))))
  out.append({'edge':a['edge'],'from':a.get('id'),'to':b.get('id'),'gapMm':float(np.linalg.norm(vector(a['to'])-vector(b['from']))),'angleDeg':angle})
 return out
def svg_part(part):
 tokens=re.findall(r'[MLCz]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',part['seamSvg']);i=0;ops=[]
 while i<len(tokens):
  cmd=tokens[i];i+=1;keys={'M':['to'],'L':['to'],'C':['cp1','cp2','to'],'z':[]}[cmd];op={'type':{'M':'move','L':'line','C':'curve','z':'close'}[cmd]}
  for key in keys:op[key]={'x':float(tokens[i]),'y':float(tokens[i+1])};i+=2
  ops.append(op)
 raw=[o for o in part['seamOps'] if o['type']!='close'];parsed=[o for o in ops if o['type']!='close'];assert len(raw)==len(parsed)
 max_error=0
 for a,b in zip(raw,parsed):
  assert a['type']==b['type'];b['edge']=a.get('edge');b['id']=a.get('id')
  for key in ['to','cp1','cp2']:
   if key in a:max_error=max(max_error,float(np.linalg.norm(vector(a[key])-vector(b[key]))))
 return {'seamOps':ops},max_error
def audit(pattern):
 ps=pattern['parts'];cap=[s for s in segments(ps['sleeve']) if s.get('edge')=='cap'];arm=[s for id in ['front','back'] for s in segments(ps[id]) if s.get('edge')=='armhole'];al,sl=sum(map(length,arm)),sum(map(length,cap));all_joins=[dict(j,part=id) for id,p in ps.items() for j in joins(p)];stationary=[];signs=[]
 for id,p in ps.items():
  for s in segments(p):
   if s['type']!='curve':continue
   c=coefficients(s);x=[3*c[3,0],2*c[2,0],c[1,0]];y=[3*c[3,1],2*c[2,1],c[1,1]];q=x if np.max(np.abs(x))>=np.max(np.abs(y)) else y
   for root in np.roots(np.trim_zeros(q,'f')):
    if abs(root.imag)<1e-9 and 1e-7<root.real<1-1e-7 and np.linalg.norm(derivative(c,root.real))<1e-7:stationary.append({'part':id,'segment':s.get('id'),'t':float(root.real)})
   if id=='sleeve' and s.get('edge')=='cap':
    for t in np.linspace(.001,.999,2001):
     d=derivative(c,t);dd=2*c[2]+6*c[3]*t;cross=d[0]*dd[1]-d[1]*dd[0]
     if abs(cross)>1e-7:signs.append(1 if cross>0 else -1)
 sparts={};control_rounding=0
 for id,p in ps.items():sparts[id],error=svg_part(p);control_rounding=max(control_rounding,error)
 sal=sum(length(s) for id in ['front','back'] for s in segments(sparts[id]) if s.get('edge')=='armhole');ssl=sum(length(s) for s in segments(sparts['sleeve']) if s.get('edge')=='cap');svg_angle=max((j['angleDeg'] for p in sparts.values() for j in joins(p)),default=0)
 return {'armholeLengthMm':al,'sleeveCapLengthMm':sl,'seamDifferenceMm':sl-al,'applicationArcLengthErrorMm':max(abs(al-(pattern['metrics']['armF']+pattern['metrics']['armB'])),abs(sl-pattern['metrics']['sleeveCap'])),'joins':all_joins,'maxTangentMismatchDeg':max((j['angleDeg'] for j in all_joins),default=0),'maxJoinGapMm':max((j['gapMm'] for j in all_joins),default=0),'interiorStationaryPoints':stationary,'capCurvatureSignChangesSampled':sum(a!=b for a,b in zip(signs,signs[1:])),'svgControlRoundingMaxMm':control_rounding,'svgSeamDifferenceMm':ssl-sal,'svgMaxTangentMismatchDeg':svg_angle}
for c in cases:
 r={'variant':c['key'],'sourceControlPointMaxErrorMm':c['sourceControlPointMaxErrorMm']}
 for name in ['baseline','legacyOptimized','legacyFixed','smoothOptimized','smoothFixed']:r[name]=audit(c[name])
 split=c['split'];a,b=split['after'];max_shape=0
 for t in np.linspace(0,1,2001):
  candidate=at(a,t/split['t']) if t<=split['t'] else at(b,(t-split['t'])/(1-split['t']));max_shape=max(max_shape,float(np.linalg.norm(at(split['before'],t)-candidate)))
 r['splitShapeSamples']=2001;r['splitMaxShapeErrorMm']=max_shape
 assert r['sourceControlPointMaxErrorMm']==0;assert max_shape<1e-8
 for name in ['baseline','smoothOptimized','smoothFixed']:
  a=r[name];assert a['applicationArcLengthErrorMm']<1e-6;assert a['maxJoinGapMm']<1e-8;assert a['maxTangentMismatchDeg']<.000001;assert not a['interiorStationaryPoints'];assert a['svgControlRoundingMaxMm']<.01;assert a['svgMaxTangentMismatchDeg']<.1
  if name!='baseline':assert abs(a['seamDifferenceMm'])<.01;assert abs(a['svgSeamDifferenceMm'])<.01;assert a['capCurvatureSignChangesSampled']<=r['baseline']['capCurvatureSignChangesSampled']
 assert r['legacyFixed']['maxTangentMismatchDeg']>1
 results.append(r)
report={'schema':'independent-curve-audit/1','status':'PASS','scopeZh':'Teagan原始母版、配缝优化样例与精确拆分的二维数字曲线复核','methodsZh':['与Teagan 4.10.2原始制版控制点逐项对照','Python幂基形式求值与SciPy自适应积分，独立于应用的Bernstein形式和Gauss积分','按接点切线方向验证G1连续；用导数多项式求根排查曲线内部退化','每条拆分曲线抽查2001个参数点，核对形状不变','从实际SVG路径重新读取坐标，复核量化误差、弧长与接点夹角'],'beforeFixZh':'旧优化器只约束弧长，可产生接点折角；旧工程按原算法保留，新检查会标记该问题。','limitsZh':['G1切线连续不代表G2曲率连续；本轮未声明G2要求已通过','反弯检查是每段2001点的采样检查，不是对任意曲线的完备证明','未验证真实面料、人体合身与缝制效果；三维仍为裁片组装预览'],'inputSha256':hashlib.sha256((ROOT/'dist/verification/curve-cases.json').read_bytes()).hexdigest(),'variants':results}
(ROOT/'dist/verification/curve-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','variants':len(results),'maxSourceErrorMm':max(r['sourceControlPointMaxErrorMm'] for r in results),'maxArcLengthErrorMm':max(r[n]['applicationArcLengthErrorMm'] for r in results for n in ['baseline','smoothOptimized','smoothFixed']),'maxFixedJoinAngleDeg':max(r['smoothFixed']['maxTangentMismatchDeg'] for r in results),'maxFixedSeamResidualMm':max(abs(r['smoothFixed']['seamDifferenceMm']) for r in results),'maxSvgSeamResidualMm':max(abs(r['smoothFixed']['svgSeamDifferenceMm']) for r in results),'maxSplitShapeErrorMm':max(r['splitMaxShapeErrorMm'] for r in results)},ensure_ascii=False,indent=2))
