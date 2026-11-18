const NAMES={leftShoulder:'左肩缝',rightShoulder:'右肩缝',leftSide:'左侧缝',rightSide:'右侧缝'};
export const SEAM_THRESHOLDS={lengthToleranceMM:5,gapToleranceMM:3,stretchLimit:1.2,compressionLimit:.8,seamBandMM:20,sewingTargetMM:1,lateRmsToleranceMM:.5};

const pairKey=(a,b)=>a<b?`${a}:${b}`:`${b}:${a}`;
const distance3=(p,a,b)=>Math.hypot(p[a*3]-p[b*3],p[a*3+1]-p[b*3+1],p[a*3+2]-p[b*3+2]);
const quantile=(a,q)=>a.length?a.slice().sort((a,b)=>a-b)[Math.max(0,Math.min(a.length-1,Math.ceil(q*a.length)-1))]:null;
const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:null;
function weightedQuantile(values,weights,q){
  const sorted=values.map((value,i)=>({value,weight:weights[i]})).filter(p=>Number.isFinite(p.value)&&p.weight>0).sort((a,b)=>a.value-b.value);
  const total=sorted.reduce((s,p)=>s+p.weight,0);
  if(!total)return null;
  let sum=0;for(const p of sorted){sum+=p.weight;if(sum>=q*total)return p.value;}
  return sorted.at(-1).value;
}
function pointSegmentDistance(x,y,a,b){
  const dx=b[0]-a[0],dy=b[1]-a[1],den=dx*dx+dy*dy;
  const t=den?Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/den)):0;
  return Math.hypot(x-a[0]-t*dx,y-a[1]-t*dy);
}
function pointPathDistance(x,y,ids,material){
  let d=Infinity;
  if(ids.length===1)return Math.hypot(x-material[ids[0]][0],y-material[ids[0]][1]);
  for(let i=1;i<ids.length;i++)d=Math.min(d,pointSegmentDistance(x,y,material[ids[i-1]],material[ids[i]]));
  return d;
}
function pathLength(ids,material){
  let sum=0;for(let i=1;i<ids.length;i++)sum+=Math.hypot(material[ids[i]][0]-material[ids[i-1]][0],material[ids[i]][1]-material[ids[i-1]][1]);return sum;
}
function areaSummary(indices,stretch,areas,limit,minStretch,compressionLimit){
  let area=0,sum=0,over=0,max=0,min=Infinity,compressed=0;
  const values=[],weights=[];
  for(const i of indices){const a=areas[i],v=stretch[i];if(!Number.isFinite(v)||!a)continue;area+=a;sum+=a*v;if(v>limit)over+=a;max=Math.max(max,v);if(minStretch){min=Math.min(min,minStretch[i]);if(minStretch[i]<compressionLimit)compressed+=a;}values.push(v);weights.push(a);}
  return {maxStretchPercent:area?max*100:null,areaWeightedMeanStretchPercent:area?sum/area*100:null,p95StretchPercent:area?weightedQuantile(values,weights,.95)*100:null,areaOverLimitPercent:area?over/area*100:null,areaM2:area,minStretchPercent:area&&min<Infinity?min*100:null,areaBelowCompressionLimitPercent:area?compressed/area*100:null};
}

