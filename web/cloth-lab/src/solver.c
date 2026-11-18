/* Pattern Agent cloth laboratory. MIT. SI units throughout.
 * Orthotropic StVK membrane energy solved as three coupled XPBD constraints.
 * Body collisions use closest points on the actual MakeHuman triangle BVH.
 * Bending is an explicit distance approximation, not a calibrated shell law.
 */
#define MAXV 4096
#define MAXT 8192
#define MAXS 256
#define MAXB 8192
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
static V closest(V p,V a,V b,V c,float *u,float *v){
 V ab=sub(b,a),ac=sub(c,a),ap=sub(p,a);float d1=dot(ab,ap),d2=dot(ac,ap);
 if(d1<=0&&d2<=0){*u=0;*v=0;return a;}
 V bp=sub(p,b);float d3=dot(ab,bp),d4=dot(ac,bp);if(d3>=0&&d4<=d3){*u=1;*v=0;return b;}
 float vc=d1*d4-d3*d2;if(vc<=0&&d1>=0&&d3<=0){*u=d1/(d1-d3);*v=0;return add(a,mul(ab,*u));}
 V cp=sub(p,c);float d5=dot(ab,cp),d6=dot(ac,cp);if(d6>=0&&d5<=d6){*u=0;*v=1;return c;}
 float vb=d5*d2-d1*d6;if(vb<=0&&d2>=0&&d6<=0){*u=0;*v=d2/(d2-d6);return add(a,mul(ac,*v));}
 float va=d3*d6-d5*d4;if(va<=0&&(d4-d3)>=0&&(d5-d6)>=0){float w=(d4-d3)/((d4-d3)+(d5-d6));*u=1-w;*v=w;return add(b,mul(sub(c,b),w));}
 float den=1/(va+vb+vc);*u=vb*den;*v=vc*den;return add(a,add(mul(ab,*u),mul(ac,*v)));
}
typedef struct {V q,n;float signedDistance;} Hit;
static Hit nearest(V point){
 V p=point;p.x-=offsetX;float best=1e20f,bu=0,bv=0;int bestFace=0,stack[64],sp=1;stack[0]=0;V q={0,0,0};
 while(sp){int ni=stack[--sp];Node n=nodes[ni];if(boxDistance(p,n)>best)continue;
  if(n.count){for(int k=n.start;k<n.start+n.count;k++){int f=order[k],ia=bodyFaces[3*f],ib=bodyFaces[3*f+1],ic=bodyFaces[3*f+2];float u,v;V z=closest(p,body[ia],body[ib],body[ic],&u,&v);V d=sub(p,z);float ds=dot(d,d);if(ds<best){best=ds;q=z;bestFace=f;bu=u;bv=v;}}}
  else{float dl=boxDistance(p,nodes[n.left]),dr=boxDistance(p,nodes[n.right]);if(dl<dr){if(dr<=best)stack[sp++]=n.right;if(dl<=best)stack[sp++]=n.left;}else{if(dl<=best)stack[sp++]=n.left;if(dr<=best)stack[sp++]=n.right;}}
 }
 int ia=bodyFaces[3*bestFace],ib=bodyFaces[3*bestFace+1],ic=bodyFaces[3*bestFace+2];V normal=unit(add(mul(bodyNormals[ia],1-bu-bv),add(mul(bodyNormals[ib],bu),mul(bodyNormals[ic],bv))));
 float sd=root(best);if(dot(sub(p,q),normal)<0)sd=-sd;q.x+=offsetX;
 return (Hit){q,normal,sd};
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
static void solveMembrane(int t,int component,float dt){
 int i0=vertex(faces[t*3]),i1=vertex(faces[t*3+1]),i2=vertex(faces[t*3+2]);float a=inverseDm[4*t],b=inverseDm[4*t+1],c=inverseDm[4*t+2],d=inverseDm[4*t+3];
 V e1=sub(x[i1],x[i0]),e2=sub(x[i2],x[i0]),u=add(mul(e1,a),mul(e2,c)),v=add(mul(e1,b),mul(e2,d)),g1,g2;float C,stiff,q11,q22,q12;moduli(&q11,&q22,&q12);
 if(component==0){float r=q12/q11;C=.5f*(dot(u,u)-1)+r*.5f*(dot(v,v)-1);g1=add(mul(u,a),mul(v,r*b));g2=add(mul(u,c),mul(v,r*d));stiff=q11;}
 else if(component==1){C=.5f*(dot(v,v)-1);g1=mul(v,b);g2=mul(v,d);stiff=q22-q12*q12/q11;}
 else{C=dot(u,v);g1=add(mul(v,a),mul(u,b));g2=add(mul(v,c),mul(u,d));stiff=G;}
 V g0=mul(add(g1,g2),-1);float alpha=1/(stiff*thickness*area[t]*dt*dt),den=invMass[i0]*dot(g0,g0)+invMass[i1]*dot(g1,g1)+invMass[i2]*dot(g2,g2)+alpha;
 float *l=&lambda[t*3+component],dl=(-C-alpha*(*l))/maxf(den,1e-12f);*l+=dl;
 x[i0]=add(x[i0],mul(g0,dl*invMass[i0]));x[i1]=add(x[i1],mul(g1,dl*invMass[i1]));x[i2]=add(x[i2],mul(g2,dl*invMass[i2]));
}
static void solveDistance(int a,int b,float rest,float alpha){a=vertex(a);b=vertex(b);V e=sub(x[b],x[a]);float len=root(dot(e,e)),sum=invMass[a]+invMass[b];if(sum<1e-12f||len<1e-10f)return;float r=(len-rest)/(len*(sum+alpha));x[a]=add(x[a],mul(e,r*invMass[a]));x[b]=sub(x[b],mul(e,r*invMass[b]));}
static int canSkip(V point,int key){V local=point;local.x-=offsetX;V delta=sub(local,cachePoint[key]);float safe=cacheDistance[key]-margin;return cacheEnabled&&safe>0&&dot(delta,delta)<safe*safe;}
static Hit cachedNearest(V point,int key){Hit h=nearest(point);cachePoint[key]=point;cachePoint[key].x-=offsetX;cacheDistance[key]=h.signedDistance;return h;}
static void collideVertex(int i){if(invMass[i]==0||canSkip(x[i],i))return;Hit h=cachedNearest(x[i],i);if(h.signedDistance<margin){x[i]=add(h.q,mul(h.n,margin));contact[i]=1;}}
static void collideCentroid(int t){int a=vertex(faces[t*3]),b=vertex(faces[t*3+1]),c=vertex(faces[t*3+2]);V p=mul(add(x[a],add(x[b],x[c])),1.f/3);if(canSkip(p,MAXV+t))return;Hit h=cachedNearest(p,MAXV+t);if(h.signedDistance>=margin)return;float sum=invMass[a]+invMass[b]+invMass[c];if(sum<1e-12f)return;V delta=sub(add(h.q,mul(h.n,margin)),p);x[a]=add(x[a],mul(delta,3*invMass[a]/sum));x[b]=add(x[b],mul(delta,3*invMass[b]/sum));x[c]=add(x[c],mul(delta,3*invMass[c]/sum));}
__attribute__((export_name("position_ptr"))) int position_ptr(){return (int)x;}__attribute__((export_name("previous_ptr"))) int previous_ptr(){return (int)previous;}__attribute__((export_name("pin_ptr"))) int pin_ptr(){return (int)pins;}__attribute__((export_name("uv_ptr"))) int uv_ptr(){return (int)uv;}__attribute__((export_name("face_ptr"))) int face_ptr(){return (int)faces;}__attribute__((export_name("invmass_ptr"))) int invmass_ptr(){return (int)invMass;}__attribute__((export_name("field_ptr"))) int field_ptr(){return (int)fields;}__attribute__((export_name("contacts_ptr"))) int contacts_ptr(){return (int)contact;}__attribute__((export_name("body_distance_ptr"))) int body_distance_ptr(){return (int)distanceBody;}__attribute__((export_name("stats_ptr"))) int stats_ptr(){return (int)stats;}__attribute__((export_name("probe_ptr"))) int probe_ptr(){return (int)probe;}
__attribute__((export_name("body_ptr"))) int body_ptr(){return (int)body;}__attribute__((export_name("body_normal_ptr"))) int body_normal_ptr(){return (int)bodyNormals;}__attribute__((export_name("body_face_ptr"))) int body_face_ptr(){return (int)bodyFaces;}__attribute__((export_name("body_order_ptr"))) int body_order_ptr(){return (int)order;}__attribute__((export_name("body_node_ptr"))) int body_node_ptr(){return (int)nodes;}
__attribute__((export_name("configure_body"))) void configure_body(int v,int f,int n){bodyNv=v;bodyNf=f;nodeCount=n;}
__attribute__((export_name("configure_material"))) void configure_material(float eu,float ev,float shear,float poisson,float thick,float rho){Eu=eu;Ev=ev;G=shear;nu=poisson;thickness=thick;density=rho;}
__attribute__((export_name("configure_cloth"))) void configure_cloth(int v,int f){nv=v;nt=f;ns=0;nb=0;for(int i=0;i<MAXV+MAXT;i++)cacheDistance[i]=-1e6f;frame=0;simTime=0;offsetX=0;for(int i=0;i<nv;i++){parent[i]=i;previous[i]=x[i];pins[i]=x[i];contact[i]=0;invMass[i]=0;}
 for(int t=0;t<nt;t++){int i=faces[t*3],j=faces[t*3+1],k=faces[t*3+2];float a=uv[2*j]-uv[2*i],b=uv[2*k]-uv[2*i],c=uv[2*j+1]-uv[2*i+1],d=uv[2*k+1]-uv[2*i+1],det=a*d-b*c;inverseDm[4*t]=d/det;inverseDm[4*t+1]=-b/det;inverseDm[4*t+2]=-c/det;inverseDm[4*t+3]=a/det;area[t]=absf(det)*.5f;float mass=area[t]*density/3;invMass[i]+=mass;invMass[j]+=mass;invMass[k]+=mass;}
 for(int i=0;i<nv;i++)invMass[i]=1/maxf(invMass[i],1e-9f);
}
__attribute__((export_name("set_pin"))) void set_pin(int i){invMass[i]=0;}
__attribute__((export_name("add_seam"))) void add_seam(int a,int b,int active){if(ns<MAXS)seams[ns++]=(Seam){a,b,active};}
__attribute__((export_name("add_bend"))) void add_bend(int a,int b,float rest){if(nb<MAXB)bends[nb++]=(Bend){a,b,rest};}
__attribute__((export_name("set_collision"))) void set_collision(int enabled){collisionEnabled=enabled;}
__attribute__((export_name("set_body_offset"))) void set_body_offset(float xoff){float delta=xoff-offsetX;offsetX=xoff;for(int i=0;i<nv;i++)if(parent[i]==i&&invMass[i]==0){pins[i].x+=delta;x[i]=pins[i];previous[i]=x[i];}sync_aliases();}
__attribute__((export_name("inject_vertex"))) void inject_vertex(int i,float px,float py,float pz){i=vertex(i);x[i]=(V){px,py,pz};previous[i]=x[i];sync_aliases();}
__attribute__((export_name("material_probe"))) void material_probe(float ux,float uy,float uz,float vx,float vy,float vz){material((V){ux,uy,uz},(V){vx,vy,vz},probe);}
__attribute__((export_name("collision_probe"))) void collision_probe(float px,float py,float pz){Hit h=nearest((V){px,py,pz});probe[0]=h.signedDistance;probe[1]=h.q.x;probe[2]=h.q.y;probe[3]=h.q.z;probe[4]=h.n.x;probe[5]=h.n.y;probe[6]=h.n.z;}
__attribute__((export_name("step"))) void step(int count,float wind){const float dt=1.f/120;for(int s=0;s<count;s++){
 for(int i=0;i<nv;i++){contact[i]=0;if(parent[i]!=i)continue;if(invMass[i]==0){x[i]=pins[i];previous[i]=x[i];continue;}V velocity=mul(sub(x[i],previous[i]),.993f);float speed=root(dot(velocity,velocity));if(speed>.025f)velocity=mul(velocity,.025f/speed);previous[i]=x[i];x[i]=add(x[i],velocity);x[i].y-=9.81f*dt*dt;x[i].z+=wind*dt*dt;}
 for(int i=0;i<nt*3;i++)lambda[i]=0;
 for(int it=0;it<24;it++){
  for(int j=0;j<nt;j++){int t=it%2?nt-1-j:j;for(int c=0;c<3;c++)solveMembrane(t,c,dt);}
  for(int j=0;j<nb;j++)solveDistance(bends[j].a,bends[j].b,bends[j].rest,1/(.04f*dt*dt));
  for(int j=0;j<ns;j++)if(seams[j].active)solveDistance(seams[j].a,seams[j].b,0,0);
  if(collisionEnabled){for(int i=0;i<nv;i++)collideVertex(i);if(it>=22)for(int t=0;t<nt;t++)collideCentroid(t);}
 }
 /* Final contact/seam projection, alternating to keep both residuals visible. */
 for(int it=0;it<3;it++){for(int j=0;j<ns;j++)if(seams[j].active)solveDistance(seams[j].a,seams[j].b,0,0);if(collisionEnabled)for(int i=0;i<nv;i++)collideVertex(i);}
 sync_aliases();frame++;simTime+=dt;
}}
__attribute__((export_name("analyze"))) void analyze(){float maxGap=0,maxPen=0,minClear=1e6f,maxStrain=-1,maxStress=0,contacts=0,energy=0;int finite=1;for(int t=0;t<nt;t++){int i0=faces[t*3],i1=faces[t*3+1],i2=faces[t*3+2];V e1=sub(x[i1],x[i0]),e2=sub(x[i2],x[i0]);V u=add(mul(e1,inverseDm[4*t]),mul(e2,inverseDm[4*t+2])),v=add(mul(e1,inverseDm[4*t+1]),mul(e2,inverseDm[4*t+3]));material(u,v,fields[t]);maxStrain=maxf(maxStrain,fields[t][0]);maxStress=maxf(maxStress,fields[t][3]);float q11,q22,q12;moduli(&q11,&q22,&q12);float a=fields[t][5],b=fields[t][6],c=fields[t][7];energy+=(.5f*q11*a*a+q12*a*b+.5f*q22*b*b+2*G*c*c)*area[t]*thickness;}
 for(int j=0;j<ns;j++)if(seams[j].active){V e=sub(x[seams[j].a],x[seams[j].b]);maxGap=maxf(maxGap,root(dot(e,e)));}
 for(int i=0;i<nv;i++){Hit h=nearest(x[i]);distanceBody[i]=h.signedDistance;minClear=minf(minClear,h.signedDistance);maxPen=maxf(maxPen,-h.signedDistance);contacts+=contact[i]>0;finite=finite&&__builtin_isfinite(x[i].x)&&__builtin_isfinite(x[i].y)&&__builtin_isfinite(x[i].z);}
 stats[0]=frame;stats[1]=simTime;stats[2]=maxGap;stats[3]=maxPen;stats[4]=minClear;stats[5]=maxStrain;stats[6]=maxStress;stats[7]=contacts;stats[8]=finite;stats[9]=energy;stats[10]=collisionEnabled;
}

__attribute__((export_name("set_clock"))) void set_clock(int n,float t){frame=n;simTime=t;}
/* Read-only clock access lets recording capture every substep without running analysis. */
__attribute__((export_name("get_frame"))) int get_frame(){return frame;}
__attribute__((export_name("get_time"))) float get_time(){return simTime;}

/* Ideal sewn joints share positional degrees of freedom. Material coordinates
 * remain per-panel, so unequal lengths and reversed sewing remain detectable. */
__attribute__((export_name("finalize_seams"))) void finalize_seams(){
 for(int j=0;j<ns;j++)if(seams[j].active){int a=vertex(seams[j].a),b=vertex(seams[j].b);if(a!=b)parent[b]=a;}
 float mass[MAXV];int fixed[MAXV];for(int i=0;i<nv;i++){mass[i]=0;fixed[i]=0;parent[i]=vertex(i);}
 for(int i=0;i<nv;i++){if(invMass[i]==0)fixed[parent[i]]=1;else mass[parent[i]]+=1/invMass[i];}
 for(int i=0;i<nv;i++){if(parent[i]!=i)invMass[i]=0;else invMass[i]=fixed[i]?0:1/maxf(mass[i],1e-9f);}
 sync_aliases();
}

__attribute__((export_name("set_cache"))) void set_cache(int enabled){cacheEnabled=enabled;}
