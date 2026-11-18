const EPS = 1e-10;

export class MeshBodyCollider {
  constructor({positions, triangles}) {
    if (!positions || positions.length % 3 || !triangles || triangles.length % 3) throw new Error('Body mesh must contain xyz vertices and triangle indices');
    this.positions = positions instanceof Float32Array ? positions : new Float32Array(positions);
    this.triangles = triangles instanceof Uint32Array ? triangles : new Uint32Array(triangles);
    if (!this.positions.length || !this.triangles.length || !this.positions.every(Number.isFinite)) throw new Error('Body mesh must be nonempty and finite');
    if (!this.triangles.every(i => i < this.positions.length / 3)) throw new Error('Body triangle index is out of range');
    this.triangleCount = this.triangles.length / 3;
    this._order = Array.from({length: this.triangleCount}, (_, i) => i);
    this._bounds = new Float64Array(this.triangleCount * 6);
    this._centers = new Float64Array(this.triangleCount * 3);
    this._nodes = [];
    this._stack = [];
    this._hits = [];
    this._output = new Float64Array(3);
    this._result = {x:0,y:0,z:0,nx:0,ny:1,nz:0,distance:Infinity,signedDistance:Infinity,inside:false,triangle:-1};
    let volume = 0;
    for (let t=0;t<this.triangleCount;t++) {
      const a=this.triangles[t*3]*3,b=this.triangles[t*3+1]*3,c=this.triangles[t*3+2]*3,p=this.positions;
      for(let k=0;k<3;k++) {
        this._bounds[t*6+k]=Math.min(p[a+k],p[b+k],p[c+k]);
        this._bounds[t*6+k+3]=Math.max(p[a+k],p[b+k],p[c+k]);
        this._centers[t*3+k]=(p[a+k]+p[b+k]+p[c+k])/3;
      }
      volume += p[a]*(p[b+1]*p[c+2]-p[b+2]*p[c+1])+p[a+1]*(p[b+2]*p[c]-p[b]*p[c+2])+p[a+2]*(p[b]*p[c+1]-p[b+1]*p[c]);
    }
    this.orientation = volume < 0 ? -1 : 1;
    this.signedVolume = volume/6;
    this._root = this._build(0, this.triangleCount);
    this.bounds = this._nodes[this._root].bounds.slice();
  }

  _build(start,end) {
    const bounds=[Infinity,Infinity,Infinity,-Infinity,-Infinity,-Infinity];
    const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
    for(let n=start;n<end;n++) {
      const t=this._order[n];
      for(let k=0;k<3;k++) {
        bounds[k]=Math.min(bounds[k],this._bounds[t*6+k]);bounds[k+3]=Math.max(bounds[k+3],this._bounds[t*6+k+3]);
        lo[k]=Math.min(lo[k],this._centers[t*3+k]);hi[k]=Math.max(hi[k],this._centers[t*3+k]);
      }
    }
    const id=this._nodes.length,node={bounds,start,end,left:-1,right:-1};this._nodes.push(node);
    if(end-start>8) {
      let axis=0;for(let k=1;k<3;k++)if(hi[k]-lo[k]>hi[axis]-lo[axis])axis=k;
      const sorted=this._order.slice(start,end).sort((a,b)=>this._centers[a*3+axis]-this._centers[b*3+axis]);
      for(let i=0;i<sorted.length;i++)this._order[start+i]=sorted[i];
      const middle=(start+end)>>1;node.left=this._build(start,middle);node.right=this._build(middle,end);
    }
    return id;
  }

  _boxDistance(bounds,x,y,z) {
    const dx=Math.max(bounds[0]-x,0,x-bounds[3]),dy=Math.max(bounds[1]-y,0,y-bounds[4]),dz=Math.max(bounds[2]-z,0,z-bounds[5]);
    return dx*dx+dy*dy+dz*dz;
  }

  _trianglePoint(t,x,y,z,best) {
    const p=this.positions,ia=this.triangles[t*3]*3,ib=this.triangles[t*3+1]*3,ic=this.triangles[t*3+2]*3;
    const ax=p[ia],ay=p[ia+1],az=p[ia+2],bx=p[ib],by=p[ib+1],bz=p[ib+2],cx=p[ic],cy=p[ic+1],cz=p[ic+2];
    const abx=bx-ax,aby=by-ay,abz=bz-az,acx=cx-ax,acy=cy-ay,acz=cz-az;
    const apx=x-ax,apy=y-ay,apz=z-az,d1=abx*apx+aby*apy+abz*apz,d2=acx*apx+acy*apy+acz*apz;
    let qx,qy,qz;
    if(d1<=0&&d2<=0){qx=ax;qy=ay;qz=az;}
    else {
      const bpx=x-bx,bpy=y-by,bpz=z-bz,d3=abx*bpx+aby*bpy+abz*bpz,d4=acx*bpx+acy*bpy+acz*bpz;
      if(d3>=0&&d4<=d3){qx=bx;qy=by;qz=bz;}
      else {
        const vc=d1*d4-d3*d2;
        if(vc<=0&&d1>=0&&d3<=0){const v=d1/(d1-d3);qx=ax+v*abx;qy=ay+v*aby;qz=az+v*abz;}
        else {
          const cpx=x-cx,cpy=y-cy,cpz=z-cz,d5=abx*cpx+aby*cpy+abz*cpz,d6=acx*cpx+acy*cpy+acz*cpz;
          if(d6>=0&&d5<=d6){qx=cx;qy=cy;qz=cz;}
          else {
            const vb=d5*d2-d1*d6;
            if(vb<=0&&d2>=0&&d6<=0){const w=d2/(d2-d6);qx=ax+w*acx;qy=ay+w*acy;qz=az+w*acz;}
            else {
              const va=d3*d6-d5*d4;
              if(va<=0&&(d4-d3)>=0&&(d5-d6)>=0){const w=(d4-d3)/((d4-d3)+(d5-d6));qx=bx+w*(cx-bx);qy=by+w*(cy-by);qz=bz+w*(cz-bz);}
              else {const denom=1/(va+vb+vc),v=vb*denom,w=vc*denom;qx=ax+abx*v+acx*w;qy=ay+aby*v+acy*w;qz=az+abz*v+acz*w;}
            }
          }
        }
      }
    }
    const d=(x-qx)**2+(y-qy)**2+(z-qz)**2;
    if(d<best) {
      const nx=aby*acz-abz*acy,ny=abz*acx-abx*acz,nz=abx*acy-aby*acx,length=Math.hypot(nx,ny,nz);
      if(length<EPS)return best;
      const r=this._result;r.x=qx;r.y=qy;r.z=qz;r.nx=nx/length*this.orientation;r.ny=ny/length*this.orientation;r.nz=nz/length*this.orientation;r.triangle=t;
      return d;
    }
    return best;
  }

