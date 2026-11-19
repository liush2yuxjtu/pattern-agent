import * as THREE from 'three';
import {OrbitControls}from 'three/addons/controls/OrbitControls.js';
import {selectByRay}from './debugger.js';
export class Viewer{
 constructor(container,onSelect){
  this.container=container;this.onSelect=onSelect;this.mode='fabric';this.pendingFrame=null;
  this.scene=new THREE.Scene();this.scene.background=new THREE.Color('#eef0ec');
  this.camera=new THREE.PerspectiveCamera(34,1,.01,20);this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});
  this.renderer.outputColorSpace=THREE.SRGBColorSpace;this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.25;container.append(this.renderer.domElement);
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.target.set(0,.86,0);this.camera.position.set(1.35,1.2,2.8);
  this.scene.add(new THREE.HemisphereLight('#ffffff','#879081',2.6));let l=new THREE.DirectionalLight('#ffffff',3.5);l.position.set(2,4,4);this.scene.add(l);l=new THREE.DirectionalLight('#dae5ff',1.6);l.position.set(-3,2,-2);this.scene.add(l);
  const floor=new THREE.Mesh(new THREE.CircleGeometry(1.25,96),new THREE.MeshStandardMaterial({color:'#dce0d7',roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.y=-.005;this.scene.add(floor);
  const grid=new THREE.GridHelper(2.4,24,'#c7ccc3','#e0e4db');grid.position.y=-.003;this.scene.add(grid);
  this.marker=new THREE.Mesh(new THREE.SphereGeometry(.009,12,12),new THREE.MeshBasicMaterial({color:'#ff6534',depthTest:false}));this.marker.renderOrder=10;this.marker.visible=false;this.scene.add(this.marker);
  this.ray=new THREE.Raycaster();const mouse=new THREE.Vector2();
  this.renderer.domElement.addEventListener('dblclick',e=>{if(!this.cloth)return;const r=this.renderer.domElement.getBoundingClientRect();mouse.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);this.ray.setFromCamera(mouse,this.camera);const selection=selectByRay(this.ray,this.cloth,this.model);if(selection)this.onSelect(selection);});
  this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(container);this.resize();
  const gl=this.renderer.getContext();const debug=gl.getExtension('WEBGL_debug_renderer_info');this.renderInfo=debug?gl.getParameter(debug.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER);
  this.controls.addEventListener('change',()=>this.requestRender());
  this.renderer.domElement.addEventListener('webglcontextrestored',()=>this.requestRender());
 }
 requestRender(){
  if(this.pendingFrame!==null||this.mode==='pattern')return;
  this.pendingFrame=requestAnimationFrame(()=>{
   if(this.mode==='pattern'){this.pendingFrame=null;return;}
   const moving=this.controls.update();
   this.pendingFrame=null;
   this.renderer.render(this.scene,this.camera);
   if(moving)this.requestRender();
  });
 }
 resize(){
  const w=this.container.clientWidth,h=this.container.clientHeight;
  if(!w||!h)return;
  this.camera.aspect=w/h;this.camera.updateProjectionMatrix();
  this.renderer.setDrawingBufferSize(w,h,Math.min(devicePixelRatio,1.5));
  this.renderer.domElement.style.width=w+'px';this.renderer.domElement.style.height=h+'px';
  this.requestRender();
 }
 remove(obj){if(obj){this.scene.remove(obj);obj.geometry?.dispose();obj.material?.dispose();}}
 setProject(body,doc,model,p){for(const obj of [this.body,this.cloth,this.lines,this.seamLines])this.remove(obj);Object.assign(this,{doc,model});this.p=null;this.colorMode=null;this.marker.visible=false;
  const bg=new THREE.BufferGeometry();bg.setAttribute('position',new THREE.Float32BufferAttribute(body.positions,3));bg.setIndex(body.triangles);bg.computeVertexNormals();this.body=new THREE.Mesh(bg,new THREE.MeshStandardMaterial({color:'#b6b9ad',roughness:.82,metalness:.04}));this.scene.add(this.body);
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(p),3).setUsage(THREE.DynamicDrawUsage));g.setAttribute('color',new THREE.BufferAttribute(new Float32Array(p.length),3).setUsage(THREE.DynamicDrawUsage));g.setIndex(doc.mesh.triangles);
  this.cloth=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:'#ffffff',vertexColors:true,side:THREE.DoubleSide,roughness:.9,metalness:0}));this.cloth.frustumCulled=false;this.scene.add(this.cloth);
  this.lines=null;this.seamLines=null;this.update(p,null,null,null);
 }
 createLines(vertices,material){
  const geometry=new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(vertices.length*3),3).setUsage(THREE.DynamicDrawUsage));
  const lines=new THREE.LineSegments(geometry,material);
  lines.frustumCulled=false;
  lines.userData.vertices=vertices;
  this.scene.add(lines);
  return lines;
 }
 updateLines(lines,p){
  const position=lines.geometry.attributes.position;
  lines.userData.vertices.forEach((vertex,i)=>{
   const offset=vertex*3;
   position.setXYZ(i,p[offset],p[offset+1],p[offset+2]);
  });
  position.needsUpdate=true;
 }
 update(p,strain,folds,collision){
  if(!this.cloth||this.mode==='pattern')return;
  const g=this.cloth.geometry,positionsChanged=this.p!==p,modeChanged=this.colorMode!==this.mode;
  this.p=p;this.colorMode=this.mode;
  if(positionsChanged){
   g.attributes.position.array.set(p);g.attributes.position.needsUpdate=true;
   g.boundingSphere=null;
   g.computeVertexNormals();g.attributes.normal.setUsage(THREE.DynamicDrawUsage);
  }
  const scalar=this.mode==='strain'?strain?.perVertex:this.mode==='stress'?strain?.vertexStress:this.mode==='folds'?folds?.perVertex:null;
  if(modeChanged||scalar||this.mode==='collision'){
   const c=new THREE.Color(),colors=g.attributes.color;
   if(scalar){
    const max={strain:.25,stress:30000,folds:120}[this.mode];
    for(let i=0;i<colors.count;i++){c.setHSL(.62-Math.min(1,scalar[i]/max)*.62,.82,.52);colors.setXYZ(i,c.r,c.g,c.b);}
   }else if(this.mode==='collision'&&collision){
    const red=new THREE.Color('#e64d39'),yellow=new THREE.Color('#f5c452'),blue=new THREE.Color('#4266c6');
    for(let i=0;i<colors.count;i++){
     const color=collision.distances[i]<-.0001||collision.crossingVertices?.has(i)?red:collision.distances[i]<.006?yellow:blue;
     colors.setXYZ(i,color.r,color.g,color.b);
    }
   }else if(this.mode==='debug'){
    const palette=['#6179a9','#6c9989','#cf937b','#b69bc7'];
    this.doc.pieces.forEach((piece,index)=>{
     c.set(palette[index]);
     for(let i=piece.offset;i<piece.offset+piece.vertices.length;i++)colors.setXYZ(i,c.r,c.g,c.b);
    });
   }else{
    c.set('#6074b7');
    for(let i=0;i<colors.count;i++)colors.setXYZ(i,c.r,c.g,c.b);
   }
   colors.needsUpdate=true;
  }
  if(this.mode==='debug'){
   if(!this.lines){
    this.lines=this.createLines(this.doc.mesh.edges.flatMap(({a,b})=>[a,b]),new THREE.LineBasicMaterial({color:'#343c4f',transparent:true,opacity:.23}));
    const vertices=this.doc.seams.flatMap(({pairs})=>pairs.slice(1).flatMap(([vertex],i)=>[pairs[i][0],vertex]));
    this.seamLines=this.createLines(vertices,new THREE.LineBasicMaterial({color:'#e8f06d',depthTest:false}));
    this.seamLines.renderOrder=3;
   }
   if(positionsChanged||modeChanged){this.updateLines(this.lines,p);this.updateLines(this.seamLines,p);}
  }
  if(this.lines)this.lines.visible=this.seamLines.visible=this.mode==='debug';
  this.requestRender();
 }
 select(vertex){if(!this.p)return;this.marker.position.fromArray(this.p,vertex*3);this.marker.visible=true;this.controls.target.copy(this.marker.position);this.requestRender();}
 view(name){const y=1.05,views={front:[0,y,3.15],back:[0,y,-3.15],left:[-3.15,y,0],right:[3.15,y,0],iso:[1.45,1.2,2.8]};this.camera.position.set(...(views[name]||views.iso));this.controls.target.set(0,.86,0);this.controls.update();this.requestRender();}
 transparency(value){this.body.material.transparent=value;this.body.material.opacity=value?.24:1;this.body.material.depthWrite=!value;this.requestRender();}
}