export function analyzeSeams(pattern,positions,options={}){
  const thresholds={...SEAM_THRESHOLDS,...options};
  const vertexCount=positions.length/3;
  if(!Number.isInteger(vertexCount)||!Array.from(positions).every(Number.isFinite))throw new Error('Analysis requires finite xyz positions');
  const material=new Array(vertexCount),panelOf=new Array(vertexCount),trianglePanel=[];
  for(let pi=0;pi<pattern.panels.length;pi++)for(let i=0;i<pattern.panels[pi].points.length;i++){
    material[pattern.panels[pi].offset+i]=pattern.panels[pi].points[i];panelOf[pattern.panels[pi].offset+i]=pi;
  }
  const triangles=pattern.triangles;
  const count=triangles.length/3,triangleStretch=new Array(count),triangleMinStretch=new Array(count),triangleRestAreaM2=new Array(count),centroids=new Array(count);
  const vertexStrain=new Array(vertexCount).fill(0),vertexArea=new Array(vertexCount).fill(0);
  let invalidRestTriangles=0,collapsedTriangles=0;
  for(let ti=0;ti<count;ti++){
    const a=triangles[ti*3],b=triangles[ti*3+1],c=triangles[ti*3+2],A=material[a],B=material[b],C=material[c];
    if(!A||!B||!C)throw new Error('Triangle has no material coordinates');
    trianglePanel[ti]=panelOf[a];centroids[ti]=[(A[0]+B[0]+C[0])/3,(A[1]+B[1]+C[1])/3];
    const ux=(B[0]-A[0])*.001,uy=(B[1]-A[1])*.001,vx=(C[0]-A[0])*.001,vy=(C[1]-A[1])*.001,det=ux*vy-uy*vx;
    const area=Math.abs(det)/2;triangleRestAreaM2[ti]=area;
    if(area<1e-15){triangleStretch[ti]=null;triangleMinStretch[ti]=null;invalidRestTriangles++;continue;}
    const e1x=positions[b*3]-positions[a*3],e1y=positions[b*3+1]-positions[a*3+1],e1z=positions[b*3+2]-positions[a*3+2];
    const e2x=positions[c*3]-positions[a*3],e2y=positions[c*3+1]-positions[a*3+1],e2z=positions[c*3+2]-positions[a*3+2];
    const f0x=(e1x*vy-e2x*uy)/det,f0y=(e1y*vy-e2y*uy)/det,f0z=(e1z*vy-e2z*uy)/det;
    const f1x=(-e1x*vx+e2x*ux)/det,f1y=(-e1y*vx+e2y*ux)/det,f1z=(-e1z*vx+e2z*ux)/det;
    const aa=f0x*f0x+f0y*f0y+f0z*f0z,ab=f0x*f1x+f0y*f1y+f0z*f1z,bb=f1x*f1x+f1y*f1y+f1z*f1z;
    const disc=Math.sqrt((aa-bb)**2+4*ab*ab),hi=Math.sqrt(Math.max(0,(aa+bb+disc)/2));
    const areaRatio=Math.hypot(f0y*f1z-f0z*f1y,f0z*f1x-f0x*f1z,f0x*f1y-f0y*f1x),lo=hi>0?areaRatio/hi:0;
    triangleStretch[ti]=hi;triangleMinStretch[ti]=lo;
    if(hi*lo<1e-6)collapsedTriangles++;
    for(const id of [a,b,c]){vertexStrain[id]+=hi*area;vertexArea[id]+=area;}
  }
  for(let i=0;i<vertexCount;i++)vertexStrain[i]=vertexArea[i]?vertexStrain[i]/vertexArea[i]:1;

  const active=[];let invalidPairs=0,duplicatePairs=0;
  const seen=new Set();
  for(const pair of pattern.seams||[]){
    let [a,b]=pair;
    if(!Number.isInteger(a)||!Number.isInteger(b)||a<0||b<0||a>=vertexCount||b>=vertexCount||a===b||panelOf[a]===panelOf[b]){invalidPairs++;continue;}
    if(panelOf[a]>panelOf[b])[a,b]=[b,a];
    const key=pairKey(a,b);if(seen.has(key))duplicatePairs++;seen.add(key);active.push({a,b,key});
  }
  const groups=Object.entries(pattern.seamGroups||{}),claimed=new Set(),perSeam=[];
  for(let gi=0;gi<groups.length;gi++){
    const [key,expectedPairs]=groups[gi];
    const aPath=[...new Set(expectedPairs.map(p=>p[0]))],bPath=[...new Set(expectedPairs.map(p=>p[1]))];
    const aRank=new Map(aPath.map((id,i)=>[id,i])),bRank=new Map(bPath.map((id,i)=>[id,i]));
    const expectedKeys=new Set(expectedPairs.map(p=>pairKey(...p)));
    const records=active.filter(r=>aRank.has(r.a)||bRank.has(r.b));
    for(const r of records)claimed.add(r.key);
    const sorted=records.slice().sort((a,b)=>(aRank.get(a.a)??Infinity)-(aRank.get(b.a)??Infinity));
    const missing=expectedPairs.filter(pair=>!seen.has(pairKey(...pair))).length;
    const unexpected=records.filter(r=>!expectedKeys.has(r.key)).length;
    const repeatedA=records.length-new Set(records.map(r=>r.a)).size,repeatedB=records.length-new Set(records.map(r=>r.b)).size;
    const directions=sorted.map(r=>bRank.get(r.b));
    const directionOrderPass=sorted.length>=2&&sorted.every(r=>aRank.has(r.a)&&bRank.has(r.b))&&directions.every((rank,i)=>i===0||rank>directions[i-1]);
    const endpointsPass=sorted.length>=2&&sorted[0].a===aPath[0]&&sorted[0].b===bPath[0]&&sorted.at(-1).a===aPath.at(-1)&&sorted.at(-1).b===bPath.at(-1);
    const pairingPass=expectedPairs.length>=2&&missing===0&&unexpected===0&&repeatedA===0&&repeatedB===0&&directionOrderPass&&endpointsPass;
    const aMM=pathLength(aPath,material),bMM=pathLength(bPath,material),differenceMM=Math.abs(aMM-bMM);
    const gaps=records.map(r=>distance3(positions,r.a,r.b)*1000),residuals=gaps.map(v=>Math.abs(v-thresholds.sewingTargetMM));
    const bandIndices=[];
    for(let ti=0;ti<count;ti++){
      const pi=trianglePanel[ti],path=pi===panelOf[aPath[0]]?aPath:pi===panelOf[bPath[0]]?bPath:null;
      if(path&&pointPathDistance(...centroids[ti],path,material)<=thresholds.seamBandMM)bandIndices.push(ti);
    }
    const strain=areaSummary(bandIndices,triangleStretch,triangleRestAreaM2,thresholds.stretchLimit,triangleMinStretch,thresholds.compressionLimit);
    const gapMax=gaps.length?Math.max(...gaps):null;
    const lengthStatus=differenceMM<=thresholds.lengthToleranceMM?'PASS':'FAIL';
    const gapStatus=gapMax===null?'UNKNOWN':gapMax<=thresholds.gapToleranceMM?'PASS':'FAIL';
    const bandInvalidRestTriangles=bandIndices.filter(i=>triangleStretch[i]===null).length;
    const strainExtensionStatus=bandInvalidRestTriangles||!strain.areaM2?'UNKNOWN':strain.maxStretchPercent>thresholds.stretchLimit*100?'REVIEW':'PASS';
    const strainCompressionStatus=bandInvalidRestTriangles||!strain.areaM2?'UNKNOWN':strain.areaBelowCompressionLimitPercent>0?'REVIEW':'PASS';
    const strainStatus=strainExtensionStatus==='UNKNOWN'||strainCompressionStatus==='UNKNOWN'?'UNKNOWN':strainExtensionStatus==='REVIEW'||strainCompressionStatus==='REVIEW'?'REVIEW':'PASS';
    const samples=records.map(r=>({a:r.a,b:r.b,gapMM:distance3(positions,r.a,r.b)*1000,rankA:aRank.get(r.a)??null,rankB:bRank.get(r.b)??null,expected:expectedKeys.has(r.key)}));
    perSeam.push({id:`S${gi+1}`,key,name:NAMES[key]||key,paths:{a:aPath,b:bPath},
      length:{aMM,bMM,differenceMM,ratioPercent:Math.max(aMM,bMM)?differenceMM/Math.max(aMM,bMM)*100:0,status:lengthStatus},
      pairing:{expected:expectedPairs.length,active:records.length,missing,unexpected,repeatedA,repeatedB,directionOrderPass,endpointsPass,status:pairingPass?'PASS':'FAIL'},
      gap:{meanMM:mean(gaps),p95MM:quantile(gaps,.95),p95Method:'inverse empirical CDF nearest rank: sorted[ceil(0.95*n)-1]; unweighted pair gaps',sampleCount:gaps.length,maxMM:gapMax,targetMM:thresholds.sewingTargetMM,residualMeanMM:mean(residuals),residualMaxMM:residuals.length?Math.max(...residuals):null,status:gapStatus},
      strain:{...strain,status:strainStatus,extensionStatus:strainExtensionStatus,compressionStatus:strainCompressionStatus,invalidRestTriangles:bandInvalidRestTriangles,bandMM:thresholds.seamBandMM,bandRule:'rest-space triangle centroid within band of seam path'},
      samples,triangleIndices:bandIndices,status:!pairingPass||lengthStatus==='FAIL'||gapStatus==='FAIL'?'FAIL':strainStatus==='UNKNOWN'||gapStatus==='UNKNOWN'?'UNKNOWN':strainStatus==='REVIEW'?'REVIEW':'PASS'});
  }
  const allIndices=Array.from({length:count},(_,i)=>i),strain=areaSummary(allIndices,triangleStretch,triangleRestAreaM2,thresholds.stretchLimit,triangleMinStretch,thresholds.compressionLimit);
  const peakIndices=allIndices.filter(i=>Number.isFinite(triangleStretch[i])).sort((a,b)=>triangleStretch[b]-triangleStretch[a]).slice(0,8);
  const peaks=peakIndices.map(i=>{
    const ids=Array.from(triangles.slice(i*3,i*3+3));
    return {triangleIndex:i,panelIndex:trianglePanel[i],panelName:pattern.panels[trianglePanel[i]].name||`Panel ${trianglePanel[i]+1}`,materialCentroidMM:centroids[i],positionM:[0,1,2].map(k=>ids.reduce((s,id)=>s+positions[id*3+k],0)/3),stretchPercent:triangleStretch[i]*100,restAreaMM2:triangleRestAreaM2[i]*1e6};
  });
  let penetratingVertices=null;
  if(pattern.body?.collider){penetratingVertices=0;for(let i=0;i<vertexCount;i++)if(pattern.body.collider.contains(positions[i*3],positions[i*3+1],positions[i*3+2],-1e-5))penetratingVertices++;}
  const unassignedPairs=active.filter(r=>!claimed.has(r.key)).length;
  const hasSeams=perSeam.length>0;
  const matchingStatus=!hasSeams?'NOT_APPLICABLE':invalidPairs||duplicatePairs||unassignedPairs||perSeam.some(s=>s.pairing.status==='FAIL')?'FAIL':'PASS';
  const lengthStatus=!hasSeams?'NOT_APPLICABLE':perSeam.some(s=>s.length.status==='FAIL')?'FAIL':'PASS';
  const closureStatus=!hasSeams?'NOT_APPLICABLE':perSeam.some(s=>s.gap.status==='FAIL')?'FAIL':perSeam.some(s=>s.gap.status==='UNKNOWN')?'UNKNOWN':'PASS';
  const extensionStatus=invalidRestTriangles||!strain.areaM2?'UNKNOWN':strain.maxStretchPercent>thresholds.stretchLimit*100?'REVIEW':'PASS';
  const compressionStatus=invalidRestTriangles||!strain.areaM2?'UNKNOWN':strain.areaBelowCompressionLimitPercent>0||collapsedTriangles?'REVIEW':'PASS';
  const summary={verdict:!hasSeams?'NOT_APPLICABLE':matchingStatus==='FAIL'||lengthStatus==='FAIL'||closureStatus==='FAIL'||penetratingVertices>0||invalidRestTriangles?'FAIL':extensionStatus==='REVIEW'||compressionStatus==='REVIEW'?'REVIEW_REQUIRED':extensionStatus==='UNKNOWN'?'UNKNOWN':'LIMITED_CHECKS_PASS',
    lengths:lengthStatus,pairing:matchingStatus,closure:closureStatus,geometricExtension:extensionStatus,geometricCompression:compressionStatus,vertices:vertexCount,triangles:count,seamGroups:perSeam.length,seamPairs:active.length,invalidPairs,duplicatePairs,unassignedPairs,invalidRestTriangles,collapsedTriangles,
    maxGapMM:hasSeams?Math.max(...perSeam.map(s=>s.gap.maxMM??0)):null,
    vertexCollision:{checked:penetratingVertices===null?0:vertexCount,penetrating:penetratingVertices,status:penetratingVertices===null?'UNKNOWN':penetratingVertices?'FAIL':'PASS',scope:'discrete body-mesh vertex checks only'},
    strain,peaks,unknown:['calibrated fabric stretch limit','physical stress in kPa','cloth self collision','edge and face collision','moving-avatar motion test','mesh refinement convergence','real seam strength and real fit']};
  return {schema:'pattern-lab-seam-analysis-1',thresholds:{...SEAM_THRESHOLDS,...options,meaning:{lengthToleranceMM:'CLO Check Sewing Length document default; flags source 2D length difference, not 3D closure',gapToleranceMM:'project research screen, not a CLO acceptance limit',stretchLimit:'project geometric screen; not calibrated Fabric mode',compressionLimit:'project geometric compression screen, not a CLO limit',sewingTargetMM:'distance-constraint solver target',lateRmsToleranceMM:'project still-avatar drift screen'}},summary,perSeam,triangleStretch,triangleMinStretch,triangleRestAreaM2,vertexStrain,
    limitations:['Maximum principal stretch from material-space F^T F; not CLO warp/weft/bias fabric-limit output','Direction compares actual constraints to the generator seam path/notch manifest; external CAD intent is not independently certified','Rest-space area weights; tiny stretched triangles are still reported as peaks','0 penetrating vertices does not prove no surface penetration','Fixed shoulder supports remain active']};
}
