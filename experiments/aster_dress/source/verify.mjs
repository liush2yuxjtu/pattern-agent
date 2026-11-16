import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DEFAULTS,verify,offsetOutline,outline} from './model.mjs';
const variants=[DEFAULTS,{...DEFAULTS,bust:800,waist:600,hem:1800,skirt:500,allowance:6},{...DEFAULTS,bust:1200,waist:1000,hem:3200,skirt:1000,allowance:20},{...DEFAULTS,bust:1040,waist:1000,hem:1800,skirt:500,allowance:15}];
const rows=[];
for(const c of variants){const r=verify(c);assert(r.passed,'3D and 2D metric / seam coincidence test failed');for(const type of ['B','S']){const p=outline(c,type),q=offsetOutline(c,type);for(let i=0;i<p.length;i++){const j=(i+1)%p.length,a=p[i],b=p[j],m=[(q[i][0]+q[j][0])/2,(q[i][1]+q[j][1])/2],dx=b[0]-a[0],dy=b[1]-a[1],dist=Math.abs(dx*(m[1]-a[1])-dy*(m[0]-a[0]))/Math.hypot(dx,dy),expected=type==='S'&&i>=192&&i<288?25:c.allowance;assert(Math.abs(dist-expected)<1e-5,'Incorrect perpendicular cut allowance');}
for(let i=0;i<q.length;i++)for(let j=i+2;j<q.length;j++){if(i===0&&j===q.length-1)continue;const a=q[i],b=q[(i+1)%q.length],x=q[j],y=q[(j+1)%q.length],cross=(v,w,z)=>(w[0]-v[0])*(z[1]-v[1])-(w[1]-v[1])*(z[0]-v[0]);assert(!(cross(a,b,x)*cross(a,b,y)<-1e-8&&cross(x,y,a)*cross(x,y,b)<-1e-8),'Cut contour self-intersection');}}
rows.push({config:c,passed:r.passed,maxEdgeError:r.maxRelativeEdgeError,maxAreaError:r.maxAreaError,offsetDistancePassed:true,cutContourSelfIntersections:0});}
const html=fs.readFileSync('dist/index.html','utf8');assert(!/<script[^>]+src=|<link[^>]+stylesheet/.test(html),'External runtime dependency');assert(html.length<2e6,'Unexpected HTML size');
fs.writeFileSync('dist/geometry-verification.json',JSON.stringify({default:verify(),variants:rows},null,2));
console.log(`PASS: ${variants.length} drafts, ${variants.length*7680} sampled edge comparisons, ${variants.length*24} seam pairs, all cut offsets and contour intersections. Self-contained HTML ${Buffer.byteLength(html)} bytes.`);
