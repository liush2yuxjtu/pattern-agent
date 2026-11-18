// Two developable annular sectors: dimensions are seam arc lengths in mm.
export function sector(top,bottom,length){
  const angle=(bottom-top)/length,radius=top/angle;
  return {angle,radius,at:(i,j)=>[(radius+length*j)*Math.cos((i-.5)*angle)-radius,(radius+length*j)*Math.sin((i-.5)*angle)]};
}
export function patternSVG(p){
  const {bottomMm:bottom,lengthsMm:lengths}=p,tops=p.topsMm||[p.topMm,p.topMm],W=bottom*2+120;
  const offsets=lengths.map((L,i)=>{const a=sector(tops[i],bottom,L),inner=a.radius-10;return Math.max(55,15-(inner*Math.cos(a.angle/2+Math.asin(10/inner))-a.radius));});
  const H=Math.max(...lengths.map((L,i)=>L+offsets[i]))+50;
  const groups=lengths.map((L,n)=>{
    const top=tops[n],a=sector(top,bottom,L),tx=bottom/2+25+n*(bottom+55),ty=offsets[n];
    const path=(inner,outer,angle,allowance=0)=>{
      const point=(r,phi)=>[r*Math.sin(phi),r*Math.cos(phi)-a.radius].join(' ');
      const hi=angle/2+Math.asin(allowance/inner),ho=angle/2+Math.asin(allowance/outer);
      return `M ${point(inner,-hi)} A ${inner} ${inner} 0 0 0 ${point(inner,hi)} L ${point(outer,ho)} A ${outer} ${outer} 0 0 1 ${point(outer,-ho)} Z`;
    };
    const d=path(a.radius,a.radius+L,a.angle),cut=path(a.radius-10,a.radius+L+10,a.angle,10);
    return `<g transform="translate(${tx},${ty})"><path d="${cut}" fill="#e7ebdf" stroke="#425e4b"/><path d="${d}" fill="none" stroke="#738677" stroke-dasharray="7 5"/><text x="0" y="35" text-anchor="middle" font-size="17">${n?'B 后片':'A 前片'} · CUT 1</text><text x="0" y="60" text-anchor="middle" font-size="14">${top.toFixed(1)} / ${bottom} × ${L} mm · 腰/摆弧长</text><path d="M 0 110 v ${L-220} m -8 -14 l 8 14 8 -14" stroke="#425e4b" fill="none" stroke-width="2"/></g>`;
  }).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}mm" height="${H}mm" viewBox="0 0 ${W} ${H}"><rect width="100%" height="100%" fill="#fffdf6"/>${groups}<path d="M 20 ${H-28} h 100 m -100 -5 v 10 m 100 -10 v 10" stroke="#263d37"/><text x="135" y="${H-23}" font-size="14">100 mm · 缝份 10 mm · 扇环测试纸样 / 无腰头开合结构</text></svg>`;
}
