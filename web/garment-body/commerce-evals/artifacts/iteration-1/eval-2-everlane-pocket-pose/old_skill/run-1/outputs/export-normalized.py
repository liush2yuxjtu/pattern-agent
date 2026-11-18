# No new fitting candidate: normalize final UI state to documented 0.1 increment and re-render all actual evidence.
from pathlib import Path
import sys,json,time,copy,shutil,csv
import numpy as np,cv2
from scipy.spatial.transform import Rotation
ROOT=Path('/workspace/work/pattern-agent');BASE=ROOT/'work/commerce-skill-evals-20261118';OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/human_fit/pose_guided'))
from runtime import Runtime,sha
from render_mesh import raster
r=Runtime();start=time.time();save=lambda n,v:(OUT/n).write_text(json.dumps(v,indent=2)+'\n');prior=json.loads((BASE/'fixtures/neutral-state.json').read_text());state=json.loads((OUT/'final-state.json').read_text());shutil.copyfile(OUT/'final-state.json',OUT/'unrounded-optimized-state.json')
for k,v in state['poseDegrees'].items():state['poseDegrees'][k]=[round(x,1) for x in v]
for k,v in state['dimensions'].items():state['dimensions'][k]=round(v,1)
cam=np.array(json.loads((OUT/'camera.json').read_text())['final']);initialcam=np.array(json.loads((OUT/'initial-camera.json').read_text())['final']);history=json.loads((OUT/'parameter-history.json').read_text());photo=cv2.imread(str(BASE/'inputs/everlane-blue-shirt/original.jpg'));h,w=photo.shape[:2];ref=cv2.imread(str(OUT/'reference-mask.png'),0)
land=json.loads((OUT/'source-landmarks.json').read_text())['coordinates'];targets={n:([v['pixel'][0]/4,v['pixel'][1]/4],v['weight']) for n,v in land.items()};t=np.array([v['pixel'] for v in land.values()]);wt=np.sqrt([v['weight'] for v in land.values()])[:,None]
def rotation(c):return Rotation.from_euler('YXZ',c[3:],degrees=True).as_matrix()
def project(p,c):q=p@rotation(c).T;return q[:,:2]*[c[0],-c[0]]+c[1:3]
source=(OUT/'solve.py').read_text();exec(source[source.index('# Keep occluded'):])
