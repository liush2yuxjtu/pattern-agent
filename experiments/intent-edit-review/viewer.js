class PatternMeshViewer {
  constructor(canvas, camera, frame, onCamera, color) {
    this.canvas=canvas;this.camera=camera;this.frame=frame;this.onCamera=onCamera;this.color=color;
    this.gl=canvas.getContext('webgl',{antialias:true,preserveDrawingBuffer:true});
    this.mode=this.gl?'webgl':'software';this.buffers=[];this.mesh=null;
    if(this.gl)this.initGL();else this.ctx=canvas.getContext('2d');
    let drag=null;
    canvas.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);canvas.focus({preventScroll:true});});
    canvas.addEventListener('pointermove',e=>{if(!drag)return;camera.yaw+=(e.clientX-drag[0])*.008;camera.pitch=Math.max(-1,Math.min(1,camera.pitch+(e.clientY-drag[1])*.008));drag=[e.clientX,e.clientY];onCamera();});
    for(const type of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(type,()=>drag=null);
    canvas.addEventListener('wheel',e=>{e.preventDefault();camera.zoom=Math.max(.55,Math.min(2.4,camera.zoom*Math.exp(-e.deltaY*.001)));onCamera();},{passive:false});
    canvas.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();camera.yaw+=e.key==='ArrowLeft'?-.13:e.key==='ArrowRight'?.13:0;camera.pitch=Math.max(-1,Math.min(1,camera.pitch+(e.key==='ArrowUp'?-.09:e.key==='ArrowDown'?.09:0)));onCamera();});
    new ResizeObserver(()=>this.draw()).observe(canvas);
  }
  initGL(){
    const gl=this.gl;
    const shader=(kind,src)=>{const s=gl.createShader(kind);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;};
    const vertex=`attribute vec3 p;attribute vec3 n;uniform vec3 center;uniform float scale;uniform vec2 angle;uniform float zoom;uniform float aspect;varying vec3 normal;
      void main(){vec3 v=(p-center)/scale;float c=cos(angle.x),s=sin(angle.x),cp=cos(angle.y),sp=sin(angle.y);
      mat3 r=mat3(c,0.,-s,0.,1.,0.,s,0.,c);mat3 t=mat3(1.,0.,0.,0.,cp,sp,0.,-sp,cp);v=t*r*v;normal=t*r*n;
      gl_Position=vec4(v.x*zoom/aspect,v.y*zoom,-v.z*.3,1.);}`;
    const fragment=`precision mediump float;varying vec3 normal;uniform vec3 color;void main(){vec3 N=normalize(normal);
      float light=.62+.32*abs(dot(N,normalize(vec3(-.45,.7,1.))))+.06*abs(N.x);gl_FragColor=vec4(color*light,1.);}`;
    this.program=gl.createProgram();gl.attachShader(this.program,shader(gl.VERTEX_SHADER,vertex));gl.attachShader(this.program,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(this.program);
    if(!gl.getProgramParameter(this.program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(this.program));
    this.locations={};for(const key of ['center','scale','angle','zoom','aspect','color'])this.locations[key]=gl.getUniformLocation(this.program,key);
    this.locations.p=gl.getAttribLocation(this.program,'p');this.locations.n=gl.getAttribLocation(this.program,'n');
  }
  setModel(model,hash){
    const positions=[],normals=[];this.faces=[];
    for(const panel of model.panels){
      const p=panel.positions.flat(Infinity),ix=panel.triangles.flat(Infinity);let ns=(panel.normals||[]).flat(Infinity);
      if(ns.length!==p.length){
        ns=new Array(p.length).fill(0);
        for(let j=0;j<ix.length;j+=3){const a=ix[j]*3,b=ix[j+1]*3,c=ix[j+2]*3;
          const u=[p[b]-p[a],p[b+1]-p[a+1],p[b+2]-p[a+2]],v=[p[c]-p[a],p[c+1]-p[a+1],p[c+2]-p[a+2]];
          const n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
          for(const k of [a,b,c])for(let q=0;q<3;q++)ns[k+q]+=n[q];}
      }
      for(let j=0;j<ix.length;j+=3){const face=[];
        for(let q=0;q<3;q++){const k=ix[j+q]*3,point=p.slice(k,k+3),normal=ns.slice(k,k+3);if(point.some(x=>!Number.isFinite(x)))throw Error('模型坐标无效');positions.push(...point);normals.push(...normal);face.push(point);}
        this.faces.push(face);}
    }
    this.mesh=model;this.count=positions.length/3;
    if(this.gl){const gl=this.gl;this.buffers.forEach(b=>gl.deleteBuffer(b));this.buffers=[];
      for(const array of [positions,normals]){const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(array),gl.STATIC_DRAW);this.buffers.push(buffer);}}
    Object.assign(this.canvas.dataset,{modelId:model.id,modelHash:hash,triangles:String(this.faces.length),mode:this.mode});this.draw();
  }
  dimensions(){
    const dpr=Math.min(devicePixelRatio||1,2),w=Math.max(1,Math.round(this.canvas.clientWidth*dpr)),h=Math.max(1,Math.round(this.canvas.clientHeight*dpr));
    if(this.canvas.width!==w||this.canvas.height!==h){this.canvas.width=w;this.canvas.height=h;}
    const span=this.frame.max.map((v,k)=>v-this.frame.min[k]);
    return {w,h,center:this.frame.max.map((v,k)=>(v+this.frame.min[k])/2),scale:.55*Math.max(span[1],span[0]/(w/h),span[2])};
  }
  draw(){
    if(!this.mesh)return;
    const {w,h,center,scale}=this.dimensions(),cam=this.camera;
    if(this.gl){const gl=this.gl,l=this.locations;gl.useProgram(this.program);gl.viewport(0,0,w,h);gl.clearColor(.933,.945,.953,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);
      gl.uniform3fv(l.center,center);gl.uniform1f(l.scale,scale);gl.uniform2f(l.angle,cam.yaw,cam.pitch);gl.uniform1f(l.zoom,cam.zoom);gl.uniform1f(l.aspect,w/h);gl.uniform3fv(l.color,this.color);
      for(const [i,key] of ['p','n'].entries()){gl.bindBuffer(gl.ARRAY_BUFFER,this.buffers[i]);gl.enableVertexAttribArray(l[key]);gl.vertexAttribPointer(l[key],3,gl.FLOAT,false,0,0);}gl.drawArrays(gl.TRIANGLES,0,this.count);
      if(gl.getError()!==gl.NO_ERROR)throw Error('三维绘制错误');
    }else{
      const ctx=this.ctx,c=Math.cos(cam.yaw),s=Math.sin(cam.yaw),cp=Math.cos(cam.pitch),sp=Math.sin(cam.pitch);
      const transform=p=>{let x=p[0]-center[0],y=p[1]-center[1],z=p[2]-center[2];const xx=c*x+s*z,zz=-s*x+c*z;return [xx,cp*y-sp*zz,sp*y+cp*zz];};
      const faces=this.faces.map(f=>f.map(transform)).sort((a,b)=>a.reduce((s,p)=>s+p[2],0)-b.reduce((s,p)=>s+p[2],0));ctx.fillStyle='#eef1f3';ctx.fillRect(0,0,w,h);
      for(const f of faces){const u=f[1].map((v,k)=>v-f[0][k]),v=f[2].map((v,k)=>v-f[0][k]),n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],len=Math.hypot(...n)||1;
        const light=.62+.38*Math.abs((n[0]*-.346+n[1]*.539+n[2]*.770)/len);ctx.fillStyle=`rgb(${this.color.map(c=>Math.round(c*light*255)).join(',')})`;
        ctx.beginPath();f.forEach((p,i)=>{const x=w/2+p[0]/scale*cam.zoom*h/2,y=h/2-p[1]/scale*cam.zoom*h/2;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.closePath();ctx.fill();}
    }
    Object.assign(this.canvas.dataset,{ready:'true',yaw:String(cam.yaw),pitch:String(cam.pitch),zoom:String(cam.zoom)});
  }
}
