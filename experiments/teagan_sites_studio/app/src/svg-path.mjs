// Serialize geometry without the upstream display formatter's two-decimal rounding.
// Precision concerns file representation, not a claim about physical manufacturing accuracy.
export function precisePathString(ops){const number=v=>{if(!Number.isFinite(v))throw Error('SVG 坐标不是有效数值');const n=Number(v.toFixed(6));return Object.is(n,-0)?'0':String(n);},point=p=>number(p.x)+','+number(p.y);return ops.map(o=>o.type==='move'?'M '+point(o.to):o.type==='line'?'L '+point(o.to):o.type==='curve'?'C '+point(o.cp1)+' '+point(o.cp2)+' '+point(o.to):o.type==='close'?'z':'').filter(Boolean).join(' ');}
