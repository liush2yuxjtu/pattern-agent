import { Teagan } from '@freesewing/teagan'
import { cisFemaleAdult38 } from './package/src/index.mjs'
import { writeFileSync } from 'node:fs'
const p = new Teagan({ measurements: cisFemaleAdult38, options: {fitWaist: true, sleeveLength: 1}, sa: 0, complete: false}).draft()
console.log('model',cisFemaleAdult38)
console.log('required',Teagan.patternConfig.measurements)
console.log('keys',Object.keys(p), 'parts',Object.keys(p.parts??{}))
for(const [i,set] of Object.entries(p.parts??{})) {
console.log(i, Object.keys(set));
for(const [name,part] of Object.entries(set)) if(name.startsWith('teagan')) console.log(name, Object.keys(part), 'points',Object.keys(part.points), 'seam',JSON.stringify(part.paths.seam?.ops), 'store',JSON.stringify(part.store))
}
writeFileSync('probes/pattern/native-teagan.svg',p.render())
