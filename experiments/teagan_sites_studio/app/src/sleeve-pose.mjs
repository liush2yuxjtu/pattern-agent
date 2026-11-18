// Geometric endpoint constraints for the preview. No material or contact solve.
export function solveSleevePose({shoulder,underarm,radius,length,sideLength}){
 const distance=a=>Math.hypot(shoulder.x-underarm.x+Math.cos(a)*length-2*Math.sin(a)*radius,shoulder.y-underarm.y-Math.sin(a)*length-2*Math.cos(a)*radius);
 const error=a=>distance(a)-sideLength;
 const candidates=[];let best={angle:0,error:Math.abs(error(0))};
 for(let i=1;i<=180;i++){
  const a=(i-1)*Math.PI/360,b=i*Math.PI/360,ea=error(a),eb=error(b);
  if(Math.abs(eb)<best.error)best={angle:b,error:Math.abs(eb)};
  if(ea*eb<=0){let lo=a,hi=b;for(let j=0;j<50;j++){const mid=(lo+hi)/2;if(error(lo)*error(mid)<=0)hi=mid;else lo=mid;}candidates.push((lo+hi)/2);}
 }
 const preferred=50*Math.PI/180;
 const angle=candidates.length?candidates.sort((a,b)=>Math.abs(a-preferred)-Math.abs(b-preferred))[0]:best.angle;
 return{angle,angleDegrees:angle*180/Math.PI,targetSideChordM:sideLength,actualSideChordM:distance(angle),sideChordResidualMm:Math.abs(error(angle))*1000,rootFound:candidates.length>0,meetsEndpointConstraints:Math.abs(error(angle))<1e-6,inputs:{shoulderM:[shoulder.x,shoulder.y,shoulder.z||0],underarmM:[underarm.x,underarm.y,underarm.z||0],radiusM:radius,centerlineLengthM:length,sideChordM:sideLength},method:'Preserve centerline length and mean underarm-to-cuff chord; select root closest to reference A-pose'};
}
