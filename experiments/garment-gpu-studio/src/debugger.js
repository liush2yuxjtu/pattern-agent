export function verdict(metrics,seams){const checks=[
  {id:'finite',name:'坐标有限',status:metrics.finite?'PASS':'FAIL',value:metrics.finite},
  {id:'seams',name:'缝合关系及间隙 ≤ 2 mm',status:seams.status,value:seams.maxGapMm,unit:'mm'},
  {id:'body',name:'人体内部顶点 = 0',status:metrics.penetratingVertices===0?'PASS':'FAIL',value:metrics.penetratingVertices},
  {id:'samples',name:'内部边中点/面心 = 0',status:metrics.fullCollision?(metrics.penetratingSamples===0?'PASS':'FAIL'):'NOT_RUN',value:metrics.penetratingSamples},
  {id:'strain',name:'三角面主应变 p95 ≤ 10%',status:metrics.strainP95<=.1?'PASS':'FAIL',value:metrics.strainP95*100,unit:'%'},
  {id:'maxStrain',name:'最大主应变 ≤ 25%',status:metrics.strainMax<=.25?'PASS':'FAIL',value:metrics.strainMax*100,unit:'%'},
  {id:'bodyFaces',name:'人体三角面横穿 = 0',status:metrics.fullCollision?(metrics.bodyFaceCrossings===0?'PASS':'FAIL'):'NOT_RUN',value:metrics.bodyFaceCrossings},
  {id:'self',name:'布料三角面横穿 = 0',status:metrics.fullCollision?(metrics.selfFaceCrossings===0?'PASS':'FAIL'):'NOT_RUN',value:metrics.selfFaceCrossings},
  {id:'ccd',name:'连续碰撞 CCD',status:'NOT_RUN',value:null},
  {id:'calibration',name:'真实面料/真人合身',status:'NOT_RUN',value:null},
];return {geometry:checks.slice(0,8).some(x=>x.status==='FAIL')?'FAIL':checks.slice(0,8).some(x=>x.status==='NOT_RUN')?'NOT_RUN':'PASS',physicalFit:'NOT_RUN',checks};}
export function selectByRay(raycaster,mesh,model){const hit=raycaster.intersectObject(mesh)[0];if(!hit)return null;const ids=[hit.face.a,hit.face.b,hit.face.c];return {triangle:hit.faceIndex,vertex:ids[0],node:model.map[ids[0]],position:hit.point.toArray()};}
