import * as THREE from 'three';

// Fit the current bounds in the camera's viewing direction, including depth.
function fittedDistance(box, camera, aspect, direction) {
  const center = box.getCenter(new THREE.Vector3());
  const right = new THREE.Vector3().crossVectors(camera.up, direction).normalize();
  if (right.lengthSq() < 1e-8) right.set(1, 0, 0);
  const up = new THREE.Vector3().crossVectors(direction, right).normalize();
  const tangent = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  let distance = camera.near * 4;
  for (const x of [box.min.x, box.max.x]) {
    for (const y of [box.min.y, box.max.y]) {
      for (const z of [box.min.z, box.max.z]) {
        const corner = new THREE.Vector3(x, y, z).sub(center);
        distance = Math.max(distance, corner.dot(direction) + 1.12 * Math.max(
          Math.abs(corner.dot(right)) / (tangent * aspect),
          Math.abs(corner.dot(up)) / tangent,
        ));
      }
    }
  }
  return distance;
}

export class SceneViewport {
  constructor({renderer, camera, controls, element, bounds, prepare, changed, resetView, releaseResources}) {
    Object.assign(this, {renderer, camera, controls, element, bounds, prepare, changed});
    this.frames = 0;
    this.losses = 0;
    this.restorations = 0;
    this.lost = false;
    this.previous = null;
    this.retryTimers = [];
    this.clearColor = renderer.getClearColor(new THREE.Color()).clone();
    this.clearAlpha = renderer.getClearAlpha();
    // Retain the extension before a loss: getExtension may return null while lost.
    this.contextExtension = renderer.getContext().getExtension('WEBGL_lose_context');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'scene-reset';
    button.textContent = '恢复显示';
    button.setAttribute('aria-label', element.id === 'scene' ? '恢复三维实体显示' : element.id === 'heat-scene' ? '恢复三维拉伸热图显示' : element.id === 'crease-scene' ? '恢复三维折角热图显示' : '恢复当前三维显示');
    button.title = '将当前衣片移回窗口中央';
    button.onclick = () => { this.restoreContext(); resetView(); };
    element.appendChild(button);
    this.notice = document.createElement('div');
    this.notice.className = 'scene-status';
    this.notice.setAttribute('role', 'status');
    this.notice.hidden = true;
    element.appendChild(this.notice);
    renderer.domElement.addEventListener('webglcontextlost', event => {
      event.preventDefault();
      this.lost = true;
      this.losses++;
      // Dispose GPU associations while the old context is lost. CPU geometry is
      // retained; each renderer uploads it again. Otherwise Three.js's old
      // geometry listeners can later try to delete handles from the lost context.
      releaseResources();
      this.notice.hidden = false;
      this.notice.textContent = '三维显示中断，正在恢复…';
      this.clearRetries();
      for (const delay of [200, 800, 2000]) {
        this.retryTimers.push(setTimeout(() => this.restoreContext(), delay));
      }
      this.changed();
    });
    renderer.domElement.addEventListener('webglcontextrestored', () => {
      // Three.js registers its own restore listener first and rebuilds GPU resources.
      this.lost = false;
      this.restorations++;
      this.clearRetries();
      this.notice.hidden = true;
      renderer.setClearColor(this.clearColor, this.clearAlpha);
      this.resize();
      this.render();
      this.changed();
    });
  }

  clearRetries() {
    this.retryTimers.forEach(clearTimeout);
    this.retryTimers = [];
  }

  restoreContext() {
    if (this.lost && this.contextExtension) this.contextExtension.restoreContext();
  }

  setPose(position, target) {
    const damping = this.controls.enableDamping;
    this.controls.enableDamping = false;
    this.controls.update(); // Consume pending orbit deltas before setting the new pose.
    this.controls.target.copy(target);
    this.camera.position.copy(position);
    this.controls.update();
    this.controls.enableDamping = damping;
  }

  fit(box, aspect, direction) {
    const distance = fittedDistance(box, this.camera, aspect, direction);
    this.controls.maxDistance = Math.max(8, distance * 4);
    this.camera.far = Math.max(30, distance * 8 + box.getSize(new THREE.Vector3()).length());
    return distance;
  }

  reset(back = false) {
    if (!this.element.clientWidth || !this.element.clientHeight) return;
    this.resize();
    const box = this.bounds();
    const center = box.getCenter(new THREE.Vector3());
    const direction = new THREE.Vector3(0, 0, back ? -1 : 1);
    const distance = this.fit(box, this.camera.aspect, direction);
    this.setPose(direction.multiplyScalar(distance).add(center), center);
    this.camera.updateProjectionMatrix();
    this.previous = {box: box.clone(), aspect: this.camera.aspect};
    this.render();
    this.changed();
  }

  resize() {
    const width = this.element.clientWidth, height = this.element.clientHeight;
    if (!width || !height) return;
    const {renderer, camera, controls} = this;
    // Bound each drawing buffer's memory when multiple 3D views are open on high-DPI screens.
    const ratio = Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(1_500_000 / (width * height)));
    const size = renderer.getSize(new THREE.Vector2());
    if (renderer.getPixelRatio() !== ratio) renderer.setPixelRatio(ratio);
    if (size.x !== width || size.y !== height) renderer.setSize(width, height, false);
    const aspect = width / height, box = this.bounds();
    const old = this.previous;
    if (old && old.aspect === aspect && old.box.equals(box)) return;
    const center = box.getCenter(new THREE.Vector3());
    let direction = camera.position.clone().sub(controls.target);
    const currentDistance = direction.length();
    if (currentDistance < 1e-8) direction.set(0, 0, 1);
    else direction.normalize();
    const distance = this.fit(box, aspect, direction);
    const zoom = old ? currentDistance / fittedDistance(old.box, camera, old.aspect, direction) : 1;
    const target = old ? controls.target.clone().sub(old.box.getCenter(new THREE.Vector3())).add(center) : center;
    camera.aspect = aspect;
    camera.updateProjectionMatrix();
    this.setPose(direction.multiplyScalar(distance * zoom).add(target), target);
    this.previous = {box: box.clone(), aspect};
    this.render();
  }

  render() {
    if (this.lost || this.renderer.getContext().isContextLost() || !this.element.clientWidth || !this.element.clientHeight) return;
    this.controls.update();
    this.prepare(this.renderer, this.camera);
    this.frames++;
  }

  diagnostics() {
    const {renderer, camera, controls, element} = this;
    const box = this.bounds(), projected = [];
    camera.updateMatrixWorld();
    for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) {
      projected.push(new THREE.Vector3(x, y, z).project(camera).toArray());
    }
    return {
      contextLost: this.lost || renderer.getContext().isContextLost(),
      frames: this.frames, losses: this.losses, restorations: this.restorations,
      client: [element.clientWidth, element.clientHeight],
      buffer: [renderer.domElement.width, renderer.domElement.height],
      pixelRatio: renderer.getPixelRatio(),
      camera: camera.position.toArray(), target: controls.target.toArray(),
      aspect: camera.aspect, maxDistance: controls.maxDistance,
      projectedBounds: projected,
    };
  }
}
