import {Carlton} from '@freesewing/carlton';
import {cisMaleAdult38} from '@freesewing/models';
import {pluginTheme} from '@freesewing/plugin-theme';
import {writeFile} from 'node:fs/promises';

const [mode, projectPath, svgPath] = process.argv.slice(2);
if (!['baseline', 'chest-plus-40'].includes(mode) || !projectPath || !svgPath) {
  throw new Error('用法：node draft-carlton.mjs baseline|chest-plus-40 工程.json 纸样.svg');
}

const measurements = {...cisMaleAdult38};
if (mode === 'chest-plus-40') measurements.chest += 40;
const settings = {measurements, options: {}, sa: 10, complete: true};
const draft = new Carlton(settings).use(pluginTheme).draft();
const store = draft.setStores[0];
const errors = [...draft.store.logs.error, ...store.logs.error];
if (errors.length) throw new Error(errors.join('\n'));

function point({x, y}) {
  if (!Number.isFinite(x) || !Number.isFinite(y)) throw new Error('纸样坐标不是有限值');
  return {x, y};
}

const pieces = Object.entries(draft.parts[0]).filter(([, part]) => !part.hidden)
  .map(([name, part]) => {
    const outline = part.paths.seam;
    if (!outline || outline.start().dist(outline.end()) > 1e-6) {
      throw new Error(`裁片净线未闭合：${name}`);
    }
    const draft_paths = {};
    const lines = [];
    for (const [role, path] of Object.entries(part.paths)) {
      // Construction-only paths remain in the SVG. Keep sewn outlines, cut lines and visible marks.
      if (!['seam', 'sa'].includes(role) && (path.hidden || role.startsWith('__macro_banner_'))) continue;
      const length = path.length();
      if (!Number.isFinite(length)) throw new Error(`裁片路径长度不是有限值：${name} / ${role}`);
      if (length <= 1e-6) continue;
      draft_paths[role] = path.ops.map(({type, to, cp1, cp2}) => ({
        type, ...(to && {to: point(to)}), ...(cp1 && {cp1: point(cp1)}), ...(cp2 && {cp2: point(cp2)}),
      }));
      lines.push({lineIndex: lines.length, role, length, start: point(path.start()), end: point(path.end())});
    }
    if (!draft_paths.seam || !draft_paths.sa) throw new Error(`缺少净线或缝份：${name}`);
    return {name, lines, draft_paths};
  });

const markup = draft.render();
const definitions = Object.values(draft.svg.defs.list).join('\n');
const svg = markup.replace(/<defs>[\s\S]*?<\/defs>/, () => `<defs>\n${definitions}\n</defs>`);
if (/\b(?:NaN|Infinity)\b/.test(svg)) throw new Error('纸样图包含无效数值');
const cuts = store.get('cutlist');
const cutlist = Object.fromEntries(pieces.map(({name}) => {
  if (!cuts[name]) throw new Error(`缺少裁片裁剪信息：${name}`);
  return [name, cuts[name]];
}));
const project = {
  version: 1, units: 'mm', source: 'FreeSewing Carlton 4.10.2', pieces, seams: [],
  draft_settings: {
    ...settings, mode, measurementModel: 'cisMaleAdult38',
    cutlist, warnings: [...draft.store.logs.warn, ...store.logs.warn],
  },
};
await writeFile(projectPath, JSON.stringify(project, null, 2) + '\n');
await writeFile(svgPath, svg);
