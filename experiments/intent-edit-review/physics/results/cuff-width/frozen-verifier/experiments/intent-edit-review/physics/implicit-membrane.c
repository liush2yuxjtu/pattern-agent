/* Global implicit membrane minimizer for the existing native cloth kernel.
 *
 * Integration contract:
 *   1. Preserve the existing Verlet prediction and call
 *        implicit_membrane_begin(dt);
 *      immediately after prediction, before membrane/hinge/contact iterations.
 *   2. Replace the per-triangle membrane sweep in each iteration with
 *        implicit_membrane_iteration(dt);
 *      Keep hinge/body projections separate and explicitly outside this energy.
 *
 * J(x) = original orthotropic StVK energy
 *        + sum_roots .5*m*|x-predicted|^2/dt^2.
 * Material parameters, reference UV/areas, welded masses and dt are unchanged.
 * Each ACCEPTED membrane update lowers the total actual stored-coordinate J by
 * Armijo line search.  External contact/hinge projections can increase J; they
 * invalidate the L-BFGS history but NEVER reset the physical predicted target.
 * This is not a contact-energy, collision-free or real-person-fit guarantee.
 */
#define IM_HISTORY 6
typedef struct {double x,y,z;} ImplicitD;
static V im_prediction[MAXV],im_last[MAXV],im_trial[MAXV];
static V im_s[IM_HISTORY][MAXV],im_y[IM_HISTORY][MAXV];
static ImplicitD im_gradient[MAXV],im_next_gradient[MAXV];
static ImplicitD im_direction[MAXV],im_q[MAXV],im_r[MAXV];
static double im_diagonal[MAXV],im_rho[IM_HISTORY],im_alpha[IM_HISTORY];
static double im_stats[20];
static int im_head,im_count,im_active,im_nv;
static float im_dt;
static ImplicitD im_from(V a){return (ImplicitD){a.x,a.y,a.z};}
static ImplicitD im_add(ImplicitD a,ImplicitD b){return (ImplicitD){a.x+b.x,a.y+b.y,a.z+b.z};}
static ImplicitD im_sub(ImplicitD a,ImplicitD b){return (ImplicitD){a.x-b.x,a.y-b.y,a.z-b.z};}
static ImplicitD im_mul(ImplicitD a,double s){return (ImplicitD){a.x*s,a.y*s,a.z*s};}
static double im_dot(ImplicitD a,ImplicitD b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static int im_free(int i){return vertex(i)==i&&invMass[i]>0;}
static void im_accumulate(ImplicitD *g,int i,ImplicitD value){g[i]=im_add(g[i],value);}
static int im_finite_vectors(ImplicitD *values){
 for(int i=0;i<nv;i++)if(im_free(i)&&(!__builtin_isfinite(values[i].x)||
  !__builtin_isfinite(values[i].y)||!__builtin_isfinite(values[i].z)))return 0;
 return 1;
}

/* Optional gradient and rotation-equivariant scalar Gauss-Newton diagonal.
 * All geometry arithmetic is f64 on the actual f32 stored positions/rest data.
 * Fixed vertices have no optimization degree of freedom; their reactions are
 * not misrepresented as movable gradients or finite inertial masses. */
static double im_evaluate(const V *points,float dt,ImplicitD *g,double *diagonal,double *elastic){
 if(!(dt>0))return __builtin_inf();
 double inertia=0,energy=0,dt2=(double)dt*dt;
 for(int i=0;i<nv;i++){
  if(g)g[i]=(ImplicitD){0,0,0};
  if(diagonal)diagonal[i]=0;
  if(!im_free(i))continue;
  double coefficient=1.0/((double)invMass[i]*dt2);
  ImplicitD delta=im_sub(im_from(points[i]),im_from(im_prediction[i]));
  inertia+=.5*coefficient*im_dot(delta,delta);
  if(g)g[i]=im_mul(delta,coefficient);
  if(diagonal)diagonal[i]=coefficient;
 }
 float fq11,fq22,fq12;moduli(&fq11,&fq22,&fq12);
 double q11=fq11,q22=fq22,q12=fq12,shear=G,r=q12/q11;
 double k2=q22-q12*q12/q11;
 if(!(q11>0&&k2>0&&shear>0&&thickness>0))return __builtin_inf();
 for(int t=0;t<nt;t++){
  if(!(area[t]>0))return __builtin_inf();
  int ids[3]={vertex(faces[t*3]),vertex(faces[t*3+1]),vertex(faces[t*3+2])};
  if(ids[0]==ids[1]||ids[1]==ids[2]||ids[2]==ids[0])return __builtin_inf();
  double a=inverseDm[4*t],b=inverseDm[4*t+1],c=inverseDm[4*t+2],d=inverseDm[4*t+3];
  ImplicitD e1=im_sub(im_from(points[ids[1]]),im_from(points[ids[0]]));
  ImplicitD e2=im_sub(im_from(points[ids[2]]),im_from(points[ids[0]]));
  ImplicitD u=im_add(im_mul(e1,a),im_mul(e2,c));
  ImplicitD v=im_add(im_mul(e1,b),im_mul(e2,d));
  double E11=.5*(im_dot(u,u)-1),E22=.5*(im_dot(v,v)-1),E12=.5*im_dot(u,v);
  double measure=(double)area[t]*thickness;
  energy+=measure*(.5*q11*E11*E11+q12*E11*E22+.5*q22*E22*E22+2*shear*E12*E12);
  if(g){
   double S11=q11*E11+q12*E22,S22=q12*E11+q22*E22,S12=2*shear*E12;
   ImplicitD Pu=im_add(im_mul(u,S11),im_mul(v,S12));
   ImplicitD Pv=im_add(im_mul(u,S12),im_mul(v,S22));
   ImplicitD g1=im_mul(im_add(im_mul(Pu,a),im_mul(Pv,b)),measure);
   ImplicitD g2=im_mul(im_add(im_mul(Pu,c),im_mul(Pv,d)),measure);
   im_accumulate(g,ids[0],im_mul(im_add(g1,g2),-1));
   im_accumulate(g,ids[1],g1);im_accumulate(g,ids[2],g2);
  }
  if(diagonal){
   ImplicitD h0[3],h1[3],hs[3];
   h0[1]=im_add(im_mul(u,a),im_mul(v,r*b));
   h0[2]=im_add(im_mul(u,c),im_mul(v,r*d));
   h1[1]=im_mul(v,b);h1[2]=im_mul(v,d);
   hs[1]=im_add(im_mul(v,a),im_mul(u,b));
   hs[2]=im_add(im_mul(v,c),im_mul(u,d));
   h0[0]=im_mul(im_add(h0[1],h0[2]),-1);
   h1[0]=im_mul(im_add(h1[1],h1[2]),-1);
   hs[0]=im_mul(im_add(hs[1],hs[2]),-1);
   for(int k=0;k<3;k++)diagonal[ids[k]]+=measure*(q11*im_dot(h0[k],h0[k])+
     k2*im_dot(h1[k],h1[k])+shear*im_dot(hs[k],hs[k]))/3;
  }
 }
 if(g)for(int i=0;i<nv;i++)if(!im_free(i))g[i]=(ImplicitD){0,0,0};
 if(elastic)*elastic=energy;
 return energy+inertia;
}

static void im_clear_history(void){im_head=0;im_count=0;}
static void im_remember_positions(void){for(int i=0;i<nv;i++)im_last[i]=x[i];}
static void implicit_membrane_begin(float dt){
 im_clear_history();im_dt=dt;im_nv=nv;im_active=dt>0;
 for(int i=0;i<20;i++)im_stats[i]=0;
 im_stats[12]=dt;
 for(int i=0;i<nv;i++)im_prediction[i]=x[vertex(i)];
 im_remember_positions();
}
static double im_inner(ImplicitD *a,ImplicitD *b){
 double result=0;for(int i=0;i<nv;i++)if(im_free(i))result+=im_dot(a[i],b[i]);return result;
}
static double im_stored_inner(V *stored,ImplicitD *values){
 double result=0;for(int i=0;i<nv;i++)if(im_free(i))result+=im_dot(im_from(stored[i]),values[i]);return result;
}
static void im_preconditioned_direction(void){
 for(int i=0;i<nv;i++)im_direction[i]=im_free(i)?im_mul(im_gradient[i],-1/im_diagonal[i]):(ImplicitD){0,0,0};
}
static void im_lbfgs_direction(void){
 for(int i=0;i<nv;i++)im_q[i]=im_gradient[i];
 for(int j=0;j<im_count;j++){
  int slot=(im_head+IM_HISTORY-1-j)%IM_HISTORY;
  im_alpha[slot]=im_rho[slot]*im_stored_inner(im_s[slot],im_q);
  for(int i=0;i<nv;i++)if(im_free(i))im_q[i]=im_sub(im_q[i],im_mul(im_from(im_y[slot][i]),im_alpha[slot]));
 }
 for(int i=0;i<nv;i++)im_r[i]=im_free(i)?im_mul(im_q[i],1/im_diagonal[i]):(ImplicitD){0,0,0};
 for(int j=im_count-1;j>=0;j--){
  int slot=(im_head+IM_HISTORY-1-j)%IM_HISTORY;
  double beta=im_rho[slot]*im_stored_inner(im_y[slot],im_r);
  for(int i=0;i<nv;i++)if(im_free(i))im_r[i]=im_add(im_r[i],im_mul(im_from(im_s[slot][i]),im_alpha[slot]-beta));
 }
 for(int i=0;i<nv;i++)im_direction[i]=im_mul(im_r[i],-1);
}

/* With no fixed roots the exact inertial minimizer has predicted center of
 * mass.  Remove the preconditioner's artificial translation; retain the
 * correct restoring translation if an external projection moved that center.
 * Pins break translation symmetry, so no such projection is applied to them. */
static void im_translation_component(void){
 double mass=0;ImplicitD weighted=(ImplicitD){0,0,0},target=(ImplicitD){0,0,0};
 for(int i=0;i<nv;i++)if(vertex(i)==i){
  if(!(invMass[i]>0))return;
  double m=1.0/invMass[i];mass+=m;
  weighted=im_add(weighted,im_mul(im_direction[i],m));
  target=im_add(target,im_mul(im_sub(im_from(im_prediction[i]),im_from(x[i])),m));
 }
 if(!(mass>0))return;
 ImplicitD correction=im_mul(im_sub(target,weighted),1/mass);
 for(int i=0;i<nv;i++)if(im_free(i))im_direction[i]=im_add(im_direction[i],correction);
}
static void im_update_history(void){
 int slot=im_head;double sy=0,ss=0,yy=0;int finite=1;
 /* Store float history, then compute curvature on exactly that stored pair. */
 for(int i=0;i<nv;i++){
  ImplicitD s=im_free(i)?im_sub(im_from(im_trial[i]),im_from(x[i])):(ImplicitD){0,0,0};
  ImplicitD y=im_free(i)?im_sub(im_next_gradient[i],im_gradient[i]):(ImplicitD){0,0,0};
  im_s[slot][i]=(V){(float)s.x,(float)s.y,(float)s.z};
  im_y[slot][i]=(V){(float)y.x,(float)y.y,(float)y.z};
  s=im_from(im_s[slot][i]);y=im_from(im_y[slot][i]);
  sy+=im_dot(s,y);ss+=im_dot(s,s);yy+=im_dot(y,y);
  finite=finite&&__builtin_isfinite(sy)&&__builtin_isfinite(ss)&&__builtin_isfinite(yy);
 }
 if(finite&&sy>0&&sy>1e-10*__builtin_sqrt(ss*yy)){
  im_rho[slot]=1/sy;im_head=(slot+1)%IM_HISTORY;
  if(im_count<IM_HISTORY)im_count++;
 }else if(im_count==IM_HISTORY){
  /* The oldest live slot was overwritten while forming a rejected pair.
   * Clear instead of accidentally retaining corrupted curvature history. */
  im_clear_history();
 }
}

static int implicit_membrane_iteration(float dt){
 if(!im_active||im_nv!=nv||dt!=im_dt)return 0;
 int external=0;
 for(int i=0;i<nv;i++)if(vertex(i)==i&&(x[i].x!=im_last[i].x||x[i].y!=im_last[i].y||x[i].z!=im_last[i].z)){external=1;break;}
 if(external){im_clear_history();im_stats[7]++;}
 im_stats[8]++;
 double elastic=0,J=im_evaluate(x,dt,im_gradient,im_diagonal,&elastic);
 im_stats[0]=im_stats[1]=J;im_stats[2]=im_stats[3]=elastic;
 im_stats[4]=im_stats[5]=im_stats[10]=0;
 im_stats[13]=__builtin_isfinite(J)&&im_finite_vectors(im_gradient);
 if(!im_stats[13])return 0;
 im_stats[9]=__builtin_sqrt(im_inner(im_gradient,im_gradient));
 if(im_count)im_lbfgs_direction();else im_preconditioned_direction();
 im_translation_component();
 double slope=im_inner(im_gradient,im_direction);
 if(!__builtin_isfinite(slope)||!(slope<0)||!im_finite_vectors(im_direction)){
  im_clear_history();im_preconditioned_direction();im_translation_component();
  slope=im_inner(im_gradient,im_direction);
 }
 if(!__builtin_isfinite(slope)||!(slope<0)){
  im_remember_positions();im_stats[11]=im_count;return 0;
 }
 double step=1;
 for(int attempt=0;attempt<40;attempt++,step*=.5){
  int changed=0,finite=1;
  for(int i=0;i<nv;i++){
   im_trial[i]=x[i];if(!im_free(i))continue;
   im_trial[i]=(V){(float)((double)x[i].x+step*im_direction[i].x),
                   (float)((double)x[i].y+step*im_direction[i].y),
                   (float)((double)x[i].z+step*im_direction[i].z)};
   changed=changed||im_trial[i].x!=x[i].x||im_trial[i].y!=x[i].y||im_trial[i].z!=x[i].z;
   finite=finite&&__builtin_isfinite(im_trial[i].x)&&__builtin_isfinite(im_trial[i].y)&&__builtin_isfinite(im_trial[i].z);
  }
  im_stats[5]=attempt;
  if(!changed)break;
  if(!finite)continue;
  double nextElastic=0,nextJ=im_evaluate(im_trial,dt,0,0,&nextElastic);
  if(!__builtin_isfinite(nextJ)||!(nextJ<J)||nextJ>J+.0001*step*slope)continue;
  double checked=im_evaluate(im_trial,dt,im_next_gradient,0,&nextElastic);
  if(!__builtin_isfinite(checked)||!im_finite_vectors(im_next_gradient))continue;
  im_update_history();double maximum=0;
  for(int i=0;i<nv;i++)if(im_free(i)){
   ImplicitD delta=im_sub(im_from(im_trial[i]),im_from(x[i]));
   double distance=im_dot(delta,delta);if(distance>maximum)maximum=distance;
   x[i]=im_trial[i];
  }
  sync_aliases();im_remember_positions();
  im_stats[1]=checked;im_stats[3]=nextElastic;im_stats[4]=step;
  im_stats[6]++;im_stats[10]=__builtin_sqrt(maximum);im_stats[11]=im_count;
  return 1;
 }
 im_remember_positions();im_stats[11]=im_count;return 0;
}

/* Direct independent controls call the same functions used by native step(). */
__attribute__((export_name("implicit_membrane_probe_begin")))
void implicit_membrane_probe_begin(float dt){implicit_membrane_begin(dt);}
__attribute__((export_name("implicit_membrane_probe_iteration")))
int implicit_membrane_probe_iteration(float dt){return implicit_membrane_iteration(dt);}
__attribute__((export_name("implicit_membrane_probe_objective")))
double implicit_membrane_probe_objective(float dt){
 return im_active&&dt==im_dt?im_evaluate(x,dt,0,0,0):__builtin_inf();
}
__attribute__((export_name("implicit_membrane_probe_gradient")))
double implicit_membrane_probe_gradient(float dt){
 return im_active&&dt==im_dt?im_evaluate(x,dt,im_gradient,0,0):__builtin_inf();
}
__attribute__((export_name("implicit_membrane_gradient_ptr")))
int implicit_membrane_gradient_ptr(void){return (int)im_gradient;}
__attribute__((export_name("implicit_membrane_prediction_ptr")))
int implicit_membrane_prediction_ptr(void){return (int)im_prediction;}
__attribute__((export_name("implicit_membrane_stats_ptr")))
int implicit_membrane_stats_ptr(void){return (int)im_stats;}
