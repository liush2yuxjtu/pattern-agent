static void solve_hinges(float dt);static void reset_hinge_lambdas();
/* Normal contact reused from this repository: web/pattern-pressure-bench.html.
 * Source provenance is recorded in PRESSURE_PROVENANCE.json. */
/* Pattern Agent cloth laboratory. MIT. SI units throughout.
 * Orthotropic StVK membrane energy solved as three coupled XPBD constraints.
 * Body collisions use closest points on the actual MakeHuman triangle BVH.
 * Bending is an explicit distance approximation, not a calibrated shell law.
 */
#define MAXV 8192
#define MAXT 8192
#define MAXS 2048
#define MAXB 16384
#define MAXBV 16000
#define MAXBF 30000
#define MAXNODE 10000
typedef struct {float x,y,z;} V;
typedef struct {float lo[3],hi[3];int left,right,start,count;} Node;
typedef struct {int a,b;float rest;} Bend;
typedef struct {int a,b,active;} Seam;
static V x[MAXV],previous[MAXV],pins[MAXV];
static float uv[MAXV*2],invMass[MAXV],contact[MAXV],distanceBody[MAXV];
static int faces[MAXT*3];
static float inverseDm[MAXT*4],area[MAXT],lambda[MAXT*3],fields[MAXT][8];
static Bend bends[MAXB];static Seam seams[MAXS];
static V body[MAXBV],bodyNormals[MAXBV];static int bodyFaces[MAXBF*3],order[MAXBF];static Node nodes[MAXNODE];
static int nv,nt,ns,nb,bodyNv,bodyNf,nodeCount,frame,collisionEnabled=1;
static int parent[MAXV],cacheEnabled=1;
static int vertex(int i){while(parent[i]!=i)i=parent[i];return i;}
static void sync_aliases(){for(int i=0;i<nv;i++)if(parent[i]!=i){x[i]=x[parent[i]];previous[i]=previous[parent[i]];}}
static V cachePoint[MAXV+MAXT];static float cacheDistance[MAXV+MAXT];
static float Eu=200000,Ev=120000,G=30000,nu=.2f,thickness=.0005f,density=.22f;
static float offsetX,margin=.006f,simTime,stats[16],probe[16];
static V add(V a,V b){return (V){a.x+b.x,a.y+b.y,a.z+b.z};}
static V sub(V a,V b){return (V){a.x-b.x,a.y-b.y,a.z-b.z};}
static V mul(V a,float s){return (V){a.x*s,a.y*s,a.z*s};}
static float dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static float root(float a){return __builtin_sqrtf(a>0?a:0);}
static float absf(float a){return a<0?-a:a;}
static float minf(float a,float b){return a<b?a:b;}
static float maxf(float a,float b){return a>b?a:b;}
static V unit(V a){return mul(a,1/maxf(root(dot(a,a)),1e-12f));}
static float boxDistance(V p,Node n){float a[3]={p.x,p.y,p.z},s=0;for(int j=0;j<3;j++){float d=maxf(0,maxf(n.lo[j]-a[j],a[j]-n.hi[j]));s+=d*d;}return s;}
/* Ericson closest point, with barycentrics retained for the body normal. */
/* Closest-feature arithmetic in f64. Body/cloth storage remains original f32.
 * Thin decimated fingertip triangles lose micrometres in f32 Gram determinants.
 */
