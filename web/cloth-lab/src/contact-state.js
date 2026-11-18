const view=(w,p,n)=>new Float32Array(w.memory.buffer,p,n);
export function capturePressure(w,nv,nt){
  if(!w.pressure_valid())return {valid:false,samples:new Float32Array()};
  const start=w.pressure_face_start(),lambda=view(w,w.pressure_lambda_ptr(),start+nt),normal=view(w,w.pressure_normal_ptr(),(start+nt)*3),rows=[];
  for(let j=0;j<nv+nt;j++){const slot=j<nv?j:start+j-nv;if(lambda[slot]>0)rows.push(slot,lambda[slot],...normal.subarray(slot*3,slot*3+3));}
  return {valid:true,samples:new Float32Array(rows)};
}
export function restorePressure(w,packet){
  w.pressure_clear();const start=w.pressure_face_start(),n=start+1536;
  const lambda=view(w,w.pressure_lambda_ptr(),n),normal=view(w,w.pressure_normal_ptr(),n*3);
  for(let j=0;j<packet.samples.length;j+=5){const slot=packet.samples[j];lambda[slot]=packet.samples[j+1];normal.set(packet.samples.subarray(j+2,j+5),slot*3);}
  w.pressure_restore(+packet.valid);
}
export function pressureData(w,nv,nt){
  const s=view(w,w.pressure_summary_ptr(),16),packet=capturePressure(w,nv,nt),start=w.pressure_face_start();
  const contacts=packet.valid?{vertex:[],centroid:[]}:null;
  for(let j=0;j<packet.samples.length;j+=5){const a=Array.from(packet.samples.subarray(j,j+5));if(a[0]>=start){a[0]-=start;contacts.centroid.push(a);}else contacts.vertex.push(a);}
  return {packet,contacts,fields:{model:'unilateral-XPBD-normal-contact',calibration:'synthetic-interface-not-measured',dtSeconds:w.pressure_dt(),referenceSpringPaPerM:w.pressure_stiffness(),nominalOffsetM:w.pressure_margin(),faceGuardOffsetM:w.pressure_margin()/2,
    nominalClothAreaPressurePa:Array.from(view(w,w.pressure_ptr(),nv)),nodalAreaM2:Array.from(view(w,w.pressure_area_ptr(),nv)),nodalNormalForceN:Array.from(view(w,w.pressure_force_ptr(),nv))},
    summary:{ready:!!s[0],frame:s[0]?s[9]:null,normalForceN:s[1],resultantOnClothN:Array.from(s.subarray(2,5)),maxPressurePa:s[5],loadedAreaM2:s[6],clothAreaM2:s[7],contactSamples:s[8],maxConstraintResidualMm:s[10]*1000,minNormalAlignment:s[11],finite:!!s[12],consistent:!!s[13]}};
}
