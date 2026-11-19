export function createBodyCollider(body) {
  const positions = new Float64Array(body.positions);
  const triangles = new Uint32Array(body.triangles);
  const tree = body.collision.bvh;
  const nodes = new Float64Array(tree.nodes);
  const order = new Uint32Array(tree.triangleOrder);
  const faceCount = triangles.length / 3;
  const faceNormals = new Float64Array(faceCount * 3);
  const triangleData = new Float64Array(faceCount * 12);
  const triangleBounds = new Float64Array(faceCount * 6);
  const neighborhoods = new Array(faceCount);
  const vertexNormals = new Float64Array(positions.length);
  const edgeNormals = new Float64Array(faceCount * 9);
  const edgeFaces = new Map();
  const stack = new Int32Array(nodes.length / 10);
  const stackDistances = new Float64Array(stack.length);
  const parents = new Int32Array(stack.length).fill(-1);
  const siblings = new Int32Array(stack.length).fill(-1);
  const triangleLeaves = new Int32Array(faceCount);
  const vertexCount = positions.length / 3;

  for (let face = 0; face < faceCount; face++) {
    const a = triangles[face * 3] * 3;
    const b = triangles[face * 3 + 1] * 3;
    const c = triangles[face * 3 + 2] * 3;
    const abx = positions[b] - positions[a];
    const aby = positions[b + 1] - positions[a + 1];
    const abz = positions[b + 2] - positions[a + 2];
    const acx = positions[c] - positions[a];
    const acy = positions[c + 1] - positions[a + 1];
    const acz = positions[c + 2] - positions[a + 2];
    const data = face * 12;
    triangleData[data] = positions[a]; triangleData[data + 1] = positions[a + 1]; triangleData[data + 2] = positions[a + 2];
    triangleData[data + 3] = abx; triangleData[data + 4] = aby; triangleData[data + 5] = abz;
    triangleData[data + 6] = acx; triangleData[data + 7] = acy; triangleData[data + 8] = acz;
    triangleData[data + 9] = abx * abx + aby * aby + abz * abz;
    triangleData[data + 10] = abx * acx + aby * acy + abz * acz;
    triangleData[data + 11] = acx * acx + acy * acy + acz * acz;
    const bound = face * 6;
    for (let axis = 0; axis < 3; axis++) {
      triangleBounds[bound + axis] = Math.min(positions[a + axis], positions[b + axis], positions[c + axis]);
      triangleBounds[bound + axis + 3] = Math.max(positions[a + axis], positions[b + axis], positions[c + axis]);
    }
    let nx = aby * acz - abz * acy;
    let ny = abz * acx - abx * acz;
    let nz = abx * acy - aby * acx;
    const length = Math.hypot(nx, ny, nz);
    nx /= length;
    ny /= length;
    nz /= length;
    faceNormals.set([nx, ny, nz], face * 3);
    const ids = [a, b, c];
    for (let corner = 0; corner < 3; corner++) {
      const center = ids[corner];
      const first = ids[(corner + 1) % 3];
      const second = ids[(corner + 2) % 3];
      const ux = positions[first] - positions[center];
      const uy = positions[first + 1] - positions[center + 1];
      const uz = positions[first + 2] - positions[center + 2];
      const vx = positions[second] - positions[center];
      const vy = positions[second + 1] - positions[center + 1];
      const vz = positions[second + 2] - positions[center + 2];
      const cosine = (ux * vx + uy * vy + uz * vz) / (Math.hypot(ux, uy, uz) * Math.hypot(vx, vy, vz));
      const angle = Math.acos(Math.max(-1, Math.min(1, cosine)));
      vertexNormals[center] += angle * nx;
      vertexNormals[center + 1] += angle * ny;
      vertexNormals[center + 2] += angle * nz;
      const firstId = center / 3;
      const secondId = first / 3;
      const key = Math.min(firstId, secondId) * vertexCount + Math.max(firstId, secondId);
      let entries = edgeFaces.get(key);
      if (!entries) edgeFaces.set(key, entries = []);
      entries.push(face * 3 + corner);
    }
  }
  for (const entries of edgeFaces.values()) {
    let x = 0, y = 0, z = 0;
    for (const entry of entries) {
      const normal = Math.floor(entry / 3) * 3;
      x += faceNormals[normal];
      y += faceNormals[normal + 1];
      z += faceNormals[normal + 2];
    }
    for (const entry of entries) edgeNormals.set([x, y, z], entry * 3);
  }
  for (let node = 0; node < stack.length; node++) {
    const offset = node * 10, count = nodes[offset + 9];
    if (count) {
      const start = nodes[offset + 8];
      for (let index = start; index < start + count; index++) triangleLeaves[order[index]] = node;
    } else {
      const left = nodes[offset + 6], right = nodes[offset + 7];
      parents[left] = node; parents[right] = node;
      siblings[left] = right; siblings[right] = left;
    }
  }

  let queryX, queryY, queryZ, bestDistance2, bestFace, bestX, bestY, bestZ, bestU, bestV;

  function testTriangle(face) {
    const data = face * 12;
    const ax = triangleData[data], ay = triangleData[data + 1], az = triangleData[data + 2];
    const abx = triangleData[data + 3], aby = triangleData[data + 4], abz = triangleData[data + 5];
    const acx = triangleData[data + 6], acy = triangleData[data + 7], acz = triangleData[data + 8];
    const apx = queryX - ax, apy = queryY - ay, apz = queryZ - az;
    const d1 = abx * apx + aby * apy + abz * apz;
    const d2 = acx * apx + acy * apy + acz * apz;
    let u, v;
    if (d1 <= 0 && d2 <= 0) {
      u = 1; v = 0;
    } else {
      const d3 = d1 - triangleData[data + 9];
      const d4 = d2 - triangleData[data + 10];
      if (d3 >= 0 && d4 <= d3) {
        u = 0; v = 1;
      } else {
        const vc = d1 * d4 - d3 * d2;
        if (vc <= 0 && d1 >= 0 && d3 <= 0) {
          v = d1 / (d1 - d3); u = 1 - v;
        } else {
          const d5 = d1 - triangleData[data + 10];
          const d6 = d2 - triangleData[data + 11];
          if (d6 >= 0 && d5 <= d6) {
            u = 0; v = 0;
          } else {
            const vb = d5 * d2 - d1 * d6;
            if (vb <= 0 && d2 >= 0 && d6 <= 0) {
              const w = d2 / (d2 - d6); u = 1 - w; v = 0;
            } else {
              const va = d3 * d6 - d5 * d4;
              if (va <= 0 && d4 - d3 >= 0 && d5 - d6 >= 0) {
                const w = (d4 - d3) / ((d4 - d3) + (d5 - d6)); u = 0; v = 1 - w;
              } else {
                const inverse = 1 / (va + vb + vc);
                v = vb * inverse; u = 1 - v - vc * inverse;
              }
            }
          }
        }
      }
    }
    const w = 1 - u - v;
    const x = ax + abx * v + acx * w;
    const y = ay + aby * v + acy * w;
    const z = az + abz * v + acz * w;
    const dx = queryX - x, dy = queryY - y, dz = queryZ - z;
    const distance2 = dx * dx + dy * dy + dz * dz;
    if (distance2 < bestDistance2) {
      bestDistance2 = distance2; bestFace = face;
      bestX = x; bestY = y; bestZ = z; bestU = u; bestV = v;
    }
  }

  function boxDistance2(node) {
    const offset = node * 10;
    const dx = Math.max(nodes[offset] - queryX, 0, queryX - nodes[offset + 3]);
    const dy = Math.max(nodes[offset + 1] - queryY, 0, queryY - nodes[offset + 4]);
    const dz = Math.max(nodes[offset + 2] - queryZ, 0, queryZ - nodes[offset + 5]);
    return dx * dx + dy * dy + dz * dz;
  }

  function searchSubtree(root) {
    let top = 1;
    stack[0] = root;
    stackDistances[0] = boxDistance2(root);
    while (top) {
      const node = stack[--top];
      if (stackDistances[top] > bestDistance2) continue;
      const offset = node * 10;
      const count = nodes[offset + 9];
      if (count) {
        const start = nodes[offset + 8];
        for (let index = start; index < start + count; index++) testTriangle(order[index]);
      } else {
        const left = nodes[offset + 6], right = nodes[offset + 7];
        const leftDistance = boxDistance2(left), rightDistance = boxDistance2(right);
        if (leftDistance < rightDistance) {
          if (rightDistance <= bestDistance2) { stack[top] = right; stackDistances[top++] = rightDistance; }
          if (leftDistance <= bestDistance2) { stack[top] = left; stackDistances[top++] = leftDistance; }
        } else {
          if (leftDistance <= bestDistance2) { stack[top] = left; stackDistances[top++] = leftDistance; }
          if (rightDistance <= bestDistance2) { stack[top] = right; stackDistances[top++] = rightDistance; }
        }
      }
    }
  }

  function collectNeighborhood(cx, cy, cz, radius) {
    const radius2 = (radius + 1e-12) * (radius + 1e-12);
    const candidates = [];
    stack[0] = 0;
    let top = 1;
    while (top) {
      const node = stack[--top], offset = node * 10;
      const dx = Math.max(nodes[offset] - cx, 0, cx - nodes[offset + 3]);
      const dy = Math.max(nodes[offset + 1] - cy, 0, cy - nodes[offset + 4]);
      const dz = Math.max(nodes[offset + 2] - cz, 0, cz - nodes[offset + 5]);
      if (dx * dx + dy * dy + dz * dz > radius2) continue;
      const count = nodes[offset + 9];
      if (count) {
        const start = nodes[offset + 8];
        for (let index = start; index < start + count; index++) {
          const triangle = order[index], bound = triangle * 6;
          const tx = Math.max(triangleBounds[bound] - cx, 0, cx - triangleBounds[bound + 3]);
          const ty = Math.max(triangleBounds[bound + 1] - cy, 0, cy - triangleBounds[bound + 4]);
          const tz = Math.max(triangleBounds[bound + 2] - cz, 0, cz - triangleBounds[bound + 5]);
          if (tx * tx + ty * ty + tz * tz <= radius2) candidates.push(triangle);
        }
      } else {
        stack[top++] = nodes[offset + 6]; stack[top++] = nodes[offset + 7];
      }
    }
    return { cx, cy, cz, radius, triangles: new Uint32Array(candidates) };
  }

  function closestPointInto(x, y, z, hintTriangle, result) {
    queryX = x; queryY = y; queryZ = z;
    bestDistance2 = Infinity; bestFace = -1;
    if (hintTriangle >= 0 && hintTriangle < faceCount) {
      testTriangle(hintTriangle);
      const hintDistance = Math.sqrt(bestDistance2);
      let cache = neighborhoods[hintTriangle], neighborhood;
      if (cache) for (let index = 0; index < cache.entries.length; index++) {
        const entry = cache.entries[index], dx = x - entry.cx, dy = y - entry.cy, dz = z - entry.cz;
        const available = entry.radius - hintDistance - 1e-10;
        // Omitted triangles lie outside this ball, so its remaining radius is a strict distance lower bound.
        if (available > 0 && dx * dx + dy * dy + dz * dz < available * available) { neighborhood = entry; break; }
      }
      if (!neighborhood && hintDistance <= .02) {
        neighborhood = collectNeighborhood(x, y, z, hintDistance + .004);
        if (!cache) neighborhoods[hintTriangle] = cache = { entries: [], next: 0 };
        if (cache.entries.length < 4) cache.entries.push(neighborhood);
        else { cache.entries[cache.next] = neighborhood; cache.next = (cache.next + 1) % 4; }
      }
      if (neighborhood) {
        const candidates = neighborhood.triangles;
        for (let index = 0; index < candidates.length; index++) if (candidates[index] !== hintTriangle) testTriangle(candidates[index]);
      } else {
        let child = triangleLeaves[hintTriangle];
        const offset = child * 10, start = nodes[offset + 8], count = nodes[offset + 9];
        for (let index = start; index < start + count; index++) {
          const face = order[index];
          if (face !== hintTriangle) testTriangle(face);
        }
        for (; parents[child] >= 0; child = parents[child]) searchSubtree(siblings[child]);
      }
    } else searchSubtree(0);
    const epsilon = 1e-8;
    const w = 1 - bestU - bestV;
    let normalArray = faceNormals, normalIndex = bestFace * 3;
    if (bestU <= epsilon && bestV <= epsilon) {
      normalArray = vertexNormals; normalIndex = triangles[bestFace * 3 + 2] * 3;
    } else if (bestU <= epsilon && w <= epsilon) {
      normalArray = vertexNormals; normalIndex = triangles[bestFace * 3 + 1] * 3;
    } else if (bestV <= epsilon && w <= epsilon) {
      normalArray = vertexNormals; normalIndex = triangles[bestFace * 3] * 3;
    } else if (bestU <= epsilon) {
      normalArray = edgeNormals; normalIndex = bestFace * 9 + 3;
    } else if (bestV <= epsilon) {
      normalArray = edgeNormals; normalIndex = bestFace * 9 + 6;
    } else if (w <= epsilon) {
      normalArray = edgeNormals; normalIndex = bestFace * 9;
    }
    const dx = x - bestX, dy = y - bestY, dz = z - bestZ;
    let nx = normalArray[normalIndex], ny = normalArray[normalIndex + 1], nz = normalArray[normalIndex + 2];
    const distance = Math.sqrt(bestDistance2);
    const sign = dx * nx + dy * ny + dz * nz < 0 ? -1 : 1;
    if (distance > 1e-12) {
      nx = sign * dx / distance; ny = sign * dy / distance; nz = sign * dz / distance;
    } else {
      const length = Math.hypot(nx, ny, nz);
      nx /= length; ny /= length; nz /= length;
    }
    result.point[0] = bestX; result.point[1] = bestY; result.point[2] = bestZ;
    result.normal[0] = nx; result.normal[1] = ny; result.normal[2] = nz;
    result.signedDistance = sign * distance; result.triangle = bestFace;
    return result;
  }

  function closestPoint(x, y, z, hintTriangle = -1) {
    return closestPointInto(x, y, z, hintTriangle, { point: [0, 0, 0], normal: [0, 0, 0], signedDistance: 0, triangle: -1 });
  }

  function projectPoint(x, y, z, clearance = .003, hintTriangle = -1, maxIterations = 24) {
    let contact = closestPoint(x, y, z, hintTriangle);
    let iterations = 0;
    while (contact.signedDistance < clearance - 1e-7 && iterations < maxIterations) {
      const correction = clearance - contact.signedDistance + 1e-7;
      x += contact.normal[0] * correction;
      y += contact.normal[1] * correction;
      z += contact.normal[2] * correction;
      contact = closestPointInto(x, y, z, contact.triangle, contact);
      iterations++;
    }
    const remainingPenetration = Math.max(0, clearance - contact.signedDistance);
    return { position: [x, y, z], contact, iterations, remainingPenetration, converged: remainingPenetration <= 1e-7 };
  }

  return { closestPoint, closestPointInto, projectPoint, positions, triangles, vertexNormals, faceNormals };
}
