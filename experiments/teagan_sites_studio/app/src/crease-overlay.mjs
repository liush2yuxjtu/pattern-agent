import * as THREE from 'three';
export const creaseColors={smooth:'#26b7a5',warning:'#ffab25',sharp:'#f000b8',excluded:'#8b929c'};
// Fixed degree scale, independent of the current garment's minimum and maximum.
export const creaseAngleStops=[[0,'#244be8'],[5,'#00a4ff'],[15,'#22d9dc'],[25,'#ffe044'],[30,'#ff982c'],[45,'#f000b8']];
export const creaseFullAngleStops=[[0,'#244be8'],[5,'#00a4ff'],[15,'#22d9dc'],[30,'#ffe044'],[60,'#ff982c'],[90,'#f000b8'],[180,'#6c123d']];
export function creaseScale(maxDeg=180){return maxDeg===45?creaseAngleStops:creaseFullAngleStops;}
export function creaseAngleColor(angle,maxDeg=180){
  const stops=creaseScale(maxDeg),value=Math.max(0,Math.min(maxDeg,angle));let i=1;while(i<stops.length-1&&value>stops[i][0])i++;
  const [lo,a]=stops[i-1],[hi,b]=stops[i];return new THREE.Color(a).convertLinearToSRGB().lerp(new THREE.Color(b).convertLinearToSRGB(),(value-lo)/(hi-lo)).convertSRGBToLinear();
}

export function makeCreaseOverlay(panels,diagnostic,{colorMode='classes',includeUnderarm=false,includeSeams=false,qualityOnly=false,colorMaxDeg=180}={}) {
  const group=new THREE.Group(),marker=new THREE.Group();group.name='measured-sleeve-creases';
  const resources=[];
  for(const part of diagnostic.parts) {
    const panel=panels.find(p=>(p.partId||p.part)===part.partId),faceClass=panel.triangles.map(()=>null),faceAngle=panel.triangles.map(()=>null);
    const rank={excluded:0,smooth:1,warning:2,sharp:3};
    for(const edge of part.edges)for(const f of edge.faces)if(!faceClass[f]||rank[edge.classification]>rank[faceClass[f]])faceClass[f]=edge.classification;
    for(const edge of part.edges)if((!qualityOnly||part.partId.startsWith('sleeve'))&&(includeUnderarm||!edge.excluded))for(const f of edge.faces)faceAngle[f]=Math.max(faceAngle[f]??0,edge.angleDeg);
    if(includeSeams)for(const edge of diagnostic.seams?.samples||[]){if(edge.partId===part.partId)for(const f of edge.faces)faceAngle[f]=Math.max(faceAngle[f]??0,edge.angleDeg);if(edge.counterpart.partId===part.partId){const f=edge.counterpart.face;faceAngle[f]=Math.max(faceAngle[f]??0,edge.angleDeg);}}
    const positions=[],colors=[],linePositions=[],lineColors=[];
    panel.triangles.forEach((t,f)=>{const color=colorMode==='angle'?(faceAngle[f]===null?new THREE.Color(creaseColors.excluded):creaseAngleColor(faceAngle[f],colorMaxDeg)):new THREE.Color(creaseColors[faceClass[f]||'excluded']);for(const i of t){positions.push(...panel.vertices[i]);colors.push(...color.toArray());}});
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));
    const material=new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.DoubleSide,transparent:colorMode!=='angle',opacity:colorMode==='angle'?1:.83,toneMapped:colorMode!=='angle',depthWrite:false,polygonOffset:true,polygonOffsetFactor:-2,polygonOffsetUnits:-2});
    const mesh=new THREE.Mesh(g,material);mesh.name='crease-faces';mesh.userData={partId:part.partId,faceAngles:faceAngle};mesh.renderOrder=2;group.add(mesh);resources.push(g,material);
    const lineEdges=[...part.edges,...(includeSeams?(diagnostic.seams?.samples||[]).filter(e=>e.partId===part.partId):[])];
    for(const edge of lineEdges){if(colorMode==='angle'?(!edge.excluded&&edge.angleDeg<=diagnostic.limits.limitDeg&&edge.kind!=='seam'):edge.classification==='smooth')continue;const color=colorMode==='angle'?(edge.excluded&&!includeUnderarm||qualityOnly&&!part.partId.startsWith('sleeve')?new THREE.Color(creaseColors.excluded):creaseAngleColor(edge.angleDeg,colorMaxDeg)):new THREE.Color(creaseColors[edge.classification]);for(const i of[edge.a,edge.b]){linePositions.push(...panel.vertices[i]);lineColors.push(...color.toArray());}}
    if(colorMode==='angle')for(const e of panel.boundary||[])if(['hem','neck'].includes(e.edge))for(const i of[e.a,e.b]){linePositions.push(...panel.vertices[i]);lineColors.push(...new THREE.Color(creaseColors.excluded).toArray());}
    const lines=new THREE.BufferGeometry();lines.setAttribute('position',new THREE.Float32BufferAttribute(linePositions,3));lines.setAttribute('color',new THREE.Float32BufferAttribute(lineColors,3));
    const lm=new THREE.LineBasicMaterial({vertexColors:true,transparent:true,opacity:.95,toneMapped:colorMode!=='angle',depthWrite:false});const lineMesh=new THREE.LineSegments(lines,lm);lineMesh.renderOrder=3;group.add(lineMesh);resources.push(lines,lm);
  }
  group.add(marker);
  function clearMarker(){while(marker.children.length){const child=marker.children[0];child.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});marker.remove(child);}}
  function select(edge){
    clearMarker();if(!edge)return;
    const p=panels.find(p=>(p.partId||p.part)===(edge.partId||edge.id.split(':')[0]));
    const a=new THREE.Vector3(...p.vertices[edge.a]),b=new THREE.Vector3(...p.vertices[edge.b]),mid=a.clone().add(b).multiplyScalar(.5),direction=b.clone().sub(a);
    const selectedColor=colorMode==='angle'?creaseAngleColor(edge.angleDeg,colorMaxDeg):new THREE.Color(creaseColors[edge.classification]);
    const g=new THREE.CylinderGeometry(.0017,.0017,direction.length(),8),m=new THREE.MeshBasicMaterial({color:selectedColor,toneMapped:colorMode!=='angle'});
    const cylinder=new THREE.Mesh(g,m);cylinder.position.copy(mid);cylinder.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),direction.normalize());marker.add(cylinder);
    const ball=new THREE.Mesh(new THREE.SphereGeometry(.004,12,8),new THREE.MeshBasicMaterial({color:0xffffff}));ball.position.copy(mid);marker.add(ball);
    for(let i=0;i<2;i++)marker.add(new THREE.ArrowHelper(new THREE.Vector3(...edge.normals[i]),new THREE.Vector3(...edge.faceCenters[i]),.04,i===0?0x385dff:0xffba24,.008,.004));
  }
  return {group,select,dispose(){clearMarker();resources.forEach(r=>r.dispose());group.removeFromParent();}};
}
