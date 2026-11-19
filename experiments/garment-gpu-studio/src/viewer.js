import * as THREE from 'three';
import {OrbitControls}from 'three/addons/controls/OrbitControls.js';
import {selectByRay}from './debugger.js';
export class Viewer{
 constructor(container,onSelect){
  this.container=container;this.onSelect=onSelect;this.mode='fabric';
  this.scene=new THREE.Scene();this.scene.background=new THREE.Color('#eef0ec');
  this.camera=new THREE.PerspectiveCamera(34,1,.01,20);this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,preserveDrawingBuffer:true});
  this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));this.renderer.outputColorSpace=THREE.SRGBColorSpace;this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.25;container.append(this.renderer.domElement);
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.target.set(0,.86,0);this.camera.position.set(1.35,1.2,2.8);
  this.scene.add(new THREE.HemisphereLight('#ffffff','#879081',2.6));let l=new THREE.DirectionalLight('#ffffff',3.5);l.position.set(2,4,4);this.scene.add(l);l=new THREE.DirectionalLight('#dae5ff',1.6);l.position.set(-3,2,-2);this.scene.add(l);
  const floor=new THREE.Mesh(new THREE.CircleGeometry(1.25,96),new THREE.MeshStandardMaterial({color:'#dce0d7',roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.y=-.005;this.scene.add(floor);
  const grid=new THREE.GridHelper(2.4,24,'#c7ccc3','#e0e4db');grid.position.y=-.003;this.scene.add(grid);
  this.marker=new THREE.Mesh(new THREE.SphereGeometry(.009,12,12),new THREE.MeshBasicMaterial({color:'#ff6534',depthTest:false}));this.marker.renderOrder=10;this.marker.visible=false;this.scene.add(this.marker);
  this.ray=new THREE.Raycaster();const mouse=new THREE.Vector2();
  this.renderer.domElement.addEventListener('dblclick',e=>{if(!this.cloth)return;const r=this.renderer.domElement.getBoundingClientRect();mouse.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);this.ray.setFromCamera(mouse,this.camera);const selection=selectByRay(this.ray,this.cloth,this.model);if(selection)this.onSelect(selection);});
  this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(container);this.resize();
  const gl=this.renderer.getContext();const debug=gl.getExtension('WEBGL_debug_renderer_info');this.renderInfo=debug?gl.getParameter(debug.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER);
  this.renderer.setAnimationLoop(()=>{this.controls.update();this.renderer.render(this.scene,this.camera);});
 }
 resize(){const w=this.container.clientWidth,h=this.container.clientHeight;this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.renderer.setSize(w,h);}
 remove(obj){if(obj){this.scene.remove(obj);obj.geometry?.dispose();obj.material?.dispose();}}
 setProject(body,doc,model,p){for(const obj of [this.body,this.cloth,this.lines,this.seamLines])this.remove(obj);Object.assign(this,{doc,model});
  const bg=new THREE.BufferGeometry();bg.setAttribute('position',new THREE.Float32BufferAttribute(body.positions,3));bg.setIndex(body.triangles);bg.computeVertexNormals();this.body=new THREE.Mesh(bg,new THREE.MeshStandardMaterial({color:'#b6b9ad',roughness:.82,metalness:.04}));this.scene.add(this.body);
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(p),3));g.setAttribute('color',new THREE.BufferAttribute(new Float32Array(p.length),3));g.setIndex(doc.mesh.triangles);g.computeVertexNormals();
  this.cloth=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:'#ffffff',vertexColors:true,side:THREE.DoubleSide,roughness:.9,metalness:0}));this.cloth.frustumCulled=false;this.scene.add(this.cloth);
  this.lines=new THREE.LineSegments(new THREE.WireframeGeometry(g),new THREE.LineBasicMaterial({color:'#343c4f',transparent:true,opacity:.23}));this.lines.visible=false;this.scene.add(this.lines);
  this.seamLines=new THREE.LineSegments(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:'#e8f06d',depthTest:false}));this.seamLines.renderOrder=3;this.scene.add(this.seamLines);this.update(p,null,null,null);
 }
 update(p,strain,folds,collision){if(!this.cloth)return;this.p=p;
  const g=this.cloth.geometry;g.attributes.position.array.set(p);g.attributes.position.needsUpdate=true;g.computeVertexNormals();const c=new THREE.Color(),colors=g.attributes.color.array;
  for(let i=0;i<p.length/3;i++){
   if(this.mode==='strain'&&strain)c.setHSL(.62-Math.min(1,strain.perVertex[i]/.25)*.62,.82,.52);
   else if(this.mode==='stress'&&strain)c.setHSL(.62-Math.min(1,strain.vertexStress[i]/30000)*.62,.82,.52);
   else if(this.mode==='folds'&&folds)c.setHSL(.62-Math.min(1,folds.perVertex[i]/120)*.62,.82,.52);
   else if(this.mode==='collision'&&collision)c.set(collision.distances[i]<-.0001||collision.crossingVertices?.has(i)?'#e64d39':collision.distances[i]<.006?'#f5c452':'#4266c6');
   else if(this.mode==='debug'){
    const index=this.doc.pieces.findIndex(x=>i>=x.offset&&i<x.offset+x.vertices.length);c.set(['#6179a9','#6c9989','#cf937b','#b69bc7'][Math.max(0,index)]);
   }else c.set('#6074b7');colors[i*3]=c.r;colors[i*3+1]=c.g;colors[i*3+2]=c.b;
  }g.attributes.color.needsUpdate=true;
  this.lines.visible=this.mode==='debug';if(this.lines.visible){this.lines.geometry.dispose();this.lines.geometry=new THREE.WireframeGeometry(g);}
  const seam=[];for(const s of this.doc.seams)for(let i=1;i<s.pairs.length;i++)for(const j of [i-1,i]){const k=s.pairs[j][0];seam.push(...p.slice(k*3,k*3+3));}
  this.seamLines.geometry.dispose();this.seamLines.geometry=new THREE.BufferGeometry();this.seamLines.geometry.setAttribute('position',new THREE.Float32BufferAttribute(seam,3));this.seamLines.visible=this.mode==='debug';
 }
 select(vertex){if(!this.p)return;this.marker.position.fromArray(this.p,vertex*3);this.marker.visible=true;this.controls.target.copy(this.marker.position);}
 view(name){const y=1.05,views={front:[0,y,3.15],back:[0,y,-3.15],left:[-3.15,y,0],right:[3.15,y,0],iso:[1.45,1.2,2.8]};this.camera.position.set(...(views[name]||views.iso));this.controls.target.set(0,.86,0);this.controls.update();}
 transparency(value){this.body.material.transparent=value;this.body.material.opacity=value?.24:1;this.body.material.depthWrite=!value;}
}
