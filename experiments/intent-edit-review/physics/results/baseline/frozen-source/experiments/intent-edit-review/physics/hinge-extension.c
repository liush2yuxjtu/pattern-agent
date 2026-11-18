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
