/* Replacement for solveMembrane in the native cloth kernel.
 *
 * Same orthotropic StVK energy, reference areas, masses and XPBD compliance.
 * Only the nonlinear projection changes.  A linearized XPBD correction can
 * overshoot badly when a material direction is nearly compressed to zero.
 * Along its fixed mass-weighted gradient, C is exactly quadratic, whereas
 * alpha*lambda is linear.  Use that quadratic to shorten unsafe steps, then
 * backtrack against the ACTUAL stored f32 positions and f32 multiplier.
 *
 * Accepted updates decrease |C(x)+alpha*lambda|.  A rejected/stagnant update
 * changes neither positions nor lambda.  This is not a collision, area-barrier,
 * global energy-minimization or untangling guarantee.
 */
typedef struct { double x, y, z; } MembraneD;
static MembraneD membrane_d(V p) { return (MembraneD){p.x,p.y,p.z}; }
static MembraneD membrane_add(MembraneD a,MembraneD b) {
 return (MembraneD){a.x+b.x,a.y+b.y,a.z+b.z};
}
static MembraneD membrane_sub(MembraneD a,MembraneD b) {
 return (MembraneD){a.x-b.x,a.y-b.y,a.z-b.z};
}
static MembraneD membrane_mul(MembraneD a,double s) {
 return (MembraneD){a.x*s,a.y*s,a.z*s};
}
static double membrane_dot(MembraneD a,MembraneD b) {
 return a.x*b.x+a.y*b.y+a.z*b.z;
}
static double membrane_abs(double a) { return a<0?-a:a; }
static void membrane_frame(const V p[3],double a,double b,double c,double d,
                           MembraneD *u,MembraneD *v) {
 MembraneD e1=membrane_sub(membrane_d(p[1]),membrane_d(p[0]));
 MembraneD e2=membrane_sub(membrane_d(p[2]),membrane_d(p[0]));
 *u=membrane_add(membrane_mul(e1,a),membrane_mul(e2,c));
 *v=membrane_add(membrane_mul(e1,b),membrane_mul(e2,d));
}
static double membrane_constraint(MembraneD u,MembraneD v,int component,double r) {
 if(component==0)return .5*(membrane_dot(u,u)-1)+r*.5*(membrane_dot(v,v)-1);
 if(component==1)return .5*(membrane_dot(v,v)-1);
 return membrane_dot(u,v);
}
static void solveMembrane(int t,int component,float dt) {
 int ids[3]={vertex(faces[t*3]),vertex(faces[t*3+1]),vertex(faces[t*3+2])};
 if(ids[0]==ids[1]||ids[1]==ids[2]||ids[2]==ids[0])return;
 if(!(dt>0)||!(area[t]>0)||!(thickness>0))return;
 double a=inverseDm[4*t],b=inverseDm[4*t+1];
 double c=inverseDm[4*t+2],d=inverseDm[4*t+3];
 float q11,q22,q12,stiff,rStored;moduli(&q11,&q22,&q12);
 rStored=q12/q11;
 if(component==0)stiff=q11;
 else if(component==1)stiff=q22-q12*q12/q11;
 else stiff=G;
 if(!(stiff>0))return;
 double r=rStored,alpha=1.0/((double)stiff*thickness*area[t]*(double)dt*dt);
 if(!(alpha>0)||!__builtin_isfinite(alpha))return;
 V base[3]={x[ids[0]],x[ids[1]],x[ids[2]]};
 MembraneD u,v,gradient[3];membrane_frame(base,a,b,c,d,&u,&v);
 double C=membrane_constraint(u,v,component,r);
 if(component==0){
  gradient[1]=membrane_add(membrane_mul(u,a),membrane_mul(v,r*b));
  gradient[2]=membrane_add(membrane_mul(u,c),membrane_mul(v,r*d));
 }else if(component==1){
  gradient[1]=membrane_mul(v,b);gradient[2]=membrane_mul(v,d);
 }else{
  gradient[1]=membrane_add(membrane_mul(v,a),membrane_mul(u,b));
  gradient[2]=membrane_add(membrane_mul(v,c),membrane_mul(u,d));
 }
 gradient[0]=membrane_mul(membrane_add(gradient[1],gradient[2]),-1);
 double denominator=alpha;
 for(int k=0;k<3;k++){
  if(!(invMass[ids[k]]>=0))return;
  denominator+=(double)invMass[ids[k]]*membrane_dot(gradient[k],gradient[k]);
 }
 float *storedLambda=&lambda[t*3+component];
 double oldLambda=*storedLambda,residual=C+alpha*oldLambda;
 if(!__builtin_isfinite(residual)||!__builtin_isfinite(denominator)||residual==0)return;
 double deltaLambda=-residual/denominator;
 if(!__builtin_isfinite(deltaLambda)||deltaLambda==0)return;
 MembraneD direction[3];
 for(int k=0;k<3;k++)direction[k]=membrane_mul(gradient[k],(double)invMass[ids[k]]*deltaLambda);
 MembraneD de1=membrane_sub(direction[1],direction[0]);
 MembraneD de2=membrane_sub(direction[2],direction[0]);
 MembraneD du=membrane_add(membrane_mul(de1,a),membrane_mul(de2,c));
 MembraneD dv=membrane_add(membrane_mul(de1,b),membrane_mul(de2,d));
 double quadratic;
 if(component==0)quadratic=.5*(membrane_dot(du,du)+r*membrane_dot(dv,dv));
 else if(component==1)quadratic=.5*membrane_dot(dv,dv);
 else quadratic=membrane_dot(du,dv);
 /* R(s)/R(0)=1-s+eta*s*s.  The cancellation-free positive root is
  * in (0,1) when eta<0.  Otherwise take at most one Newton step, or the
  * quadratic minimum if it occurs before that step.  Never extrapolate. */
 double eta=quadratic/residual,step=1;
 if(!__builtin_isfinite(eta))return;
 if(eta<0)step=2/(1+__builtin_sqrt(1-4*eta));
 else if(eta>.5)step=.5/eta;
 for(int attempt=0;attempt<32&&step>0;attempt++,step*=.5){
  float candidateLambda=(float)(oldLambda+step*deltaLambda);
  double actualDelta=(double)candidateLambda-oldLambda;
  if(!__builtin_isfinite(candidateLambda))continue;
  /* Once rounding removes the multiplier update, smaller steps cannot help.
   * Build positions from its ACTUAL stored increment, preserving x/lambda
   * coupling instead of moving positions with an unrecorded increment. */
  if(actualDelta==0)break;
  double fraction=actualDelta/deltaLambda;
  if(!(fraction>0))continue;
  V candidate[3];int finite=1;
  for(int k=0;k<3;k++){
   MembraneD shift=membrane_mul(gradient[k],(double)invMass[ids[k]]*actualDelta);
   candidate[k]=(V){(float)((double)base[k].x+shift.x),
                     (float)((double)base[k].y+shift.y),
                     (float)((double)base[k].z+shift.z)};
   finite=finite&&__builtin_isfinite(candidate[k].x)&&
           __builtin_isfinite(candidate[k].y)&&__builtin_isfinite(candidate[k].z);
  }
  if(!finite)continue;
  MembraneD nextU,nextV;membrane_frame(candidate,a,b,c,d,&nextU,&nextV);
  double nextResidual=membrane_constraint(nextU,nextV,component,r)+alpha*(double)candidateLambda;
  if(__builtin_isfinite(nextResidual)&&membrane_abs(nextResidual)<membrane_abs(residual)&&
     membrane_abs(nextResidual)<=membrane_abs(residual)*(1-.0001*fraction)){
   for(int k=0;k<3;k++)x[ids[k]]=candidate[k];
   *storedLambda=candidateLambda;
   return;
  }
 }
}

/* Direct controls for independent tests of the compiled production function.
 * Normal simulation never calls these; no alternate testing implementation. */
__attribute__((export_name("membrane_projection_probe")))
void membrane_projection_probe(int t,int component,float dt) {
 if(t>=0&&t<nt&&component>=0&&component<3)solveMembrane(t,component,dt);
}
__attribute__((export_name("membrane_lambda_ptr")))
int membrane_lambda_ptr(void) { return (int)lambda; }
__attribute__((export_name("membrane_inverse_dm_ptr")))
int membrane_inverse_dm_ptr(void) { return (int)inverseDm; }
__attribute__((export_name("membrane_area_ptr")))
int membrane_area_ptr(void) { return (int)area; }
