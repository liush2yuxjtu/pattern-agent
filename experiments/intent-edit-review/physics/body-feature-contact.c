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
