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
