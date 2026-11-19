import * as T from 'three/webgpu'
import { interpolate } from './mounts.mjs'

export function makeTrimView(scene,definitions){
  const group=new T.Group()
  scene.add(group)
  const buttonGeometry=new T.CylinderGeometry(.01,.0094,.00323,24)
  const slitGeometry=new T.CapsuleGeometry(.0014,.018,4,8).rotateZ(Math.PI/2)
  const dark=new T.MeshStandardMaterial({color:0x191b19,roughness:.55})
  const seam=new T.MeshStandardMaterial({color:0x16352d,roughness:.94})
  const ink=new T.MeshBasicMaterial({color:0x262626})
  const axis=new T.Vector3(0,1,0)
  const normal=new T.Vector3()
  const u=new T.Vector3(),v=new T.Vector3()
  const textureDirection=new T.Vector3()
  const basis=new T.Matrix4()
  const objects=definitions.map(({kind})=>{
    const mesh=new T.Mesh(kind==='button'?buttonGeometry:slitGeometry,kind==='button'?dark:seam)
    group.add(mesh)
    return mesh
  })
  function update(positions,flat,trims){
    return trims.map(({kind,key,host,anchor,targetUv,projectionMm},i)=>{
      const [a,b,c]=anchor.map(id=>id*3)
      u.set(positions[b]-positions[a],positions[b+1]-positions[a+1],positions[b+2]-positions[a+2])
      v.set(positions[c]-positions[a],positions[c+1]-positions[a+1],positions[c+2]-positions[a+2])
      normal.crossVectors(u,v).normalize()
      if(normal.z<0)normal.negate()
      const mesh=objects[i]
      mesh.position.fromArray(interpolate(positions,anchor,3))
      mesh.position.addScaledVector(normal,kind==='button'?.0024:.0014)
      if(kind==='button')mesh.quaternion.setFromUnitVectors(axis,normal)
      else{
        const dv1=flat[2*anchor[1]+1]-flat[2*anchor[0]+1]
        const dv2=flat[2*anchor[2]+1]-flat[2*anchor[0]+1]
        textureDirection.copy(u).multiplyScalar(dv2).addScaledVector(v,-dv1).normalize()
        u.crossVectors(normal,textureDirection).normalize()
        mesh.quaternion.setFromRotationMatrix(basis.makeBasis(textureDirection,normal,u.negate()))
      }
      return {kind,key,host,anchor,targetUv,projectionMm,position:mesh.position.toArray()}
    })
  }
  function setMode(mode){
    group.visible=mode==='appearance'||mode==='line'
    objects.forEach((mesh,i)=>{mesh.material=mode==='line'?ink:definitions[i].kind==='button'?dark:seam})
  }
  return {update,setMode}
}
