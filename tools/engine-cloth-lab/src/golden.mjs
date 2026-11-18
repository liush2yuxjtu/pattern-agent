const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
export function goldenDrawing(golden,selected=null){
  const parts=Object.entries(golden['完整二维几何']);
  let minGX=Infinity,minGY=Infinity,maxGX=-Infinity,maxGY=-Infinity;const groups=[],bounds={};let lines=0,vertices=0,texts=0,polylines=0;
  for(const [name,part] of parts){
    const points=part['线条'].flatMap(l=>l['点位']??[l['起点'],l['终点']].filter(Boolean));
    const xs=points.map(p=>p['横']),ys=points.map(p=>p['高']),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
    const tx=part['排版放置点']['横'],ty=-part['排版放置点']['高'];
    bounds[name]={x:tx+minX,y:ty-maxY,width:maxX-minX,height:maxY-minY,sourcePlacement:part['排版放置点']};
    minGX=Math.min(minGX,tx+minX-20);maxGX=Math.max(maxGX,tx+maxX+20);minGY=Math.min(minGY,ty-maxY-35);maxGY=Math.max(maxGY,ty-minY+20);
    const content=part['线条'].map(l=>{
      const pts=l['点位']??[l['起点'],l['终点']].filter(Boolean);if(l['线型']==='折线'){polylines++;vertices+=pts.length;}else lines++;
      return `<path data-line="${escape(l['名称'])}" d="M ${pts.map(p=>`${p['横']},${-p['高']}`).join(' L ')}${l['闭合方式']==='闭合'?' Z':''}" fill="none" stroke="${selected===l['名称']?'#cf682e':l['名称'].includes('外侧')?'#ada99d':'#455b50'}" stroke-width="${selected===l['名称']?2.8:.8}"/>`;
    }).join('');
    const textSource=part['文字']??[];
    const labels=textSource.map(t=>{texts++;const p=t['位置']??t['点位']??t['放置点']??{横:0,高:0};return `<text x="${p['横']}" y="${-p['高']}" font-size="5" fill="#59655f">${escape(t['文字内容']??t['内容']??t['文字']??'')}</text>`;}).join('');
    groups.push(`<g transform="translate(${tx},${ty})"><text x="${minX}" y="${-maxY-13}" font-size="14" fill="#263e33">${escape(name)} · U</text>${content}${labels}</g>`);
  }
  return {svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="${minGX} ${minGY} ${maxGX-minGX} ${maxGY-minGY}" role="img" aria-label="Golden YAML 原始四片纸样与原排版 U">${groups.join('')}</svg>`,stats:{parts:parts.length,polylines,lines,texts,vertices},bounds};
}