  _rayBox(b,x,y,z) {
    const near=Math.max(0,b[0]-x,(b[1]-y)/.3713906763541037,(b[2]-z)/.2178323154395887);
    const far=Math.min(b[3]-x,(b[4]-y)/.3713906763541037,(b[5]-z)/.2178323154395887);
    if(far<near)return false;
    return far>1e-8;
  }

  _rayTriangle(t,x,y,z) {
    const p=this.positions,ia=this.triangles[t*3]*3,ib=this.triangles[t*3+1]*3,ic=this.triangles[t*3+2]*3;
    const e1x=p[ib]-p[ia],e1y=p[ib+1]-p[ia+1],e1z=p[ib+2]-p[ia+2],e2x=p[ic]-p[ia],e2y=p[ic+1]-p[ia+1],e2z=p[ic+2]-p[ia+2];
    const dy=.3713906763541037,dz=.2178323154395887,hx=dy*e2z-dz*e2y,hy=dz*e2x-e2z,hz=e2y-dy*e2x;
    const det=e1x*hx+e1y*hy+e1z*hz;if(Math.abs(det)<EPS)return;
    const inv=1/det,sx=x-p[ia],sy=y-p[ia+1],sz=z-p[ia+2],u=(sx*hx+sy*hy+sz*hz)*inv;if(u< -1e-9||u>1+1e-9)return;
    const qx=sy*e1z-sz*e1y,qy=sz*e1x-sx*e1z,qz=sx*e1y-sy*e1x,v=(qx+dy*qy+dz*qz)*inv;if(v< -1e-9||u+v>1+1e-9)return;
    const distance=(e2x*qx+e2y*qy+e2z*qz)*inv;if(distance>1e-8)this._hits.push(distance);
  }

  _rayInside(x,y,z) {
    if(this._boxDistance(this.bounds,x,y,z)>0)return false;
    const stack=this._stack,hits=this._hits;stack.length=0;hits.length=0;stack.push(this._root);
    while(stack.length) {
      const n=this._nodes[stack.pop()];if(!this._rayBox(n.bounds,x,y,z))continue;
      if(n.left<0){for(let i=n.start;i<n.end;i++)this._rayTriangle(this._order[i],x,y,z);}
      else stack.push(n.left,n.right);
    }
    hits.sort((a,b)=>a-b);let unique=0,last=-Infinity;
    for(let i=0;i<hits.length;i++)if(hits[i]-last>1e-7){unique++;last=hits[i];}
    return unique%2===1;
  }

  query(x,y,z) {
    const stack=this._stack;stack.length=0;stack.push(this._root);let best=Infinity;
    while(stack.length) {
      const node=this._nodes[stack.pop()];if(this._boxDistance(node.bounds,x,y,z)>best)continue;
      if(node.left<0){for(let i=node.start;i<node.end;i++)best=this._trianglePoint(this._order[i],x,y,z,best);}
      else {
        const a=this._boxDistance(this._nodes[node.left].bounds,x,y,z),b=this._boxDistance(this._nodes[node.right].bounds,x,y,z);
        if(a<b){if(b<=best)stack.push(node.right);if(a<=best)stack.push(node.left);}
        else {if(a<=best)stack.push(node.left);if(b<=best)stack.push(node.right);}
      }
    }
    const r=this._result;r.distance=Math.sqrt(best);r.inside=r.distance>1e-8&&this._rayInside(x,y,z);r.signedDistance=r.inside?-r.distance:r.distance;return r;
  }

  contains(x,y,z,padding=0) { return this.query(x,y,z).signedDistance<padding; }

  project(x,y,z,padding=.004,out=this._output) {
    out[0]=x;out[1]=y;out[2]=z;
    for(let iteration=0;iteration<6;iteration++) {
      const r=this.query(out[0],out[1],out[2]);
      if(r.signedDistance>=padding-1e-7)return out;
      let nx=r.nx,ny=r.ny,nz=r.nz;
      if(r.distance>1e-8&&!r.inside){nx=(out[0]-r.x)/r.distance;ny=(out[1]-r.y)/r.distance;nz=(out[2]-r.z)/r.distance;}
      const offset=Math.max(1e-6,padding+2e-6);
      out[0]=r.x+nx*offset;out[1]=r.y+ny*offset;out[2]=r.z+nz*offset;
    }
    return out;
  }
}
