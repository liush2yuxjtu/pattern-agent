/** Mass-weighted rigid shape-matching closure. Its reference stores only a
 * local shape: translation and rotation remain free; no world/body anchors.
 * This is an explicit stiff-belt approximation, not a calibrated soft waistband.
 */
export class WaistRing {
 constructor(positions,inverseMass,count,perimeter){
  if(count<3||Array.from(inverseMass).slice(0,count).some(x=>!Number.isFinite(x)||x<=0))throw new Error('Waist ring requires finite positive particle masses; no pins');
  this.count=count;this.mass=Array.from({length:count},(_,i)=>1/inverseMass[i]);this.total=this.mass.reduce((a,b)=>a+b,0);this.rest=new Float64Array(count*3);this.weightedRest=new Float64Array(count*3);this.covariance=new Float64Array(9);
  const center=this.center(positions);let length=0;for(let i=0;i<count;i++){const j=(i+1)%count;length+=Math.hypot(...[0,1,2].map(k=>positions[i*3+k]-positions[j*3+k]));}
  for(let i=0;i<count;i++)for(let k=0;k<3;k++){
   const j=i*3+k;
   this.rest[j]=(positions[j]-center[k])*perimeter/length;
   this.weightedRest[j]=this.mass[i]*this.rest[j];
  }
 }
 center(p){const c=[0,0,0];for(let i=0;i<this.count;i++)for(let k=0;k<3;k++)c[k]+=this.mass[i]*p[i*3+k]/this.total;return c;}
 solve(p){
  const center=this.center(p),s=this.covariance,weighted=this.weightedRest;
  s.fill(0);
  for(let i=0;i<this.count*3;i+=3){
   const dx=p[i]-center[0],dy=p[i+1]-center[1],dz=p[i+2]-center[2];
   for(let axis=0;axis<3;axis++){
    const m=weighted[i+axis], j=axis*3;
    s[j]+=m*dx;s[j+1]+=m*dy;s[j+2]+=m*dz;
   }
  }
  const [xx,xy,xz,yx,yy,yz,zx,zy,zz]=s;
  const a=[xx+yy+zz,yz-zy,zx-xz,xy-yx,yz-zy,xx-yy-zz,xy+yx,xz+zx,zx-xz,xy+yx,-xx+yy-zz,yz+zy,xy-yx,xz+zx,yz+zy,-xx-yy+zz],v=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
  for(let sweep=0;sweep<12;sweep++){
   let unchanged=true;
   for(let j=0;j<4;j++)for(let k=j+1;k<4;k++){
   const off=a[j*4+k];if(Math.abs(off)<1e-20)continue;unchanged=false;const tau=(a[k*4+k]-a[j*4+j])/(2*off),t=(tau>=0?1:-1)/(Math.abs(tau)+Math.sqrt(1+tau*tau)),c=1/Math.sqrt(1+t*t),sn=t*c;
   a[j*4+j]-=t*off;a[k*4+k]+=t*off;a[j*4+k]=a[k*4+j]=0;
   for(let z=0;z<4;z++){if(z!==j&&z!==k){const x=a[z*4+j],y=a[z*4+k];a[z*4+j]=a[j*4+z]=c*x-sn*y;a[z*4+k]=a[k*4+z]=sn*x+c*y;}const x=v[z*4+j],y=v[z*4+k];v[z*4+j]=c*x-sn*y;v[z*4+k]=sn*x+c*y;}
   }
   if(unchanged)break;
  }
  let best=0;for(let j=1;j<4;j++)if(a[j*4+j]>a[best*4+best])best=j;
  const [w,x,y,z]=[0,1,2,3].map(i=>v[i*4+best]),r=[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)];
  for(let i=0;i<this.count;i++)for(let k=0;k<3;k++)p[i*3+k]=center[k]+r[k*3]*this.rest[i*3]+r[k*3+1]*this.rest[i*3+1]+r[k*3+2]*this.rest[i*3+2];
 }
}
