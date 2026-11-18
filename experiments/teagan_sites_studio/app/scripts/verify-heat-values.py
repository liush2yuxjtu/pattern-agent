"""Independent SVD, ellipse quadrature and endpoint readback for the high-value audit."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.integrate import quad
r=json.loads(Path(sys.argv[1]).read_text());legacy=[]
for part in r['legacyEvidence']['parts']:
 p=part['peak'];xy=np.array([[v['x'],v['y']]for v in p['rest']])/1000;xyz=np.array(p['current']);dm=np.stack([xy[1]-xy[0],xy[2]-xy[0]],axis=1);ds=np.stack([xyz[1]-xyz[0],xyz[2]-xyz[0]],axis=1);sv=np.linalg.svd(ds@np.linalg.inv(dm),compute_uv=False);value=(sv[0]-1)*100;assert abs(value-p['maxStrain'])<1e-6
 area=abs(np.linalg.det(dm))/2*1e6;edge=max(np.linalg.norm(xy[i]-xy[(i+1)%3])*1000 for i in range(3));legacy.append({'part':part['part'],'maxStrainPercent':value,'referenceAreaMm2':area,'minimumAltitudeMm':2*area/edge})
u=r['legacyEvidence'].get('underarm')
if u:
 distance=np.linalg.norm(np.array(u['hem3dM'])-np.array(u['biceps3dM']))*1000
 assert abs(distance-u['currentChordMm'])<1e-8
 assert abs((distance/u['referenceChordMm']-1)*100-u['extensionPercent'])<1e-8
speed=lambda a:np.hypot(.78*np.cos(a),.48*np.sin(a));quarter=quad(speed,0,np.pi/2,epsabs=1e-12)[0];arc_errors=[]
for p in r['ellipseSamples']:
 angle=np.arctan2(p['x']*quarter/.78,p['z']*quarter/.48);fraction=quad(speed,0,angle,epsabs=1e-12)[0]/quarter;arc_errors.append(abs(fraction-p['fraction']))
assert max(arc_errors)<1e-7
residuals=[]
for variant in r['variants']:
 for sample in variant['samples']:
  pose=sample['sleevePose'];p=pose['inputs'];angle=pose['angle'];axis=np.array([np.cos(angle),-np.sin(angle),0]);up=np.array([np.sin(angle),np.cos(angle),0]);bottom=np.array(p['shoulderM'])+axis*p['centerlineLengthM']-2*up*p['radiusM'];residual=abs(np.linalg.norm(bottom-np.array(p['underarmM']))-p['sideChordM'])*1000;assert residual<1e-6;residuals.append(residual)
 for metric,limit in [('peakPercent',5),('areaWeightedMeanPercent',.5)]:assert abs(variant['samples'][0][metric]-variant['samples'][1][metric])<limit
r['independentReadback']={'status':'PASS','methods':['NumPy SVD of archived peak triangles','SciPy adaptive quadrature of ellipse arclength','Independent NumPy reconstruction of cuff endpoint constraints'],'legacyPeaks':legacy,'ellipseFractionMaxError':max(arc_errors),'sleeveChordMaxResidualMm':max(residuals)}
Path(sys.argv[1]).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':'PASS','legacyPeaks':legacy,'ellipseFractionMaxError':max(arc_errors),'sleeveChordMaxResidualMm':max(residuals)},ensure_ascii=False))
