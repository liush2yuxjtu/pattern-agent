import * as THREE from 'three';

export class SoftwareRenderer {
  constructor() {
    this.domElement=document.createElement('canvas');
    this.ctx=this.domElement.getContext('2d');
    this.shadowMap={};this.ratio=1;this.background='#e9e9e4';
    this.info={render:{calls:0,triangles:0,depthPassingPixelWrites:0}};
  }
  setPixelRatio(r){this.ratio=r;}
  setClearColor(c){this.background=c;}
  setSize(w,h){this.width=w;this.height=h;this.domElement.width=w*this.ratio;this.domElement.height=h*this.ratio;}
  setAnimationLoop(fn){const tick=()=>{fn();requestAnimationFrame(tick)};requestAnimationFrame(tick);}
  render(scene,camera){
    this.info.render={calls:0,triangles:0,depthPassingPixelWrites:0};
    scene.updateMatrixWorld();camera.updateMatrixWorld();
    const ctx=this.ctx,w=this.domElement.width,h=this.domElement.height;
    if(!w||!h)return;
    const image=ctx.createImageData(w,h),pixels=image.data,depth=new Float32Array(w*h).fill(Infinity);
    for(let i=0;i<pixels.length;i+=4){pixels[i]=233;pixels[i+1]=233;pixels[i+2]=228;pixels[i+3]=255;}
    const vp=new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse);
    const triangles=[];const sun=new THREE.Vector3(-.4,.8,.6).normalize();
    scene.traverse(obj=>{
      if(!obj.isMesh||!obj.visible)return;
      const g=obj.geometry,pos=g.attributes.position,index=g.index,mat=obj.material;
      if(!pos||Array.isArray(mat))return;
      this.info.render.calls++;
      const m=new THREE.Matrix4().multiplyMatrices(vp,obj.matrixWorld);
      const world=[],screen=[];
      for(let i=0;i<pos.count;i++){
        const v=new THREE.Vector3().fromBufferAttribute(pos,i);
        world.push(v.clone().applyMatrix4(obj.matrixWorld));
        const p=v.applyMatrix4(m);screen.push([(p.x*.5+.5)*w,(-p.y*.5+.5)*h,p.z]);
      }
      const n=index?index.count:pos.count;
      for(let i=0;i<n;i+=3){
        const a=index?index.getX(i):i,b=index?index.getX(i+1):i+1,c=index?index.getX(i+2):i+2;
        const A=screen[a],B=screen[b],C=screen[c];
        if(!A||!B||!C||[A,B,C].some(p=>p[2]>1||p[2]<-1))continue;
        if((A[0]<0&&B[0]<0&&C[0]<0)||(A[0]>w&&B[0]>w&&C[0]>w))continue;
        const normal=world[b].clone().sub(world[a]).cross(world[c].clone().sub(world[a])).normalize();
        const shade=mat.isMeshBasicMaterial?1:.63+.37*Math.abs(normal.dot(sun));
        const base=mat.color.clone();
        if(mat.vertexColors&&g.attributes.color){
          const colors=g.attributes.color;
          base.setRGB((colors.getX(a)+colors.getX(b)+colors.getX(c))/3,(colors.getY(a)+colors.getY(b)+colors.getY(c))/3,(colors.getZ(a)+colors.getZ(b)+colors.getZ(c))/3);
        }
        const color=base.multiplyScalar(shade).getHex();
        triangles.push({A,B,C,z:(A[2]+B[2]+C[2])/3,color,wire:mat.wireframe});
      }
    });
    this.info.render.triangles=triangles.length;
    for(const t of triangles){
      const [ax,ay,az]=t.A,[bx,by,bz]=t.B,[cx,cy,cz]=t.C;
      const d=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy);
      if(Math.abs(d)<.00001)continue;
      const minX=Math.max(0,Math.floor(Math.min(ax,bx,cx))),maxX=Math.min(w-1,Math.ceil(Math.max(ax,bx,cx)));
      const minY=Math.max(0,Math.floor(Math.min(ay,by,cy))),maxY=Math.min(h-1,Math.ceil(Math.max(ay,by,cy)));
      const red=t.color>>16&255,green=t.color>>8&255,blue=t.color&255;
      for(let y=minY;y<=maxY;y++)for(let x=minX;x<=maxX;x++){
        const u=((by-cy)*(x+.5-cx)+(cx-bx)*(y+.5-cy))/d;
        const v=((cy-ay)*(x+.5-cx)+(ax-cx)*(y+.5-cy))/d;
        const q=1-u-v;if(u<0||v<0||q<0)continue;
        const z=u*az+v*bz+q*cz,k=y*w+x;if(z>=depth[k])continue;
        depth[k]=z;const j=k*4;
        this.info.render.depthPassingPixelWrites++;
        const line=t.wire&&Math.min(u,v,q)<.045;
        pixels[j]=line?65:red;pixels[j+1]=line?75:green;pixels[j+2]=line?60:blue;
      }
    }
    ctx.putImageData(image,0,0);
  }
}
