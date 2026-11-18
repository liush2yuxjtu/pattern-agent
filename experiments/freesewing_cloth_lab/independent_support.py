"""Independently reopen all-free mass, contact force and Coulomb ledgers."""
import numpy as np


def audit(data):
 s=data['support'];inv=np.asarray(data['inverseMass']);assert np.all(np.isfinite(inv)) and np.all(inv>0),'A garment vertex is fixed'
 p=np.asarray(data['positions']).reshape(-1,3);start=np.asarray(s['stepStart_m']).reshape(-1,3);old=np.asarray(s['previousAtStart_m']).reshape(-1,3);normal=np.asarray(s['normalCorrection_m']).reshape(-1,3);friction=np.asarray(s['frictionCorrection_m']).reshape(-1,3);dt=s['dt_s'];mass=1/inv
 assert s['mode']=='free-waist' and s['gravity_m_s2']==[0,-9.81,0] and s['mu']==.6 and s['drag']==.98 and s['fixed']==0
 assert np.all(np.isfinite(normal)) and np.all(np.isfinite(friction))
 gravity=np.array([0,-9.81,s['windAcceleration_m_s2']]);expected=np.sum(mass[:,None]*((p-start-s['drag']*(start-old))/dt**2-gravity),axis=0);normal_n=np.sum(mass[:,None]*normal/dt**2,axis=0);friction_n=np.sum(mass[:,None]*friction/dt**2,axis=0);residual=float(np.linalg.norm(expected-normal_n-friction_n));assert residual<1e-5,('Unaccounted external force',residual)
 for name,value in [('normal_N',normal_n),('friction_N',friction_n),('expectedContact_N',expected)]:assert np.max(np.abs(value-np.asarray(s[name])))<1e-7
 scalar=np.asarray(data['contactPressure']['correction_m']);cone=float(np.max(np.linalg.norm(friction,axis=1)-s['mu']*scalar));assert cone<1e-10,'Friction exceeds Coulomb bound'
 total=mass.sum();com=np.sum(p*mass[:,None],axis=0)/total;velocity=np.sum((p-start)*mass[:,None]/dt,axis=0)/total;weight=total*9.81;up=normal_n[1]+friction_n[1]
 assert abs(s['weight_N']-weight)<1e-10 and abs(s['up_N']-up)<1e-7 and np.max(abs(com-np.asarray(s['com_m'])))<1e-12
 assert abs(s['speed_m_s']-np.linalg.norm(velocity))<1e-10
 # Build the closure reference from UV edge lengths and original arrangement,
 # not application constraint records or the shape-matching implementation.
 n=s['waistParticles'];uv=np.asarray(data['materialCoordinates']).reshape(-1,3,2);faces=np.asarray(data['triangles']).reshape(-1,3);edges={}
 for face,material in zip(faces,uv):
  for j in range(3):
   a,b=int(face[j]),int(face[(j+1)%3])
   if a<n and b<n:edges[tuple(sorted([a,b]))]=np.linalg.norm(material[j]-material[(j+1)%3])
 assert len(edges)==n
 seed=np.asarray(data['initialPositions']).reshape(-1,3)[:n];center=np.sum(seed*mass[:n,None],axis=0)/mass[:n].sum();perimeter=np.linalg.norm(seed-np.roll(seed,-1,axis=0),axis=1).sum();rest=(seed-center)*sum(edges.values())/perimeter;reference_error=float(np.max(abs(rest-np.asarray(s['waistLocalReference_m']).reshape(-1,3))));assert reference_error<1e-12
 return {'verdict':'PASS','fixedVertices':0,'mass_kg':float(total),'weight_N':float(weight),'normal_N':normal_n.tolist(),'friction_N':friction_n.tolist(),'upward_N':float(up),'upwardToWeight':float(up/weight),'com_m':com.tolist(),'comSpeed_m_s':float(np.linalg.norm(velocity)),'equationResidual_N':residual,'coulombExcess_m':cone,'waistLocalReferenceMaxError_m':reference_error,'calibration':'NOT_VALIDATED'}
