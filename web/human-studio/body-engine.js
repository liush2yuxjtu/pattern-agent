// Original dimension calibration for the CC0 MakeHuman mesh and morph assets.
export const DEFAULT_DIMENSIONS = Object.freeze({height:170,bust:90,waist:70,hips:96,shoulders:37,upperArm:27,thigh:54,neck:32,upperArmLength:29,forearmLength:23,thighLength:40,calf:36});
export const MODEL_VERSION = 'makehuman-cm-rig-v1';

export function normalizeDimensions(data, values = {}) {
  return Object.fromEntries(data.controls.map(c => {
    const value = typeof values[c.key] === 'number' && Number.isFinite(values[c.key]) ? values[c.key] : DEFAULT_DIMENSIONS[c.key];
    return [c.key, Math.round(Math.max(c.min, Math.min(c.max, value))*10)/10];
  }));
}

export function buildRestVertices(data, weights) {
  const positions = new Float64Array(data.vertices);
  data.controls.forEach((control, i) => {
    const value = weights[i] || 0;
    if (!value) return;
    const rows = value >= 0 ? control.incr : control.decr;
    const magnitude = Math.abs(value);
    for (const [index, x, y, z] of rows) {
      positions[index*3] += x*magnitude;
      positions[index*3+1] += y*magnitude;
      positions[index*3+2] += z*magnitude;
    }
  });
  let floor = Infinity;
  for (const index of data.bodyVertexIds) floor = Math.min(floor, positions[index*3+1]);
  for (let i=1; i<positions.length; i+=3) positions[i] -= floor;
  return positions;
}

export function measureRest(data, positions) {
  const result = {};
  for (const control of data.controls) {
    let value=0;
    if (control.key==='height') {
      let min=Infinity,max=-Infinity;
      for (const index of data.bodyVertexIds) {min=Math.min(min,positions[index*3+1]);max=Math.max(max,positions[index*3+1]);}
      value=max-min;
    } else {
      for (let i=1; i<control.path.length; i++) {
        const a=control.path[i-1]*3,b=control.path[i]*3;
        value+=Math.hypot(positions[a]-positions[b],positions[a+1]-positions[b+1],positions[a+2]-positions[b+2]);
      }
    }
    result[control.key]=value;
  }
  return result;
}

function linearSolve(matrix, rhs) {
  const n=rhs.length,a=matrix.map((row,i)=>[...row,rhs[i]]);
  for(let i=0;i<n;i++) {
    let pivot=i;
    for(let k=i+1;k<n;k++) if(Math.abs(a[k][i])>Math.abs(a[pivot][i])) pivot=k;
    [a[i],a[pivot]]=[a[pivot],a[i]];
    if(Math.abs(a[i][i])<1e-12) return null;
    const scale=a[i][i];for(let j=i;j<=n;j++) a[i][j]/=scale;
    for(let k=0;k<n;k++) if(k!==i) {const scale2=a[k][i];for(let j=i;j<=n;j++) a[k][j]-=scale2*a[i][j];}
  }
  return a.map(row=>row[n]);
}

export function fitDimensions(data, values, initialWeights, maxIterations=16) {
  const targets=normalizeDimensions(data,values),n=data.controls.length,keys=data.controls.map(c=>c.key);
  let weights=initialWeights?.length===n ? Array.from(initialWeights,v=>Number.isFinite(v)?Math.max(-2,Math.min(2,v)):0) : Array(n).fill(0);
  const evaluate=w=>{const positions=buildRestVertices(data,w),measurements=measureRest(data,positions);const residual=keys.map(k=>targets[k]-measurements[k]);return {positions,measurements,residual,error:residual.reduce((a,b)=>a+b*b,0)};};
  let current=evaluate(weights),iterations=0;
  for(;iterations<maxIterations;iterations++) {
    if(Math.max(...current.residual.map(Math.abs))<0.025) break;
    const columns=[];
    for(let j=0;j<n;j++) {
      const step=weights[j]>1.98?-0.004:0.004,w=weights.slice();w[j]+=step;
      const probe=evaluate(w);columns.push(keys.map(k=>(probe.measurements[k]-current.measurements[k])/step));
    }
    const normal=Array.from({length:n},(_,j)=>Array.from({length:n},(_,k)=>columns[j].reduce((sum,v,i)=>sum+v*columns[k][i],0)+(j===k?0.015:0)));
    const rhs=columns.map(col=>col.reduce((sum,v,i)=>sum+v*current.residual[i],0)),delta=linearSolve(normal,rhs);
    if(!delta) break;
    let improved=false;
    for(const fraction of [1,.5,.25,.1,.03]) {
      const candidate=weights.map((v,i)=>Math.max(-2,Math.min(2,v+fraction*delta[i]))),trial=evaluate(candidate);
      if(Number.isFinite(trial.error)&&trial.error<current.error-1e-10) {weights=candidate;current=trial;improved=true;break;}
    }
    if(!improved) break;
  }
  return {...current,targets,weights,iterations,maxError:Math.max(...current.residual.map(Math.abs))};
}

export function jointPosition(data, positions, name) {
  const ids=data.joints[name];
  if(!ids?.length) throw new Error('Missing anatomical joint '+name);
  const value=[0,0,0];for(const index of ids) for(let axis=0;axis<3;axis++) value[axis]+=positions[index*3+axis]/ids.length;
  return value;
}
