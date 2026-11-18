// Surface metric relative to the unstrained 2D net pattern, in meters.
// This measures the displayed geometry, not a cloth constitutive model or stress.
export const heatMetrics={
 maxStrain:{label:'最大主拉伸',unit:'%',description:'两条主方向中较大的长度变化；负值表示该处两个方向均压缩。'},
 minStrain:{label:'最小主拉伸',unit:'%',description:'两条主方向中较小的长度变化；用于查看压缩。'},
 area:{label:'面积变化',unit:'%',description:'三维三角形面积相对二维净样的变化。'},
 shear:{label:'布纹剪切',unit:'°',description:'当前布纹及其垂直方向映射后偏离直角的量；正负表示剪切方向。'}
};
const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0),sub=(a,b)=>a.map((x,i)=>x-b[i]);
export function triangleDeformation(rest,current,kernel,grainAngle=0){
 const a=sub(rest[1],rest[0]),b=sub(rest[2],rest[0]),det=a[0]*b[1]-b[0]*a[1];
 const restArea=Math.abs(det)/2;
 if(!Number.isFinite(det)||Math.abs(det)<1e-16)return{valid:false,restArea,reason:'degenerate-rest-triangle'};
 const lengths=[Math.hypot(...a),Math.hypot(...b),Math.hypot(...sub(rest[2],rest[1]))];
 let minAngle=Math.PI;for(let i=0;i<3;i++){const u=sub(rest[(i+1)%3],rest[i]),v=sub(rest[(i+2)%3],rest[i]);minAngle=Math.min(minAngle,Math.atan2(Math.abs(u[0]*v[1]-u[1]*v[0]),dot(u,v)));}
 const referenceAspectRatio=Math.max(...lengths)**2/Math.abs(det),quality={referenceMinAngleDeg:minAngle*180/Math.PI,referenceAspectRatio,meshSensitive:referenceAspectRatio>50};
 const u=sub(current[1],current[0]),v=sub(current[2],current[0]);
 const fx=u.map((x,i)=>(x*b[1]-v[i]*a[1])/det),fy=u.map((x,i)=>(v[i]*a[0]-x*b[0])/det);
 const c00=dot(fx,fx),c01=dot(fx,fy),c11=dot(fy,fy);
 const disc=Math.hypot(c00-c11,2*c01),lo=Math.max(0,(c00+c11-disc)/2),hi=Math.max(0,(c00+c11+disc)/2);
 const max=kernel?.principal_max?kernel.principal_max(c00,c01,c11):Math.sqrt(hi);
 const min=kernel?.principal_min?kernel.principal_min(c00,c01,c11):Math.sqrt(lo);
 if(min<1e-6)return{valid:false,restArea,...quality,maxStrain:(max-1)*100,minStrain:(min-1)*100,area:(max*min-1)*100,shear:null,collapsed:true,reason:'collapsed-current-triangle'};
 const theta=grainAngle*Math.PI/180,co=Math.cos(theta),si=Math.sin(theta);
 const along=c00*co*co+2*c01*co*si+c11*si*si,across=c00*si*si-2*c01*co*si+c11*co*co,cross=(c11-c00)*co*si+c01*(co*co-si*si);
 const angle=Math.atan2(Math.sqrt(Math.max(0,along*across-cross*cross)),cross);
 const result={valid:true,restArea,...quality,maxStrain:(max-1)*100,minStrain:(min-1)*100,area:(max*min-1)*100,shear:90-angle*180/Math.PI,collapsed:min<1e-6};
 if(!Object.values(result).every(v=>typeof v!=='number'||Number.isFinite(v)))return{valid:false,restArea,reason:'nonfinite-deformation'};
 return result;
}
// Fixed diverging scale: blue compression, neutral near zero, orange/red extension.
export function heatRgb(value,range=30){
 if(!Number.isFinite(value))return[.48,.45,.53];
 const t=Math.max(-1,Math.min(1,value/range)),stops=t<0?[[.12,.33,.68],[.35,.69,.78],[.91,.94,.86]]:[[.91,.94,.86],[.98,.69,.26],[.78,.13,.17]];
 const n=(t<0?t+1:t)*2,i=Math.min(1,Math.floor(n)),f=n-i;
 return stops[i].map((x,k)=>x+(stops[i+1][k]-x)*f);
}
export const heatHex=(value,range)=>'#'+heatRgb(value,range).map(v=>Math.round(v*255).toString(16).padStart(2,'0')).join('');
export function summarizeDeformation(faces,metric='maxStrain',range=30){
 const valid=faces.filter(f=>f.valid),area=valid.reduce((s,f)=>s+f.restArea,0);
 if(!valid.length)return{metric,unit:heatMetrics[metric].unit,validFaces:0,invalidFaces:faces.length,min:null,max:null,mean:null,p95:null,saturatedAreaPercent:0,collapsedFaces:faces.filter(f=>f.collapsed).length,meshSensitiveFaces:0,meshSensitiveAreaPercent:0};
 let sum=0,low=Infinity,high=-Infinity,sat=0;for(const f of valid){const v=f[metric];sum+=v*f.restArea;low=Math.min(low,v);high=Math.max(high,v);if(Math.abs(v)>range)sat+=f.restArea;}
 const sorted=valid.slice().sort((a,b)=>a[metric]-b[metric]);let cumulative=0,p95=sorted.at(-1)[metric];for(const f of sorted){cumulative+=f.restArea;if(cumulative>=area*.95){p95=f[metric];break;}}
 const sensitive=valid.filter(f=>f.meshSensitive);
 return{metric,unit:heatMetrics[metric].unit,validFaces:valid.length,invalidFaces:faces.length-valid.length,min:low,max:high,mean:sum/area,p95,restAreaM2:area,saturatedAreaPercent:sat/area*100,collapsedFaces:faces.filter(f=>f.collapsed).length,meshSensitiveFaces:sensitive.length,meshSensitiveAreaPercent:sensitive.reduce((s,f)=>s+f.restArea,0)/area*100};
}
