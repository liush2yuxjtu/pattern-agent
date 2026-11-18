// The upper edge must fit the measured avatar, as well as clear collisions.
export function wearDiagnostics(positions,distances,p,fit){
  const n=16,k=425;let gapMin=Infinity,gapMax=-Infinity,error=0;const lengths=[];
  for(let panel=0;panel<2;panel++){
    let length=0;
    for(let i=0;i<=n;i++){
      const v=panel*k+i,target=fit.waistPanelsM[panel][i];
      error=Math.max(error,Math.hypot(positions[3*v]-target[0]-p.bodyOffsetMm/1000,positions[3*v+1]-target[1],positions[3*v+2]-target[2])*1000);
      gapMin=Math.min(gapMin,distances[v]*1000);gapMax=Math.max(gapMax,distances[v]*1000);
      if(i){const a=3*(v-1),b=3*v;length+=Math.hypot(positions[b]-positions[a],positions[b+1]-positions[a+1],positions[b+2]-positions[a+2])*1000;}
    }
    lengths.push(length);
  }
  const lengthError=Math.max(...lengths.map((v,i)=>Math.abs(v-p.topsMm[i])));
  return {maxWaistGapMm:gapMax,minWaistGapMm:gapMin,maxWaistPlacementErrorMm:error,waistEdgeLengthsMm:lengths,waistPatternMismatchMm:lengthError,
    bodySectionGirthMm:fit.bodySectionGirthMm,garmentWaistMm:p.topsMm[0]+p.topsMm[1],sectionHeightM:fit.sectionHeightM,
    fitted:[gapMin,gapMax,error,lengthError].every(Number.isFinite)&&gapMin>=3&&gapMax<=10&&error<=1&&lengthError<=1};
}
