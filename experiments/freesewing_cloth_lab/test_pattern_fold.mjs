import assert from 'node:assert/strict';
import {Sandy} from '@freesewing/sandy';
import {draftSandy} from './source/freesewing-pattern.js';
import {buildHinges,foldFields} from './source/fold-fields.js';

const close=(a,b,tol=1e-9)=>assert.ok(Math.abs(a-b)<tol,`${a} != ${b}`);
const reports={};
const base={waist_mm:736.3414168681662,length_mm:560,circleRatio:.387547980686};
for(const [name,params] of Object.entries({default:base,longer:{...base,length_mm:650},wider:{...base,circleRatio:.6}})){
 const d=draftSandy(params),native=new Sandy({sa:10,measurements:{waist:params.waist_mm,hips:1000,waistToFloor:1000,waistToHips:200},options:{panels:4,waistbandPosition:0,waistbandShape:'straight',waistbandWidth:.02,lengthBonus:(params.length_mm+20)/1000,circleRatio:params.circleRatio,gathering:0,seamlessFullCircle:false}}).draft();
 const p=native.parts[0]['sandy.skirt'].points,center=p.center;
 const a=d.sample(0,1),b=d.sample(1,1);
 close(a[0],p.in2.x-center.x);close(a[1],p.in2.y-p.in2Flipped.y);
 close(b[0],p.ex2.x-center.x);close(b[1],p.ex2.y-p.in2Flipped.y);
 close(Math.hypot(b[0]-a[0],b[1]-a[1]),params.length_mm);
 assert.ok(Math.hypot(...d.sample(1,17/16).map((v,k)=>v-d.sample(1,1)[k]))>1);
 assert.match(d.nativeSVG,/<svg/);assert.ok(d.nativeSVG.length>10000);
 reports[name]={length_mm:d.profile.sideLength_mm,sourceHalfPanelEndpoint_mm:[p.ex2.x,p.ex2.y],unfoldedEndpoint_mm:b};
}
assert.notDeepEqual(reports.default.unfoldedEndpoint_mm,reports.longer.unfoldedEndpoint_mm);
assert.notDeepEqual(reports.default.unfoldedEndpoint_mm,reports.wider.unfoldedEndpoint_mm);

const triangles=[0,1,2,1,0,3],uvs=[0,0,1,0,0,1,1,0,0,0,0,-1],hinges=buildHinges(triangles,uvs);
assert.equal(hinges.length,1);
const points=theta=>[0,0,0,1,0,0,0,1,0,0,-Math.cos(theta),Math.sin(theta)];
const flat=foldFields(points(0),triangles,hinges);close(flat.angle_rad[0],0);close(flat.curvature_per_m[0],0);
const angle=Math.PI/3,pos=foldFields(points(angle),triangles,hinges),neg=foldFields(points(-angle),triangles,hinges);
close(pos.angle_rad[0],-angle);close(neg.angle_rad[0],angle);close(pos.currentDualLength_m[0],2/3);close(pos.curvature_per_m[0],-Math.PI/2);
const moved=points(angle).map((_,i)=>{const q=points(angle),j=i-i%3;return i%3===0?-q[j+1]+3:i%3===1?q[j]+4:q[i]-5;});
close(foldFields(moved,triangles,hinges).angle_rad[0],pos.angle_rad[0]);
const scaled=foldFields(points(angle).map(x=>x*2),triangles,hinges);close(scaled.angle_rad[0],pos.angle_rad[0]);close(scaled.curvature_per_m[0],pos.curvature_per_m[0]/2);
reports.foldControls={flat:true,positiveAndNegative60deg:true,rigidMotionInvariant:true,spatialScaling:true,knownCurvature_per_m:pos.curvature_per_m[0]};
reports.verdict='PASS';console.log(JSON.stringify(reports,null,2));
