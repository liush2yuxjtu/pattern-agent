#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, realpathSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, extname, isAbsolute, join, relative, resolve, sep } from 'node:path';

const kinds = [
  ['appearance', '上身外观与设计对照'],
  ['strain', '应变'],
  ['stress', '应力'],
  ['pressure', '人体接触压力'],
  ['folds', '褶皱与折角'],
];
const formats = { png:'image/png', jpeg:'image/jpeg', webp:'image/webp' };
const text = (v) => typeof v === 'string' && v.trim() !== '';
const object = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const escape = (v) => String(v).replace(/[&<>"']/g, (c) =>
  ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[c]);

async function readImage(root, path, sharp) {
  if (!text(path) || isAbsolute(path) || /^[\w+.-]+:/.test(path) || /[\0\\]/.test(path)) {
    throw new Error('图片须为清单目录内的本地相对路径');
  }
  const file = realpathSync(resolve(root, path));
  const local = relative(root, file);
  if (local === '..' || local.startsWith('..'+sep) || isAbsolute(local)) {
    throw new Error('图片超出清单目录');
  }
  const bytes = readFileSync(file);
  const decoder = sharp(bytes, { failOn:'warning' });
  const meta = await decoder.metadata();
  const mime = formats[meta.format];
  if (!mime || (meta.pages ?? 1) !== 1) {
    throw new Error('只支持可解码的单张 PNG、JPEG 或 WebP');
  }
  const { data, info } = await decoder.autoOrient().toColourspace('srgb').ensureAlpha().raw().toBuffer({ resolveWithObject:true });
  const fingerprint = createHash('sha256').update(info.width+'x'+info.height+':').update(data).digest('hex');
  return { fingerprint, file, mime, bytes };
}

async function preflight(input, root, sharp) {
  const errors = [];
  const inspected = [];
  const usedLabels = new Set();
  const usedPixels = new Map();
  if (!object(input)) throw new Error('图片清单必须是 JSON 对象。');
  for (const field of ['title','revision','size']) {
    if (!text(input[field])) errors.push('缺少 '+field+'（报告标题、工程版次或尺码）');
  }
  const postures = Array.isArray(input.postures) ? input.postures : [];
  if (postures.length !== 4) errors.push('需要 4 个约定姿势，当前 '+postures.length+' 个。');
  for (const [i, posture] of postures.slice(0,4).entries()) {
    const label = text(posture?.name) ? posture.name.trim() : '第 '+(i+1)+' 个姿势';
    const identifier = label.normalize('NFKC').replace(/\s/g,'').toLowerCase();
    if (!text(posture?.name)) errors.push(label+'缺少名称。');
    if (usedLabels.has(identifier)) errors.push(label+'：姿势名称重复。');
    usedLabels.add(identifier);
    const figures = [];
    for (const [key, title] of kinds) {
      const slot = label+' / '+title;
      const configured = posture?.images?.[key];
      const entries = Array.isArray(configured) ? configured : [configured];
      if (!entries.length || entries.every((e) => e === undefined || e === null || e === '')) {
        errors.push(slot+'：缺少已通过验收的图片。');
        continue;
      }
      for (const entry of entries) {
        const path = typeof entry === 'string' ? entry : entry?.path;
        try {
          if (entry !== null && entry !== undefined && typeof entry !== 'string' && !object(entry)) throw new Error('图片项须为路径或带 path 的对象');
          const picture = await readImage(root,path,sharp);
          if (usedPixels.has(picture.fingerprint)) {
            errors.push(slot+'：图片内容已经用于 '+usedPixels.get(picture.fingerprint)+'（'+path+'）。');
            continue;
          }
          usedPixels.set(picture.fingerprint,slot);
          figures.push({ title, caption:text(entry?.caption)?entry.caption:title, picture });
        } catch (error) {
          errors.push(slot+'：'+(path ? path+'：' : '')+error.message);
        }
      }
    }
    inspected.push({ label, figures });
  }
  if (errors.length) throw new Error('图片验收门槛未通过，未生成或替换报告。\n- '+errors.join('\n- '));
  return inspected;
}

function list(items, title, tag) {
  const body = Array.isArray(items) ? items.filter(text).map((v) => '<li>'+escape(v)+'</li>').join('\n') : '';
  return body ? '<section><h2>'+title+'</h2><'+tag+'>'+body+'</'+tag+'></section>\n' : '';
}

function readTables(tables) {
  if (tables === undefined) return [];
  if (!Array.isArray(tables)) throw new Error('tables 须为数组。');
  return tables.map((table, i) => {
    const { title, headers, rows } = table ?? {};
    if (!text(title) || !Array.isArray(headers) || !headers.length || !headers.every(text)
        || !Array.isArray(rows) || !rows.length || !rows.every((row) =>
          Array.isArray(row) && row.length === headers.length
          && row.every((cell) => typeof cell === 'string' || Number.isFinite(cell)))) {
      throw new Error('第 '+(i+1)+' 张统计表须有标题、列名及等宽的文字或数字数据行。');
    }
    return { title, headers, rows };
  });
}

const markdownText = (value) => escape(String(value).replace(/\s+/g, ' ').trim())
  .replace(/[\\\`*_{}\[\]()#+.!|~-]/g, '\\$&');

function renderMarkdown(input, postures, tables, output) {
  const lines = ['# '+markdownText(input.title), '', '尺码 '+markdownText(input.size)
    +' · 工程版次 '+markdownText(input.revision), ''];
  function items(title, values, marker) {
    lines.push('## '+title, '');
    if (Array.isArray(values)) {
      lines.push(...values.filter(text).map((value, i) => marker(i)+markdownText(value)), '');
    }
  }
  if (input.findings?.length) items('主要发现',input.findings,() => '- ');
  lines.push('## 试穿证据','');
  for (const {label,figures} of postures) {
    lines.push('### '+markdownText(label),'');
    for (const {title,caption,picture} of figures) {
      const path = relative(dirname(output),picture.file).split(sep).map((part) =>
        encodeURIComponent(part).replace(/[()]/g, (char) => char === '(' ? '%28' : '%29')).join('/');
      lines.push('#### '+title,'','!['+markdownText(caption)+']('+path+')','',
        markdownText(caption),'');
    }
  }
  if (tables.length) {
    lines.push('## 集中统计与验收','');
    const row = (cells) => '| '+cells.map(markdownText).join(' | ')+' |';
    for (const {title,headers,rows} of tables) {
      lines.push('### '+markdownText(title),'',row(headers),
        '| '+headers.map(() => '---').join(' | ')+' |',...rows.map(row),'');
    }
  }
  items('结论与复测标准',input.nextSteps,(i) => (i+1)+'. ');
  return lines.join('\n');
}

function renderHtml(input, postures, tables) {
  const contents = postures.map(({label,figures}) => '<section><h2>'+escape(label)+'</h2>\n'
    +figures.map(({title,caption,picture}) => '<figure><h3>'+escape(title)+'</h3><img src="data:'
      +picture.mime+';base64,'+picture.bytes.toString('base64')+'" alt="'+escape(caption)
      +'"><figcaption>'+escape(caption)+'</figcaption></figure>').join('\n')
    +'</section>').join('\n');
  const summaries = tables.length ? '<section><h2>集中统计与验收</h2>'+tables.map(({title,headers,rows}) =>
    '<h3>'+escape(title)+'</h3><table><thead><tr>'
    +headers.map((cell) => '<th>'+escape(cell)+'</th>').join('')+'</tr></thead><tbody>'
    +rows.map((row) => '<tr>'+row.map((cell) => '<td>'+escape(cell)+'</td>').join('')+'</tr>').join('')
    +'</tbody></table>').join('')+'</section>' : '';
  return '<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
    + '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; style-src \'unsafe-inline\'; base-uri \'none\'">'
    + '<title>'+escape(input.title)+'</title>'
    + '<style>body{max-width:58rem;margin:auto;padding:1.25rem;color:#192532;background:white;font:17px/1.6 system-ui,sans-serif;overflow-wrap:anywhere}h1,h2,h3{line-height:1.25}section{margin-top:1.6rem}figure{margin:1.5rem 0}img{display:block;max-width:100%;height:auto;margin:auto}figcaption{margin:.5em 0;color:#45566b}@media(max-width:480px){body{padding:.8rem;font-size:16px}h1{font-size:1.65em}}</style></head><body>'
    + '<h1>'+escape(input.title)+'</h1><p>尺码 '+escape(input.size)+' · 工程版次 '+escape(input.revision)+'</p>\n'
    + list(input.findings,'主要发现','ul')+contents+'\n'+summaries
    +list(input.nextSteps,'结论与复测标准','ol')+'</body></html>\n';
}

async function main(args) {
  const sharpOption = args.indexOf('--sharp');
  const positional = sharpOption === -1 ? args : args.slice(0,sharpOption);
  if (positional.length < 1 || positional.length > 2
      || (sharpOption !== -1 && (args.length !== sharpOption+2 || !args[sharpOption+1]))) {
    throw new Error('用法：node bake-report.mjs 图片清单.json [报告.md 或 报告.html] [--sharp /path/to/node_modules/sharp]');
  }
  const [sourceArg, outputArg = sourceArg.slice(0,-5)+'.md'] = positional;
  const format = extname(outputArg).toLowerCase();
  if (extname(sourceArg).toLowerCase() !== '.json' || !['.md','.html'].includes(format)) {
    throw new Error('请提供 JSON 图片清单与可选的 Markdown 或 HTML 输出路径。');
  }
  const source = realpathSync(resolve(sourceArg));
  const output = resolve(outputArg);
  const input = JSON.parse(readFileSync(source,'utf8').replace(/^\uFEFF/, ''));
  const require = createRequire(import.meta.url);
  const sharp = require(sharpOption === -1 ? 'sharp' : resolve(args[sharpOption+1]));
  const postures = await preflight(input,dirname(source),sharp);
  const tables = readTables(input.tables);
  const staging = mkdtempSync(join(dirname(output),'.bake-report-'));
  try {
    const draft = join(staging,'report'+format);
    const report = format === '.md' ? renderMarkdown(input,postures,tables,output)
      : renderHtml(input,postures,tables);
    writeFileSync(draft,report,'utf8');
    renameSync(draft,output);
  } finally {
    rmSync(staging,{recursive:true,force:true});
  }
  console.log('已检查 4 个姿势 × 5 类证据，报告包含 '+postures.reduce((n,p)=>n+p.figures.length,0)+' 张图片。'+output);
}

main(process.argv.slice(2)).catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