typedef struct {double x,y,z;} DV;
static DV diff64(V a,V b){return (DV){(double)a.x-b.x,(double)a.y-b.y,(double)a.z-b.z};}
static double dot64(DV a,DV b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static V foot64(V a,DV ab,DV ac,double u,double v){return (V){a.x+ab.x*u+ac.x*v,a.y+ab.y*u+ac.y*v,a.z+ab.z*u+ac.z*v};}
static V closest(V p,V a,V b,V c,float *u,float *v){
 DV ab=diff64(b,a),ac=diff64(c,a),ap=diff64(p,a);double d1=dot64(ab,ap),d2=dot64(ac,ap);
 if(d1<=0&&d2<=0){*u=*v=0;return a;}
 DV bp=diff64(p,b);double d3=dot64(ab,bp),d4=dot64(ac,bp);
 if(d3>=0&&d4<=d3){*u=1;*v=0;return b;}
 double vc=d1*d4-d3*d2;
 if(vc<=0&&d1>=0&&d3<=0){double t=d1/(d1-d3);*u=t;*v=0;return foot64(a,ab,ac,t,0);}
 DV cp=diff64(p,c);double d5=dot64(ab,cp),d6=dot64(ac,cp);
 if(d6>=0&&d5<=d6){*u=0;*v=1;return c;}
 double vb=d5*d2-d1*d6;
 if(vb<=0&&d2>=0&&d6<=0){double t=d2/(d2-d6);*u=0;*v=t;return foot64(a,ab,ac,0,t);}
 double va=d3*d6-d5*d4;
 if(va<=0&&d4-d3>=0&&d5-d6>=0){double t=(d4-d3)/((d4-d3)+(d5-d6));*u=1-t;*v=t;return foot64(a,ab,ac,1-t,t);}
 double den=va+vb+vc,bu=vb/den,bv=vc/den;*u=bu;*v=bv;return foot64(a,ab,ac,bu,bv);
}

static V feature_normal(int face,float u,float v);
static float bounded_normal_delta(int slot,float change,float coefficient);
typedef struct {V q,n;float signedDistance;int face,faceInterior;} Hit;
static Hit nearest(V point){
 V p=point;p.x-=offsetX;float best=1e20f,bu=0,bv=0;int bestFace=0,stack[64],sp=1;stack[0]=0;V q={0,0,0};
 while(sp){int ni=stack[--sp];Node n=nodes[ni];if(boxDistance(p,n)>best)continue;
  if(n.count){for(int k=n.start;k<n.start+n.count;k++){int f=order[k],ia=bodyFaces[3*f],ib=bodyFaces[3*f+1],ic=bodyFaces[3*f+2];float u,v;V z=closest(p,body[ia],body[ib],body[ic],&u,&v);V d=sub(p,z);float ds=dot(d,d);if(ds<best){best=ds;q=z;bestFace=f;bu=u;bv=v;}}}
  else{float dl=boxDistance(p,nodes[n.left]),dr=boxDistance(p,nodes[n.right]);if(dl<dr){if(dr<=best)stack[sp++]=n.right;if(dl<=best)stack[sp++]=n.left;}else{if(dl<=best)stack[sp++]=n.left;if(dr<=best)stack[sp++]=n.right;}}
 }
 int ia=bodyFaces[3*bestFace],ib=bodyFaces[3*bestFace+1],ic=bodyFaces[3*bestFace+2];V normal=feature_normal(bestFace,bu,bv);
 float sd=root(best);int inside=dot(sub(p,q),normal)<0;if(sd>1e-10f)normal=mul(sub(p,q),(inside?-1.f:1.f)/sd);if(inside)sd=-sd;q.x+=offsetX;
 return (Hit){q,normal,sd,bestFace,bu>1e-6f&&bv>1e-6f&&1-bu-bv>1e-6f};
}
static void moduli(float *q11,float *q22,float *q12){float den=1-nu*nu*Ev/Eu;*q11=Eu/den;*q22=Ev/den;*q12=nu*Ev/den;}
/* Returns true material-coordinate strain and Cauchy stress invariants.
 * outputs: principal engineering strain, warp/weft engineering strains,
 * maximum principal Cauchy stress Pa, von Mises Pa, Green E11/E22/E12.
 */
static void material(V f0,V f1,float *out){
 float c00=dot(f0,f0),c11=dot(f1,f1),c01=dot(f0,f1),e0=(c00-1)*.5f,e1=(c11-1)*.5f,e2=c01*.5f;
 float q11,q22,q12;moduli(&q11,&q22,&q12);float s0=q11*e0+q12*e1,s1=q12*e0+q22*e1,s2=2*G*e2;
 float J=maxf(root(c00*c11-c01*c01),1e-8f),tr=(s0*c00+s1*c11+2*s2*c01)/J,det=s0*s1-s2*s2;
 float disc=root(maxf(0,tr*tr-4*det)),p1=(tr+disc)*.5f,p2=(tr-disc)*.5f;
 out[0]=root((c00+c11+root((c00-c11)*(c00-c11)+4*c01*c01))*.5f)-1;
 out[1]=root(c00)-1;out[2]=root(c11)-1;out[3]=p1;out[4]=root(p1*p1+p2*p2-p1*p2);out[5]=e0;out[6]=e1;out[7]=e2;
}
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

static void solveDistance(int a,int b,float rest,float alpha){a=vertex(a);b=vertex(b);V e=sub(x[b],x[a]);float len=root(dot(e,e)),sum=invMass[a]+invMass[b];if(sum<1e-12f||len<1e-10f)return;float r=(len-rest)/(len*(sum+alpha));x[a]=add(x[a],mul(e,r*invMass[a]));x[b]=sub(x[b],mul(e,r*invMass[b]));}
static int canSkip(V point,int key,float envelope){V local=point;local.x-=offsetX;V delta=sub(local,cachePoint[key]);float safe=cacheDistance[key]-envelope;return cacheEnabled&&safe>0&&dot(delta,delta)<safe*safe;}
static Hit cachedNearest(V point,int key){Hit h=nearest(point);cachePoint[key]=point;cachePoint[key].x-=offsetX;cacheDistance[key]=h.signedDistance;return h;}
/* Unilateral XPBD normal contact. SI units. A compliant rigid-avatar interface
 * uses mass-lumped reference areas at cloth vertices. Separate centroid guards
 * preserve a thinner 3 mm envelope through each facet and count in the force ledger.
 */
#define CONTACT_DT (1.f/120.f)
#define NORMAL_STIFFNESS_PER_AREA 1000000.f  /* Pa / m for the virtual interface layer */
static V gravity = {0, -9.81f, 0};
static float restCornerArea[MAXV], contactArea[MAXV];
static float normalLambda[MAXV+MAXT];
static V normalDirection[MAXV+MAXT];
static float nodalArea[MAXV], mergedArea[MAXV], nodalForce[MAXV], pressurePa[MAXV];
static float pressureSummary[16];
static int pressureFrame = -1;

static void invalidatePressure(void) {
    pressureFrame = -1;
}

static V crossProduct(V a, V b) {
    return (V){a.y*b.z-a.z*b.y, a.z*b.x-a.x*b.z, a.x*b.y-a.y*b.x};
}

static V gradientAtContact(V point, Hit hit) {
    // On the interior of a face the exact gradient is its geometric normal.
    const int *triangle = &bodyFaces[3*hit.face];
    const V base = body[triangle[0]];
    const V faceNormal = unit(crossProduct(sub(body[triangle[1]],base), sub(body[triangle[2]],base)));
    if (hit.faceInterior) return faceNormal;
    if (absf(hit.signedDistance) < 1e-8f) return hit.n;
    const V radial = unit(mul(sub(point,hit.q),hit.signedDistance < 0 ? -1.f : 1.f));
    // At nearly coplanar edges, suppress roundoff from subtracting the
    // closest point. At creases keep the signed edge-distance direction.
    return dot(radial,faceNormal) >= 1.f-2e-7f ? faceNormal : radial;
}

static float unilateralDelta(int slot, float signedGap, float inverseEffectiveMass, float weight) {
    const float dt = CONTACT_DT;
    const float compliance = weight > 0 ? 1 / (NORMAL_STIFFNESS_PER_AREA * weight * dt * dt) : 0;
    const float old = normalLambda[slot];
    const float delta = (-signedGap - compliance * old) / (inverseEffectiveMass + compliance);
    const float next = maxf(0, old + delta);
    normalLambda[slot] = next;
    return next - old;
}

static void collideVertex(int i) {
    if (!invMass[i] || contactArea[i] <= 0) return;
    if (normalLambda[i] == 0 && canSkip(x[i], i, margin)) return;
    const Hit hit = cachedNearest(x[i], i);
    float change = unilateralDelta(i, hit.signedDistance - margin, invMass[i], contactArea[i]);change=bounded_normal_delta(i,change,invMass[i]);
    const V n = gradientAtContact(x[i], hit);
    normalDirection[i] = n;
    x[i] = add(x[i], mul(n, change * invMass[i]));
}

static void collideCentroid(int t) {
    const int a = vertex(faces[t*3]), b = vertex(faces[t*3+1]), c = vertex(faces[t*3+2]);
    const float inverseEffectiveMass = (invMass[a] + invMass[b] + invMass[c]) / 9.f;
    if (!inverseEffectiveMass || area[t] <= 0) return;
    const V p = mul(add(x[a], add(x[b], x[c])), 1.f/3);
    const int slot = MAXV + t;
    if (normalLambda[slot] == 0 && canSkip(p, slot, margin * .5f)) return;
    const Hit hit = cachedNearest(p, slot);
    float change = unilateralDelta(slot, hit.signedDistance - margin * .5f, inverseEffectiveMass, 0);change=bounded_normal_delta(slot,change,maxf(invMass[a],maxf(invMass[b],invMass[c]))/3);
    const V n = gradientAtContact(p, hit);
    normalDirection[slot] = n;
    x[a] = add(x[a], mul(n, change * invMass[a] / 3));
    x[b] = add(x[b], mul(n, change * invMass[b] / 3));
    x[c] = add(x[c], mul(n, change * invMass[c] / 3));
}

static void reportPressure(void) {
    const float toNewtons = 1.f / (CONTACT_DT * CONTACT_DT);
    float total = 0, maxPressure = 0, footprint = 0, clothArea = 0;
    int activeSamples = 0;
    V resultant = {0,0,0};
    const int current = pressureFrame == frame && collisionEnabled;

    for (int i = 0; i < nv; i++) {
        nodalArea[i] = mergedArea[i] = nodalForce[i] = pressurePa[i] = 0;
    }
    for (int t = 0; t < nt; t++) {
        const int a = faces[t*3], b = faces[t*3+1], c = faces[t*3+2];
        const V normalArea = crossProduct(sub(x[b],x[a]), sub(x[c],x[a]));
        const float areaNow = root(dot(normalArea,normalArea))/2;
        const float corner = areaNow/3;
        clothArea += areaNow;
        nodalArea[a] += corner;
        nodalArea[b] += corner;
        nodalArea[c] += corner;
        if (!current || normalLambda[MAXV+t] <= 0) continue;
        const float force = normalLambda[MAXV+t]*toNewtons;
        total += force;
        resultant = add(resultant,mul(normalDirection[MAXV+t],force));
        const float distributed = force/3;
        nodalForce[a] += distributed;
        nodalForce[b] += distributed;
        nodalForce[c] += distributed;
        activeSamples++;
    }
    for (int i = 0; i < nv; i++) mergedArea[vertex(i)] += nodalArea[i];
    for (int i = 0; i < nv; i++) {
        if (!current) continue;
        if (vertex(i) == i && normalLambda[i] > 0) {
            const float force = normalLambda[i]*toNewtons;
            total += force;
            resultant = add(resultant,mul(normalDirection[i],force));
            activeSamples++;
        }
        const int root = vertex(i);
        if (mergedArea[root] > 0) nodalForce[i] += normalLambda[root]*toNewtons*nodalArea[i]/mergedArea[root];
        if (nodalArea[i] > 0) pressurePa[i] = nodalForce[i]/nodalArea[i];
        if (pressurePa[i] >= 1.f) footprint += nodalArea[i];
        maxPressure = maxf(maxPressure,pressurePa[i]);
    }

    pressureSummary[0] = current;
    pressureSummary[1] = total;
    pressureSummary[2] = resultant.x;
    pressureSummary[3] = resultant.y;
    pressureSummary[4] = resultant.z;
    pressureSummary[5] = maxPressure;
    pressureSummary[6] = footprint;
    pressureSummary[7] = clothArea;
    pressureSummary[8] = activeSamples;
    pressureSummary[9] = pressureFrame;
    float residual=0,alignment=1;int finite=1;
    if(current)for(int j=0;j<nv+nt;j++){
        int slot=j<nv?j:MAXV+j-nv;if(normalLambda[slot]<=0)continue;
        V p;float envelope,correction=0;
        if(j<nv){p=x[j];envelope=margin;if(invMass[j]<=0||contactArea[j]<=0){residual=1;continue;}correction=normalLambda[slot]*toNewtons/(NORMAL_STIFFNESS_PER_AREA*contactArea[j]);}
        else{int t=j-nv;p=mul(add(x[faces[t*3]],add(x[faces[t*3+1]],x[faces[t*3+2]])),1.f/3);envelope=margin*.5f;}
        Hit hit=nearest(p);float e=absf(hit.signedDistance-envelope+correction);
        residual=maxf(residual,e);alignment=minf(alignment,dot(gradientAtContact(p,hit),normalDirection[slot]));
        finite=finite&&__builtin_isfinite(e)&&__builtin_isfinite(normalLambda[slot]);
    }
    pressureSummary[10]=residual;pressureSummary[11]=alignment;
    pressureSummary[12]=finite&&__builtin_isfinite(total)&&__builtin_isfinite(maxPressure);
    pressureSummary[13]=current&&pressureSummary[12]&&residual<=.00025f&&alignment>.9f;
}

__attribute__((export_name("pressure_ptr"))) int pressure_ptr(void) { return (int)pressurePa; }
__attribute__((export_name("pressure_area_ptr"))) int pressure_area_ptr(void) { return (int)nodalArea; }
__attribute__((export_name("pressure_force_ptr"))) int pressure_force_ptr(void) { return (int)nodalForce; }
__attribute__((export_name("pressure_summary_ptr"))) int pressure_summary_ptr(void) { return (int)pressureSummary; }
__attribute__((export_name("pressure_lambda_ptr"))) int pressure_lambda_ptr(void) { return (int)normalLambda; }
__attribute__((export_name("pressure_normal_ptr"))) int pressure_normal_ptr(void) { return (int)normalDirection; }
__attribute__((export_name("pressure_face_start"))) int pressure_face_start(void) { return MAXV; }
__attribute__((export_name("pressure_dt"))) float pressure_dt(void) { return CONTACT_DT; }
__attribute__((export_name("pressure_stiffness"))) float pressure_stiffness(void) { return NORMAL_STIFFNESS_PER_AREA; }
__attribute__((export_name("pressure_margin"))) float pressure_margin(void) { return margin; }
__attribute__((export_name("pressure_restore"))) void pressure_restore(int valid) {
    pressureFrame = valid && collisionEnabled ? frame : -1;
}
__attribute__((export_name("set_gravity"))) void set_gravity(float ax,float ay,float az) { gravity = (V){ax,ay,az}; }

__attribute__((export_name("position_ptr"))) int position_ptr(){return (int)x;}__attribute__((export_name("previous_ptr"))) int previous_ptr(){return (int)previous;}__attribute__((export_name("pin_ptr"))) int pin_ptr(){return (int)pins;}__attribute__((export_name("uv_ptr"))) int uv_ptr(){return (int)uv;}__attribute__((export_name("face_ptr"))) int face_ptr(){return (int)faces;}__attribute__((export_name("invmass_ptr"))) int invmass_ptr(){return (int)invMass;}__attribute__((export_name("field_ptr"))) int field_ptr(){return (int)fields;}__attribute__((export_name("contacts_ptr"))) int contacts_ptr(){return (int)contact;}__attribute__((export_name("body_distance_ptr"))) int body_distance_ptr(){return (int)distanceBody;}__attribute__((export_name("stats_ptr"))) int stats_ptr(){return (int)stats;}__attribute__((export_name("probe_ptr"))) int probe_ptr(){return (int)probe;}
__attribute__((export_name("body_ptr"))) int body_ptr(){return (int)body;}__attribute__((export_name("body_normal_ptr"))) int body_normal_ptr(){return (int)bodyNormals;}__attribute__((export_name("body_face_ptr"))) int body_face_ptr(){return (int)bodyFaces;}__attribute__((export_name("body_order_ptr"))) int body_order_ptr(){return (int)order;}__attribute__((export_name("body_node_ptr"))) int body_node_ptr(){return (int)nodes;}
__attribute__((export_name("configure_body"))) void configure_body(int v,int f,int n){bodyNv=v;bodyNf=f;nodeCount=n;}
__attribute__((export_name("configure_material"))) void configure_material(float eu,float ev,float shear,float poisson,float thick,float rho){Eu=eu;Ev=ev;G=shear;nu=poisson;thickness=thick;density=rho;}
__attribute__((export_name("configure_cloth"))) void configure_cloth(int v,int f){nv=v;nt=f;ns=0;nb=0;for(int i=0;i<MAXV+MAXT;i++)cacheDistance[i]=-1e6f;frame=0;simTime=0;offsetX=0;invalidatePressure();for(int i=0;i<nv;i++){parent[i]=i;previous[i]=x[i];pins[i]=x[i];contact[i]=0;invMass[i]=0;restCornerArea[i]=0;contactArea[i]=0;}
 for(int t=0;t<nt;t++){int i=faces[t*3],j=faces[t*3+1],k=faces[t*3+2];float a=uv[2*j]-uv[2*i],b=uv[2*k]-uv[2*i],c=uv[2*j+1]-uv[2*i+1],d=uv[2*k+1]-uv[2*i+1],det=a*d-b*c;inverseDm[4*t]=d/det;inverseDm[4*t+1]=-b/det;inverseDm[4*t+2]=-c/det;inverseDm[4*t+3]=a/det;area[t]=absf(det)*.5f;restCornerArea[i]+=area[t]/3;restCornerArea[j]+=area[t]/3;restCornerArea[k]+=area[t]/3;float mass=area[t]*density/3;invMass[i]+=mass;invMass[j]+=mass;invMass[k]+=mass;}
 for(int i=0;i<nv;i++)invMass[i]=1/maxf(invMass[i],1e-9f);
}
__attribute__((export_name("set_pin"))) void set_pin(int i){invMass[i]=0;}
__attribute__((export_name("add_seam"))) void add_seam(int a,int b,int active){if(ns<MAXS)seams[ns++]=(Seam){a,b,active};}
__attribute__((export_name("add_bend"))) void add_bend(int a,int b,float rest){if(nb<MAXB)bends[nb++]=(Bend){a,b,rest};}
__attribute__((export_name("set_collision"))) void set_collision(int enabled){collisionEnabled=enabled;invalidatePressure();}
__attribute__((export_name("set_body_offset"))) void set_body_offset(float xoff){invalidatePressure();float delta=xoff-offsetX;offsetX=xoff;for(int i=0;i<nv;i++)if(parent[i]==i&&invMass[i]==0){pins[i].x+=delta;x[i]=pins[i];previous[i]=x[i];}sync_aliases();}
__attribute__((export_name("inject_vertex"))) void inject_vertex(int i,float px,float py,float pz){invalidatePressure();i=vertex(i);x[i]=(V){px,py,pz};previous[i]=x[i];sync_aliases();}
__attribute__((export_name("material_probe"))) void material_probe(float ux,float uy,float uz,float vx,float vy,float vz){material((V){ux,uy,uz},(V){vx,vy,vz},probe);}
__attribute__((export_name("collision_probe"))) void collision_probe(float px,float py,float pz){Hit h=nearest((V){px,py,pz});probe[0]=h.signedDistance;probe[1]=h.q.x;probe[2]=h.q.y;probe[3]=h.q.z;probe[4]=h.n.x;probe[5]=h.n.y;probe[6]=h.n.z;}
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

__attribute__((export_name("step"))) void step(int count,float wind){const float dt=CONTACT_DT;for(int s=0;s<count;s++){
 for(int i=0;i<nv;i++){contact[i]=0;if(parent[i]!=i)continue;if(invMass[i]==0){x[i]=pins[i];previous[i]=x[i];continue;}V velocity=mul(sub(x[i],previous[i]),.993f);float speed=root(dot(velocity,velocity));if(speed>.025f)velocity=mul(velocity,.025f/speed);previous[i]=x[i];x[i]=add(x[i],velocity);x[i]=add(x[i],mul(gravity,dt*dt));x[i].z+=wind*dt*dt;}
 for(int i=0;i<nt*3;i++)lambda[i]=0;reset_hinge_lambdas();
 for(int i=0;i<nv;i++){normalLambda[i]=0;normalDirection[i]=(V){0,0,0};}
 for(int t=0;t<nt;t++){normalLambda[MAXV+t]=0;normalDirection[MAXV+t]=(V){0,0,0};}
 implicit_membrane_begin(dt);for(int it=0;it<24;it++){
  implicit_membrane_iteration(dt);
  for(int j=0;j<nb;j++)solveDistance(bends[j].a,bends[j].b,bends[j].rest,1/(.04f*dt*dt));solve_hinges(dt);
  for(int j=0;j<ns;j++)if(seams[j].active)solveDistance(seams[j].a,seams[j].b,0,0);
  if(collisionEnabled){for(int i=0;i<nv;i++)collideVertex(i);if(it%3==2)for(int t=0;t<nt;t++)collideCentroid(t);}
 }
 /* Final contact/seam projection, alternating to keep both residuals visible. */
 for(int it=0;it<16;it++){for(int j=0;j<ns;j++)if(seams[j].active)solveDistance(seams[j].a,seams[j].b,0,0);if(collisionEnabled){for(int i=0;i<nv;i++)collideVertex(i);for(int t=0;t<nt;t++)collideCentroid(t);}}
 sync_aliases();frame++;simTime+=dt;pressureFrame=collisionEnabled?frame:-1;for(int i=0;i<nv;i++)contact[i]=collisionEnabled&&normalLambda[vertex(i)]>0;
}}
static void analyzeCoverage(void);
__attribute__((export_name("analyze"))) void analyze(){float maxGap=0,maxPen=0,minClear=1e6f,maxStrain=-1,maxStress=0,contacts=0,energy=0;int finite=1;for(int t=0;t<nt;t++){int i0=faces[t*3],i1=faces[t*3+1],i2=faces[t*3+2];V e1=sub(x[i1],x[i0]),e2=sub(x[i2],x[i0]);V u=add(mul(e1,inverseDm[4*t]),mul(e2,inverseDm[4*t+2])),v=add(mul(e1,inverseDm[4*t+1]),mul(e2,inverseDm[4*t+3]));material(u,v,fields[t]);maxStrain=maxf(maxStrain,fields[t][0]);maxStress=maxf(maxStress,fields[t][3]);float q11,q22,q12;moduli(&q11,&q22,&q12);float a=fields[t][5],b=fields[t][6],c=fields[t][7];energy+=(.5f*q11*a*a+q12*a*b+.5f*q22*b*b+2*G*c*c)*area[t]*thickness;}
 for(int j=0;j<ns;j++)if(seams[j].active){V e=sub(x[seams[j].a],x[seams[j].b]);maxGap=maxf(maxGap,root(dot(e,e)));}
 for(int i=0;i<nv;i++){Hit h=nearest(x[i]);distanceBody[i]=h.signedDistance;minClear=minf(minClear,h.signedDistance);maxPen=maxf(maxPen,-h.signedDistance);contacts+=pressureFrame==frame&&normalLambda[vertex(i)]>0;finite=finite&&__builtin_isfinite(x[i].x)&&__builtin_isfinite(x[i].y)&&__builtin_isfinite(x[i].z);}
 stats[0]=frame;stats[1]=simTime;stats[2]=maxGap;stats[3]=maxPen;stats[4]=minClear;stats[5]=maxStrain;stats[6]=maxStress;stats[7]=contacts;stats[8]=finite;stats[9]=energy;stats[10]=collisionEnabled;reportPressure();analyzeCoverage();
}

__attribute__((export_name("set_clock"))) void set_clock(int n,float t){frame=n;simTime=t;}

/* Ideal sewn joints share positional degrees of freedom. Material coordinates
 * remain per-panel, so unequal lengths and reversed sewing remain detectable. */
__attribute__((export_name("finalize_seams"))) void finalize_seams(){
 for(int j=0;j<ns;j++)if(seams[j].active){int a=vertex(seams[j].a),b=vertex(seams[j].b);if(a!=b)parent[b]=a;}
 float mass[MAXV];int fixed[MAXV];for(int i=0;i<nv;i++){mass[i]=0;fixed[i]=0;parent[i]=vertex(i);}
 for(int i=0;i<nv;i++){contactArea[parent[i]]+=restCornerArea[i];if(invMass[i]==0)fixed[parent[i]]=1;else mass[parent[i]]+=1/invMass[i];}
 for(int i=0;i<nv;i++){if(parent[i]!=i)invMass[i]=0;else invMass[i]=fixed[i]?0:1/maxf(mass[i],1e-9f);}
 sync_aliases();
}

__attribute__((export_name("set_cache"))) void set_cache(int enabled){cacheEnabled=enabled;}

__attribute__((export_name("get_frame"))) int get_frame(){return frame;}
__attribute__((export_name("get_time"))) float get_time(){return simTime;}
__attribute__((export_name("pressure_clear"))) void pressure_clear(){
 for(int i=0;i<nv;i++){normalLambda[i]=0;normalDirection[i]=(V){0,0,0};contact[i]=0;}
 for(int t=0;t<nt;t++){normalLambda[MAXV+t]=0;normalDirection[MAXV+t]=(V){0,0,0};}
 pressureFrame=-1;
}

/* Independent render-space coverage gate: unchanged central avatar geometry,
 * four orthographic views of the intended hip/upper-thigh region. This is a
 * depth test on real triangles, not skin recoloring or renderer draw order. */
#define CW 48
#define CH 40
static float coverageStats[16], coverBody[CW*CH], coverCloth[CW*CH];
static void rasterCoverage(float *depth,int view,int isBody){
 const int count=isBody?bodyNf:nt;const float h0=view<2?-.23f:-.13f,h1=view<2?.23f:.19f;
 const float y0=.70f,y1=.985f,sign=(view%2)?-1.f:1.f;
 for(int t=0;t<count;t++){
  V q[3];float h[3],v[3],d[3];
  for(int j=0;j<3;j++){q[j]=isBody?body[bodyFaces[t*3+j]]:x[faces[t*3+j]];if(!isBody)q[j].x-=offsetX;h[j]=view<2?q[j].x:q[j].z;v[j]=q[j].y;d[j]=sign*(view<2?q[j].z:q[j].x);}
  if(isBody&&(minf(q[0].x,minf(q[1].x,q[2].x))>.24f||maxf(q[0].x,maxf(q[1].x,q[2].x))<-.24f))continue;
  float den=(v[1]-v[2])*(h[0]-h[2])+(h[2]-h[1])*(v[0]-v[2]);if(absf(den)<1e-12f)continue;
  int loH=(int)((minf(h[0],minf(h[1],h[2]))-h0)/(h1-h0)*CW)-1,hiH=(int)((maxf(h[0],maxf(h[1],h[2]))-h0)/(h1-h0)*CW)+1;
  int loV=(int)((minf(v[0],minf(v[1],v[2]))-y0)/(y1-y0)*CH)-1,hiV=(int)((maxf(v[0],maxf(v[1],v[2]))-y0)/(y1-y0)*CH)+1;
  if(loH<0)loH=0;if(hiH>=CW)hiH=CW-1;if(loV<0)loV=0;if(hiV>=CH)hiV=CH-1;
  for(int iy=loV;iy<=hiV;iy++)for(int ih=loH;ih<=hiH;ih++){
   const float a=h0+(ih+.5f)/CW*(h1-h0),b=y0+(iy+.5f)/CH*(y1-y0);
   const float u=((v[1]-v[2])*(a-h[2])+(h[2]-h[1])*(b-v[2]))/den;
   const float z=((v[2]-v[0])*(a-h[2])+(h[0]-h[2])*(b-v[2]))/den;
   if(u>=-1e-6f&&z>=-1e-6f&&u+z<=1.000001f){const float value=u*d[0]+z*d[1]+(1-u-z)*d[2];int k=iy*CW+ih;if(value>depth[k])depth[k]=value;}
  }
 }
}
static void analyzeCoverage(void){
 int total=0,exposed=0;float deficit=0;
 for(int view=0;view<4;view++){
  for(int k=0;k<CW*CH;k++){coverBody[k]=-1e10f;coverCloth[k]=-1e10f;}
  rasterCoverage(coverBody,view,1);rasterCoverage(coverCloth,view,0);int n=0,bad=0;
  for(int k=0;k<CW*CH;k++)if(coverBody[k]>-1e9f){n++;if(coverCloth[k]<coverBody[k]+.0001f){bad++;if(coverCloth[k]>-1e9f)deficit=maxf(deficit,coverBody[k]-coverCloth[k]);}}
  coverageStats[3+view]=bad;coverageStats[7+view]=n;total+=n;exposed+=bad;
 }
 coverageStats[0]=total;coverageStats[1]=exposed;coverageStats[2]=deficit;coverageStats[11]=total>0&&exposed==0;
}
__attribute__((export_name("coverage_ptr"))) int coverage_ptr(){return (int)coverageStats;}
__attribute__((export_name("pressure_valid"))) int pressure_valid(){return pressureFrame==frame&&collisionEnabled;}

/* Experimental complete-surface sampling, appended to the shared native kernel.
 * Uses the same actual-body BVH; never substitutes a primitive collider.
 * Vertex-only contacts cannot certify cloth triangles spanning a concavity.
 */
static V bodyEdgeNormals[MAXBF*3];
static float projectionCap=.0005f;
__attribute__((export_name("set_projection_cap"))) void set_projection_cap(float value){projectionCap=value;}
static V clipped_projection(V d,float coefficient){float l=root(dot(d,d)),limit=projectionCap/maxf(coefficient,1e-12f);return l>limit?mul(d,limit/l):d;}
static float bounded_normal_delta(int slot,float change,float coefficient){
 float limit=projectionCap/maxf(coefficient,1e-12f),bounded=maxf(-limit,minf(limit,change));normalLambda[slot]+=bounded-change;return bounded;
}
__attribute__((export_name("body_edge_normal_ptr"))) int body_edge_normal_ptr(){return (int)bodyEdgeNormals;}
static V feature_normal(int face,float u,float v){
 float bary[3]={1-u-v,u,v};int zeros=0,zero=-1,largest=0;
 for(int k=0;k<3;k++){if(bary[k]<1e-6f){zeros++;zero=k;}if(bary[k]>bary[largest])largest=k;}
 int *ids=&bodyFaces[face*3];
 if(zeros>=2)return bodyNormals[ids[largest]];
 if(zeros==1)return bodyEdgeNormals[face*3+(zero+1)%3];
 V a=sub(body[ids[1]],body[ids[0]]),b=sub(body[ids[2]],body[ids[0]]);
 return unit((V){a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x});
}
static void project_rigid_vertex(int i){
 if(parent[i]!=i||invMass[i]==0)return;Hit h=nearest(x[i]);if(h.signedDistance>=margin)return;
 V delta=clipped_projection(sub(add(h.q,mul(h.n,margin)),x[i]),1);x[i]=add(x[i],delta);previous[i]=add(previous[i],mul(delta,.8f));contact[i]=1;
}
static void project_rigid_centroid(int t){
 int a=vertex(faces[t*3]),b=vertex(faces[t*3+1]),c=vertex(faces[t*3+2]);float total=invMass[a]+invMass[b]+invMass[c];if(total<1e-12f)return;
 V p=mul(add(x[a],add(x[b],x[c])),1.f/3);Hit h=nearest(p);if(h.signedDistance>=margin)return;
 V delta=clipped_projection(sub(add(h.q,mul(h.n,margin)),p),3*maxf(invMass[a],maxf(invMass[b],invMass[c]))/total);int ids[3]={a,b,c};for(int k=0;k<3;k++){
  int i=ids[k];V d=mul(delta,3*invMass[i]/total);x[i]=add(x[i],d);previous[i]=add(previous[i],mul(d,.8f));contact[i]=1;
 }
}
static void project_midpoint(int a,int b){
 a=vertex(a);b=vertex(b);float total=invMass[a]+invMass[b];
 if(total<1e-12f)return;
 V p=mul(add(x[a],x[b]),.5f);Hit h=nearest(p);
 if(h.signedDistance>=margin)return;
 V delta=clipped_projection(sub(add(h.q,mul(h.n,margin)),p),2*maxf(invMass[a],invMass[b])/total);
 V da=mul(delta,2*invMass[a]/total),db=mul(delta,2*invMass[b]/total);
 x[a]=add(x[a],da);x[b]=add(x[b],db);
 previous[a]=add(previous[a],mul(da,.8f));previous[b]=add(previous[b],mul(db,.8f));
 contact[a]=contact[b]=1;
}
__attribute__((export_name("project_surface_contacts"))) void project_surface_contacts(int rounds){
 for(int it=0;it<rounds;it++){
  for(int i=0;i<nv;i++)project_rigid_vertex(i);
  for(int j=0;j<nt;j++){
   int t=it%2?nt-1-j:j,a=faces[3*t],b=faces[3*t+1],c=faces[3*t+2];
   project_midpoint(a,b);project_midpoint(b,c);project_midpoint(c,a);project_rigid_centroid(t);
  }
 }
 sync_aliases();
 for(int i=0;i<nv;i++)if(parent[i]!=i)contact[i]=contact[vertex(i)];
}
__attribute__((export_name("set_contact_margin"))) void set_contact_margin(float value){margin=value;}
__attribute__((export_name("seam_count"))) int seam_count(){return ns;}
__attribute__((export_name("bend_count"))) int bend_count(){return nb;}
/* Zero-restitution normal response and explicit numerical viscous damping.
 * Positions are unchanged. This avoids turning a contact correction into an
 * unchecked inward Verlet velocity on the next frame.
 */
__attribute__((export_name("contact_velocity"))) void contact_velocity(float retain,float friction){
 for(int i=0;i<nv;i++)if(parent[i]==i&&invMass[i]>0){
  V velocity=sub(x[i],previous[i]);Hit h=nearest(x[i]);float normal=dot(velocity,h.n);
  if(h.signedDistance<=margin+.0001f&&normal<0){
   V tangent=sub(velocity,mul(h.n,normal));float speed=root(dot(tangent,tangent));
   float factor=maxf(0,1-friction*absf(normal)/maxf(speed,1e-12f));velocity=mul(tangent,factor);
  }
  previous[i]=sub(x[i],mul(velocity,retain));
 }
 sync_aliases();
 for(int i=0;i<nv;i++)if(parent[i]!=i)contact[i]=contact[vertex(i)];
}

/* Source-body triangle feature contacts. Append after contact-extension.c.
 * Detection uses the actual body BVH and BOTH sets of segment/triangle
 * intersections, not an additional fixed set of cloth sample points.
 *
 * Each intersecting cloth face chooses ONE local separating support plane.
 * Candidates are the nearest-feature outward normal and +/- cloth normal.
 * Compare BOTH ends of the cloth-normal and nearest-feature axes.  A true
 * body-BVH first-exit ray prevents cheap local support planes from merely
 * sliding a cloth face along an arm into the next ring of body triangles.
 * A historical side takes precedence only if the ENTIRE previous cloth face
 * is geometrically feasible against the actual body, not just a local patch.
 * The support is over vertices of actual intersected body triangles, rather
 * than opposite entry/exit normals imposed simultaneously on the same edge.
 * This separates only the detected local region of a nonconvex body: repeat
 * true triangle gates, and never infer a whole-garment PASS from these counters.
 *
 * Per-round root path lengths are capped; previous follows actual stored
 * corrections by .8, consistently with the existing experimental contacts.
 * No persistent plane choice is hidden from saved x/previous/frame resumes.
 */
#define BFC_POINTS 64
#define BFC_FACES 512
typedef struct {double x,y,z;} BfcD;
typedef struct {double w[3];int edge;} BfcPoint;
typedef struct {
 int ids[3],count,stored,faceCount,storedFaces;
 V p[3];BfcPoint points[BFC_POINTS];int bodyFace[BFC_FACES];
 double sum[3],normalSupportMax,normalSupportMin;
 BfcD clothNormal;
} BfcRegion;
static double bfc_stats[16],bfc_last[32];
static float bfc_cap=.0005f;
static double bfc_spent[MAXV];
static BfcD bfc_d(V a){return (BfcD){a.x,a.y,a.z};}
static BfcD bfc_add(BfcD a,BfcD b){return (BfcD){a.x+b.x,a.y+b.y,a.z+b.z};}
static BfcD bfc_sub(BfcD a,BfcD b){return (BfcD){a.x-b.x,a.y-b.y,a.z-b.z};}
static BfcD bfc_mul(BfcD a,double s){return (BfcD){a.x*s,a.y*s,a.z*s};}
static double bfc_dot(BfcD a,BfcD b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static BfcD bfc_cross(BfcD a,BfcD b){return (BfcD){a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
static BfcD bfc_unit(BfcD a){double n=__builtin_sqrt(bfc_dot(a,a));return n>1e-20?bfc_mul(a,1/n):(BfcD){0,0,0};}
static BfcD bfc_body_point(int id){BfcD a=bfc_d(body[id]);a.x+=offsetX;return a;}
static BfcD bfc_weighted(BfcRegion *r,const double *w,int old){
 BfcD p={0,0,0};for(int k=0;k<3;k++)p=bfc_add(p,bfc_mul(bfc_d(old?previous[r->ids[k]]:x[r->ids[k]]),w[k]));return p;
}

/* Proper/transverse or boundary segment/triangle intersection in f64.
 * Coplanar surface contact is not classified as a transverse volume crossing.
 * body support/cloth contact margin is applied separately, after detection. */
static int bfc_segment_triangle(BfcD p,BfcD q,BfcD a,BfcD b,BfcD c,double *time,double bary[3]){
 BfcD u=bfc_sub(b,a),v=bfc_sub(c,a),n=bfc_cross(u,v);
 double n2=bfc_dot(n,n);if(n2<1e-30)return 0;
 double d0=bfc_dot(n,bfc_sub(p,a)),d1=bfc_dot(n,bfc_sub(q,a)),den=d0-d1;
 if((d0>0&&d1>0)||(d0<0&&d1<0)||den==0)return 0;
 double t=d0/den;if(t<0||t>1)return 0;
 BfcD hit=bfc_add(p,bfc_mul(bfc_sub(q,p),t)),h=bfc_sub(hit,a);
 double s=bfc_dot(bfc_cross(h,v),n)/n2,z=bfc_dot(bfc_cross(u,h),n)/n2;
 if(s< -1e-9||z< -1e-9||s+z>1+1e-9)return 0;
 double w[3]={1-s-z,s,z},sum=0;
 for(int k=0;k<3;k++){if(w[k]<0)w[k]=0;sum+=w[k];}
 for(int k=0;k<3;k++)bary[k]=w[k]/sum;
 *time=t;return 1;
}
static void bfc_add_hit(BfcRegion *r,const double *w,int edge){
 r->count++;for(int k=0;k<3;k++)r->sum[k]+=w[k];
 for(int i=0;i<r->stored;i++){
  double error=0;for(int k=0;k<3;k++){double d=r->points[i].w[k]-w[k];error+=d*d;}
  if(error<1e-18){if(edge>=0)r->points[i].edge=edge;return;}
 }
 if(r->stored<BFC_POINTS){BfcPoint *p=&r->points[r->stored++];for(int k=0;k<3;k++)p->w[k]=w[k];p->edge=edge;}
 else bfc_stats[6]++;
}
static int bfc_overlap(Node *n,const double lo[3],const double hi[3]){
 for(int k=0;k<3;k++)if(hi[k]<n->lo[k]||lo[k]>n->hi[k])return 0;return 1;
}
static int bfc_previous_feasible(BfcRegion *r){
 BfcD p[3];double lo[3]={1e300,1e300,1e300},hi[3]={-1e300,-1e300,-1e300};
 for(int k=0;k<3;k++){
  V previousPoint=previous[r->ids[k]];
  if(nearest(previousPoint).signedDistance< -1e-7f)return 0;
  p[k]=bfc_d(previousPoint);double a[3]={p[k].x-offsetX,p[k].y,p[k].z};
  for(int j=0;j<3;j++){if(a[j]<lo[j])lo[j]=a[j];if(a[j]>hi[j])hi[j]=a[j];}
 }
 int stack[64],sp=1;stack[0]=0;
 while(sp){
  Node *node=&nodes[stack[--sp]];if(!bfc_overlap(node,lo,hi))continue;
  if(!node->count){
   if(sp+2>64){bfc_stats[12]++;return 0;}
   stack[sp++]=node->left;stack[sp++]=node->right;continue;
  }
  for(int at=node->start;at<node->start+node->count;at++){
   int *ids=&bodyFaces[order[at]*3];
   BfcD b[3]={bfc_body_point(ids[0]),bfc_body_point(ids[1]),bfc_body_point(ids[2])};
   for(int k=0;k<3;k++){
    double t,w[3];
    if(bfc_segment_triangle(p[k],p[(k+1)%3],b[0],b[1],b[2],&t,w)&&t>1e-8&&t<1-1e-8)return 0;
    if(bfc_segment_triangle(b[k],b[(k+1)%3],p[0],p[1],p[2],&t,w)&&t>1e-8&&t<1-1e-8)return 0;
   }
  }
 }
 return 1;
}
static int bfc_ray_box(Node *node,BfcD origin,BfcD direction,double limit){
 double p[3]={origin.x-offsetX,origin.y,origin.z};
 double d[3]={direction.x,direction.y,direction.z},enter=0,leave=limit;
 for(int k=0;k<3;k++){
  if(__builtin_fabs(d[k])<1e-20){if(p[k]<node->lo[k]||p[k]>node->hi[k])return 0;continue;}
  double a=(node->lo[k]-p[k])/d[k],b=(node->hi[k]-p[k])/d[k];
  if(a>b){double temp=a;a=b;b=temp;}
  if(a>enter)enter=a;if(b<leave)leave=b;if(enter>leave)return 0;
 }
 return leave>0;
}
static double bfc_first_exit(BfcD origin,BfcD direction){
 double diagonal=0;
 for(int k=0;k<3;k++){double d=(double)nodes[0].hi[k]-nodes[0].lo[k];diagonal+=d*d;}
 double length=4*__builtin_sqrt(diagonal)+margin+1e-6,best=length;
 BfcD end=bfc_add(origin,bfc_mul(direction,length));int found=0,stack[64],sp=1;stack[0]=0;
 while(sp){
  Node *node=&nodes[stack[--sp]];if(!bfc_ray_box(node,origin,direction,best))continue;
  if(!node->count){
   if(sp+2>64){bfc_stats[12]++;return -1;}
   stack[sp++]=node->left;stack[sp++]=node->right;continue;
  }
  for(int at=node->start;at<node->start+node->count;at++){
   int *ids=&bodyFaces[order[at]*3];double time,w[3];
   if(bfc_segment_triangle(origin,end,bfc_body_point(ids[0]),bfc_body_point(ids[1]),bfc_body_point(ids[2]),&time,w)){
    double distance=time*length;
    if(distance>1e-8&&distance<best){best=distance;found=1;}
   }
  }
 }
 if(!found){bfc_stats[12]++;return -1;}
 return best;
}
static int bfc_gather(int t,BfcRegion *r){
 r->count=r->stored=r->faceCount=r->storedFaces=0;
 r->normalSupportMax=-1e300;r->normalSupportMin=1e300;
 double lo[3]={1e300,1e300,1e300},hi[3]={-1e300,-1e300,-1e300};
 for(int k=0;k<3;k++){
  r->sum[k]=0;r->ids[k]=vertex(faces[t*3+k]);r->p[k]=x[r->ids[k]];
  double a[3]={r->p[k].x-offsetX,r->p[k].y,r->p[k].z};
  for(int j=0;j<3;j++){if(a[j]<lo[j])lo[j]=a[j];if(a[j]>hi[j])hi[j]=a[j];}
 }
 r->clothNormal=bfc_unit(bfc_cross(bfc_sub(bfc_d(r->p[1]),bfc_d(r->p[0])),bfc_sub(bfc_d(r->p[2]),bfc_d(r->p[0]))));
 if(bfc_dot(r->clothNormal,r->clothNormal)<.5)return 0;
 for(int k=0;k<3;k++){lo[k]-=1e-8;hi[k]+=1e-8;}
 int stack[64],sp=1;stack[0]=0;bfc_stats[0]++;
 while(sp){
  Node *node=&nodes[stack[--sp]];if(!bfc_overlap(node,lo,hi))continue;
  if(!node->count){
   if(sp+2>64){bfc_stats[12]++;continue;}
   stack[sp++]=node->left;stack[sp++]=node->right;continue;
  }
  for(int at=node->start;at<node->start+node->count;at++){
   int face=order[at],*ids=&bodyFaces[face*3],hit=0;
   BfcD p[3]={bfc_body_point(ids[0]),bfc_body_point(ids[1]),bfc_body_point(ids[2])};
   for(int j=0;j<3;j++){
    double time,w[3];
    if(bfc_segment_triangle(bfc_d(r->p[j]),bfc_d(r->p[(j+1)%3]),p[0],p[1],p[2],&time,w)){
     double cw[3]={0,0,0};cw[j]=1-time;cw[(j+1)%3]=time;
     bfc_add_hit(r,cw,j);bfc_stats[2]++;hit=1;
    }
    if(bfc_segment_triangle(p[j],p[(j+1)%3],bfc_d(r->p[0]),bfc_d(r->p[1]),bfc_d(r->p[2]),&time,w)){
     bfc_add_hit(r,w,-1);bfc_stats[3]++;hit=1;
    }
   }
   if(hit){
    r->faceCount++;bfc_stats[1]++;
    if(r->storedFaces<BFC_FACES)r->bodyFace[r->storedFaces++]=face;
    for(int k=0;k<3;k++){
     double support=bfc_dot(r->clothNormal,p[k]);
     if(support>r->normalSupportMax)r->normalSupportMax=support;
     if(support<r->normalSupportMin)r->normalSupportMin=support;
    }
   }
  }
 }
 if(r->count)bfc_stats[4]++;
 return r->count>0;
}

static double bfc_support(BfcRegion *r,BfcD normal){
 double support=-1e300;
 for(int i=0;i<r->storedFaces;i++)for(int j=0;j<3;j++){
  double d=bfc_dot(normal,bfc_body_point(bodyFaces[r->bodyFace[i]*3+j]));if(d>support)support=d;
 }
 return support;
}
static Hit bfc_nearest(BfcD point){return nearest((V){(float)point.x,(float)point.y,(float)point.z});}
static void bfc_region_point(BfcRegion *r,double *w,Hit *hit){
 for(int k=0;k<3;k++)w[k]=r->sum[k]/r->count;
 *hit=bfc_nearest(bfc_weighted(r,w,0));
 /* Intersections, not fixed samples, supply the extra candidates.  Same-edge
  * entry/exit pairs reveal off-center penetration.  If the mean lies outside
  * a nonconvex body, pair chords may locate one actual inside region. */
 for(int i=0;i<r->stored;i++)for(int j=i+1;j<r->stored;j++){
  if(hit->signedDistance<0&&!(r->points[i].edge>=0&&r->points[i].edge==r->points[j].edge))continue;
  double candidate[3];for(int k=0;k<3;k++)candidate[k]=(r->points[i].w[k]+r->points[j].w[k])*.5;
  Hit h=bfc_nearest(bfc_weighted(r,candidate,0));
  if(h.signedDistance<hit->signedDistance){*hit=h;for(int k=0;k<3;k++)w[k]=candidate[k];}
 }
}
static int bfc_apply(BfcRegion *r,int face,const double *w,BfcD normal,double support,int kind){
 BfcD p=bfc_weighted(r,w,0);double gap=support-bfc_dot(normal,p),den=0;
 if(!(gap>0))return 0;
 for(int k=0;k<3;k++)den+=(double)invMass[r->ids[k]]*w[k]*w[k];
 if(!(den>0))return 0;
 double change=gap/den;
 for(int k=0;k<3;k++)if(invMass[r->ids[k]]>0&&w[k]>0){
  double remaining=(double)bfc_cap-bfc_spent[r->ids[k]];
  if(remaining<=0)return 0;
  double limit=remaining/((double)invMass[r->ids[k]]*w[k]);if(change>limit)change=limit;
 }
 if(!(change>0))return 0;
 V candidate[3];BfcD actual[3];double distance[3];int accepted=0;
 /* Theoretical limits alone can exceed the budget after f32 storage.  Test
  * every participating root's ACTUAL candidate and accumulated path before
  * atomically accepting the constraint; never clamp reported telemetry. */
 for(int attempt=0;attempt<32;attempt++,change*=.5){
  int finite=1,within=1,moving=0;
  for(int k=0;k<3;k++){
   int i=r->ids[k];BfcD before=bfc_d(x[i]);
   BfcD delta=bfc_mul(normal,(double)invMass[i]*w[k]*change);
   candidate[k]=(V){(float)(before.x+delta.x),(float)(before.y+delta.y),(float)(before.z+delta.z)};
   actual[k]=bfc_sub(bfc_d(candidate[k]),before);
   distance[k]=__builtin_sqrt(bfc_dot(actual[k],actual[k]));
   finite=finite&&__builtin_isfinite(distance[k]);
   within=within&&bfc_spent[i]+distance[k]<=(double)bfc_cap;
   moving=moving||distance[k]>0;
  }
  if(!moving)return 0;
  if(finite&&within){accepted=1;break;}
 }
 if(!accepted)return 0;
 int moved=0;
 for(int k=0;k<3;k++){
  int i=r->ids[k];if(!(invMass[i]>0&&w[k]>0))continue;
  BfcD delta=actual[k];x[i]=candidate[k];
  previous[i]=(V){(float)((double)previous[i].x+.8*delta.x),
                   (float)((double)previous[i].y+.8*delta.y),
                   (float)((double)previous[i].z+.8*delta.z)};
  bfc_spent[i]+=distance[k];
  if(bfc_spent[i]>bfc_stats[7])bfc_stats[7]=bfc_spent[i];
  contact[i]=1;moved=1;
 }
 if(moved){
  bfc_stats[5]++;bfc_last[0]=face;
  for(int k=0;k<3;k++){bfc_last[1+k]=w[k];bfc_last[14+k]=r->ids[k];}
  bfc_last[4]=p.x;bfc_last[5]=p.y;bfc_last[6]=p.z;
  bfc_last[7]=normal.x;bfc_last[8]=normal.y;bfc_last[9]=normal.z;
  bfc_last[10]=support;bfc_last[11]=den;bfc_last[12]=change;
  bfc_last[17]=kind;bfc_last[18]=gap;
 }
 return moved;
}
static void bfc_project_face(int face,BfcRegion *r){
 double w[3];Hit h;bfc_region_point(r,w,&h);
 if(-h.signedDistance>bfc_stats[10])bfc_stats[10]=-h.signedDistance;
 if(r->faceCount!=r->storedFaces){bfc_stats[6]++;return;}
 BfcD normal=bfc_unit(bfc_d(h.n));
 BfcD candidates[4]={r->clothNormal,bfc_mul(r->clothNormal,-1),normal,bfc_mul(normal,-1)};
 double support[4]={r->normalSupportMax+margin,-r->normalSupportMin+margin,
                    bfc_support(r,normal)+margin,bfc_support(r,bfc_mul(normal,-1))+margin};
 double rawSupport[4],exitDistance[4]={-1,-1,-1,-1};int count=4;
 BfcD region=bfc_weighted(r,w,0);
 BfcD rayOrigin=bfc_d((V){(float)region.x,(float)region.y,(float)region.z});
 for(int j=0;j<count;j++){
  rawSupport[j]=support[j];
  if(h.signedDistance< -1e-6f){
   exitDistance[j]=bfc_first_exit(rayOrigin,candidates[j]);
   if(exitDistance[j]<0)return;
   double actualExitPlane=bfc_dot(candidates[j],rayOrigin)+exitDistance[j]+margin;
   if(actualExitPlane>support[j])support[j]=actualExitPlane;
  }
 }
 int previousFeasible=bfc_previous_feasible(r);
 int chosen=-1,bestFeasible=0;double best=1e300,bestHistory=-1e300;
 for(int j=0;j<count;j++){
  if(bfc_dot(candidates[j],candidates[j])<.5)continue;
  double minimum=1e300;
  for(int k=0;k<3;k++){double value=bfc_dot(candidates[j],bfc_d(x[r->ids[k]]));if(value<minimum)minimum=value;}
  double previousMinimum=1e300;
  for(int k=0;k<3;k++){
   double value=bfc_dot(candidates[j],bfc_d(previous[r->ids[k]]));
   if(value<previousMinimum)previousMinimum=value;
  }
  double needed=support[j]-minimum,history=previousMinimum-(support[j]-margin);
  int feasible=previousFeasible&&history>= -1e-7;
  /* Preserve a provably previously feasible side even when exiting through
   * the opposite side would be cheaper in the already penetrated geometry.
   * This local side test is useful, but is not a full swept CCD guarantee. */
  if(chosen<0||(feasible&&!bestFeasible)||(feasible==bestFeasible&&
     (needed<best-1e-8||(__builtin_fabs(needed-best)<=1e-8&&history>bestHistory)))){
   chosen=j;best=needed;bestHistory=history;bestFeasible=feasible;
  }
 }
 if(chosen<0)return;
 if(bestFeasible)bfc_stats[15]++;
 if(chosen>=2)bfc_stats[8]++;else bfc_stats[9]++;
 if(best>bfc_stats[11])bfc_stats[11]=best;
 BfcD n=candidates[chosen];double plane=support[chosen];
 double projectedBefore=bfc_stats[5];bfc_apply(r,face,w,n,plane,0);
 /* One-hot barycentrics impose the same region support plane on the rest of
  * this participating face.  Detection still comes only from actual crossings.
  * This avoids indefinitely sliding an interior contact within an unchanged
  * large triangle while its corners continue spanning the body. */
 for(int k=0;k<3;k++){double one[3]={0,0,0};one[k]=1;bfc_apply(r,face,one,n,plane,1);}
 if(bfc_stats[5]>projectedBefore){
  bfc_last[19]=bfc_dot(n,r->clothNormal);bfc_last[20]=best;
  bfc_last[21]=chosen;bfc_last[22]=bestFeasible;bfc_last[23]=h.signedDistance;
  bfc_last[24]=previousFeasible;bfc_last[25]=exitDistance[chosen];
  bfc_last[26]=rayOrigin.x;bfc_last[27]=rayOrigin.y;bfc_last[28]=rayOrigin.z;
  bfc_last[29]=rawSupport[chosen];bfc_last[30]=support[chosen]-rawSupport[chosen];bfc_last[31]=count;
 }
}
static void bfc_reset_stats(void){for(int k=0;k<16;k++)bfc_stats[k]=0;bfc_stats[13]=margin;bfc_stats[14]=bfc_cap;}
__attribute__((export_name("set_body_feature_cap")))
void set_body_feature_cap(float cap){if(cap>0)bfc_cap=cap;}
__attribute__((export_name("body_feature_contact_scan")))
int body_feature_contact_scan(void){
 bfc_reset_stats();BfcRegion region;
 for(int t=0;t<nt;t++)bfc_gather(t,&region);
 return (int)bfc_stats[4];
}
__attribute__((export_name("project_body_feature_contacts")))
void project_body_feature_contacts(int rounds){
 bfc_reset_stats();BfcRegion region;
 for(int it=0;it<rounds;it++){
  for(int i=0;i<nv;i++)bfc_spent[i]=0;
  for(int j=0;j<nt;j++){
   int t=(frame+it)%2?nt-1-j:j;
   if(bfc_gather(t,&region))bfc_project_face(t,&region);
  }
 }
 sync_aliases();
}
__attribute__((export_name("body_feature_stats_ptr")))
int body_feature_stats_ptr(void){return (int)bfc_stats;}
__attribute__((export_name("body_feature_last_contact_ptr")))
int body_feature_last_contact_ptr(void){return (int)bfc_last;}

/* Signed dihedral XPBD. Material rest angles are flat; no permanent crease law.
 * The derivative is independently checked by finite differences.
 */
#define MAXH 16384
typedef struct {int a,b,c,d;float weight,lambda;} Hinge;
static Hinge hinges[MAXH];static int nh;
static float hingeStiffness=.000001f,hingeLimit=2.0943951023931953f,hingeMoveCap=.001f;
__attribute__((export_name("configure_bending"))) void configure_bending(float stiffness,float limit,float move){hingeStiffness=stiffness;hingeLimit=limit;hingeMoveCap=move;}
static void reset_hinge_lambdas(){for(int i=0;i<nh;i++)hinges[i].lambda=0;}
static V cross_h(V a,V b){return (V){a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
static float small_atan_h(float x){float z=x*x,p=1.f/17;for(int i=7;i>=0;i--)p=(i%2?-1.f:1.f)/(2*i+1)+z*p;return x*p;}
static float atan_h(float x){
 if(x>1)return 1.5707963267948966f-atan_h(1/x);
 if(x>.41421356237f)return .7853981633974483f+small_atan_h((x-1)/(x+1));
 return small_atan_h(x);
}
static float angle_h(float y,float z){float a=atan_h(absf(y)/maxf(absf(z),1e-20f));if(z<0)a=3.141592653589793f-a;return y<0?-a:a;}
static void solve_hinges(float dt){
 for(int j=0;j<nh;j++){
  Hinge *h=&hinges[j];int ids[4]={vertex(h->a),vertex(h->b),vertex(h->c),vertex(h->d)};
  V e=sub(x[ids[1]],x[ids[0]]),u=sub(x[ids[2]],x[ids[0]]),v=sub(x[ids[3]],x[ids[0]]);
  V n=cross_h(e,u),m=cross_h(v,e);float l2=dot(e,e),n2=dot(n,n),m2=dot(m,m);
  if(minf(l2,minf(n2,m2))<1e-20f)continue;
  float len=root(l2);V nn=mul(n,1/root(n2)),mm=mul(m,1/root(m2));
  float angle=angle_h(dot(cross_h(nn,mm),mul(e,1/len)),dot(nn,mm));
  V q[4];q[2]=mul(n,-len/n2);q[3]=mul(m,-len/m2);
  float a=dot(u,e)/l2,b=dot(v,e)/l2;
  q[0]=add(mul(q[2],a-1),mul(q[3],b-1));q[1]=add(mul(q[2],-a),mul(q[3],-b));
  float den=0;for(int k=0;k<4;k++)den+=invMass[ids[k]]*dot(q[k],q[k]);
  float alpha=1/(hingeStiffness*h->weight*dt*dt),delta;
  if(absf(angle)>hingeLimit){
   float target=angle>0?hingeLimit:-hingeLimit;
   delta=-(angle-target)/maxf(den,1e-20f);h->lambda=0;
  }else delta=(-angle-alpha*h->lambda)/maxf(den+alpha,1e-20f);
  float largest=0;for(int k=0;k<4;k++)largest=maxf(largest,root(dot(q[k],q[k]))*invMass[ids[k]]*absf(delta));
  if(largest>hingeMoveCap)delta*=hingeMoveCap/largest;
  h->lambda+=delta;
  for(int k=0;k<4;k++)x[ids[k]]=add(x[ids[k]],mul(q[k],invMass[ids[k]]*delta));
 }
}
__attribute__((export_name("add_hinge"))) void add_hinge(int a,int b,int c,int d,float weight){if(nh<MAXH)hinges[nh++]=(Hinge){a,b,c,d,weight,0};}
__attribute__((export_name("hinge_count"))) int hinge_count(){return nh;}
__attribute__((export_name("hinge_probe"))) void hinge_probe(int j){
 Hinge h=hinges[j];V e=sub(x[vertex(h.b)],x[vertex(h.a)]),n=unit(cross_h(e,sub(x[vertex(h.c)],x[vertex(h.a)]))),m=unit(cross_h(sub(x[vertex(h.d)],x[vertex(h.a)]),e));
 probe[0]=angle_h(dot(cross_h(n,m),unit(e)),dot(n,m));
}
