const axisX=.78,axisZ=.48,n=2048,step=Math.PI/2/n,cumulative=[0];
const speed=a=>Math.hypot(axisX*Math.cos(a),axisZ*Math.sin(a));
for(let i=0;i<n;i++){const a=i*step,b=a+step;cumulative.push(cumulative.at(-1)+step*(speed(a)+4*speed((a+b)/2)+speed(b))/6);}
const quarter=cumulative.at(-1);
export function ellipseSection(fraction){const sign=fraction<0?-1:1,t=Math.abs(fraction),target=t*quarter;let angle;if(t>=1)angle=Math.PI/2+(t-1)*quarter/axisZ;else{let lo=0,hi=n;while(hi-lo>1){const m=(lo+hi)>>1;if(cumulative[m]<target)lo=m;else hi=m;}angle=(lo+(target-cumulative[lo])/(cumulative[hi]-cumulative[lo]))*step;}return{x:sign*axisX/quarter*Math.sin(angle),z:axisZ/quarter*Math.cos(angle)};}
