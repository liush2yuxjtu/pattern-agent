import { Carlton } from '@freesewing/carlton'
import { plugin as theme } from '@freesewing/plugin-theme'
import source from './joost.json'
import standard from '../page-carlton-inputs/standard-m.json'

const settings = source.settings
export const frontLength = pattern => {
  const {cfHem,hps,s3CollarSplit} = pattern.parts[0]['carlton.front'].points
  return cfHem.y - (hps??s3CollarSplit).y
}
const draft = (chest,length,layout) => {
  const pattern = new Carlton({
    ...settings, measurements: {...settings.measurements,chest},
    options:{length}, sa:0, layout,
  })
  if (layout) pattern.use(theme)
  return pattern.draft()
}

const standardRatio = 0.69
const original = draft(settings.measurements.chest, standardRatio, false)

function sample(path) {
  const points = []
  let from, start
  for (const {type,to,cp1,cp2} of path.ops) {
    if (type === 'move') {
      start = from = to
      points.push([to.x,to.y])
      continue
    }
    if (type === 'close') {
      points.push([start.x,start.y])
      from = start
      continue
    }
    if (type === 'curve') {
      for (let i=1;i<=18;i++) {
        const t=i/18, s=1-t
        points.push(['x','y'].map(axis => s**3*from[axis]+3*s*s*t*cp1[axis]+3*s*t*t*cp2[axis]+t**3*to[axis]))
      }
    } else {
      points.push([to.x,to.y])
    }
    from = to
  }
  return points
}

const outline = (pattern,part) => sample(pattern.parts[0]['carlton.'+part].paths.seam)
export const originalOutline = part => outline(original,part)

const frontPoints = pattern => pattern.parts[0]['carlton.front'].points
export const forAssembly = pattern => ({
  outline:part=>outline(pattern,part),
  front:frontPoints(pattern),
})

export const baselineDraft = forAssembly(new Carlton({...standard,options:{},sa:0,layout:false}).draft())
