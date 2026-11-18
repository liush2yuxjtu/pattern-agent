"""Independent NumPy pseudoinverse/SVD readback; imports no application code."""
import gzip,json,sys
import numpy as np
from pathlib import Path
data=json.loads(gzip.decompress(Path(sys.argv[1]).read_bytes()))
errors={k:0.0 for k in ['maxStrain','minStrain','area','shear']}
for case in data['cases']:
    rest=np.array(case['rest'],dtype=float);current=np.array(case['current'],dtype=float)
    dm=np.stack([rest[1]-rest[0],rest[2]-rest[0]],axis=1)
    ds=np.stack([current[1]-current[0],current[2]-current[0]],axis=1)
    f=ds@np.linalg.inv(dm)
    singular=np.linalg.svd(f,compute_uv=False)
    angle=np.deg2rad(case['grainAngle']);rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    axes=f@rotation;cos=np.dot(axes[:,0],axes[:,1])/(np.linalg.norm(axes[:,0])*np.linalg.norm(axes[:,1]))
    expected={'maxStrain':(singular[0]-1)*100,'minStrain':(singular[1]-1)*100,'area':(singular.prod()-1)*100,'shear':90-np.rad2deg(np.arccos(np.clip(cos,-1,1)))}
    assert case['field']['valid'],case['id']
    for key in errors:
        err=abs(case['field'][key]-expected[key]);errors[key]=max(errors[key],err)
        assert err<1e-5,(case['id'],key,err)
result={'status':'PASS','method':'Independent NumPy inverse + 3x2 SVD and rotated-axis arccos; no app geometry calls','caseCount':len(data['cases']),'maxAbsoluteErrors':errors,'checks':data['checks'],'summaries':data['summaries'],'human':data['human'],'limits':['This suite verifies the initializer and numeric kernel; solved body-contact geometry is verified separately in wear-report.json. Material stress is not calibrated.']}
out=Path(sys.argv[2] if len(sys.argv)>2 else '/tmp/pattern-deformation-results.json');out.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
