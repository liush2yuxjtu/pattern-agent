#!/usr/bin/env node
'use strict';

// Canonical offline build: C -> WASM, ES modules -> one inline IIFE, then HTML.
// The Python helper only packs the original MakeHuman mesh and collision BVH.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const APP = __dirname;
const ROOT = path.resolve(APP, '../..');
const SRC = path.join(APP, 'src');
const VENDOR = path.join(ROOT, 'web/human-studio/vendor');
const BODY_SOURCE = path.join(ROOT, 'web/human-studio/assets/human.json');
const BODY_PROVENANCE = path.join(ROOT, 'web/human-studio/assets/provenance.json');
const RENDERER_PROVENANCE = path.join(VENDOR, 'provenance.json');
const BODY_HELPER = path.join(ROOT, 'scripts/cloth_lab_body.py');
const LEGACY_ENTRY = path.join(ROOT, 'scripts/build_cloth_lab.py');
const EXPECTED = { zig: '0.14.1', esbuild: '0.25.12' };
const SOLVER_FLAGS = [
  '-target', 'wasm32-freestanding', '-O3', '-nostdlib', '-Wl,--no-entry', '-rdynamic',
  '-Wl,--initial-memory=16777216', '-Wl,--max-memory=16777216',
  '-Wl,-z,stack-size=262144', '-Wl,--strip-debug',
];
const LICENSES = [
  path.join(APP, 'LICENSE.txt'),
  path.join(VENDOR, 'THREE-LICENSE.txt'),
  path.join(ROOT, 'web/human-studio/assets/MAKEHUMAN-CC0.txt'),
];

const HELP = `Build a complete offline WASM + WebGPU/WebGL cloth-lab HTML.

Usage: node web/cloth-lab/build.js [--out <file.html>] [--work-dir <directory>]

  --out <file.html>       HTML destination (relative to the current directory).
                         Default: web/cloth-lab/index.html with build.json.
                         Other names use <name>.build.json beside the HTML.
  --work-dir <directory>  Keep solver.wasm, app.js, bundle-meta.json and body.json
                         here. Default: a temporary directory under work/cloth-lab.
  --help, -h             Show this help without requiring build tools.

Local build dependencies: Node >=18, Zig ${EXPECTED.zig}, esbuild ${EXPECTED.esbuild},
Python 3 with NumPy (web/cloth-lab/requirements-build.txt).
ZIG, ESBUILD and PYTHON select local executables. Without ESBUILD, the builder
also checks local node_modules/.bin and PATH. No tool or asset is downloaded.
All code, WASM, styles, MakeHuman data/BVH and license notices are embedded.
Release WASM omits debug metadata so source checkout paths do not affect it.
`;

function parseArgs(argv) {
  const options = { out: path.join(APP, 'index.html'), workDir: null, help: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') options.help = true;
    else if (arg === '--out' || arg === '--work-dir') {
      const value = argv[++i];
      if (!value || value.startsWith('--')) throw new Error(`${arg} requires a path. Run --help for usage.`);
      options[arg === '--out' ? 'out' : 'workDir'] = path.resolve(value);
    } else throw new Error(`Unknown option: ${arg}. Run --help for usage.`);
  }
  if (!options.help && path.extname(options.out).toLowerCase() !== '.html') {
    throw new Error('--out must name an .html file.');
  }
  return options;
}

function relative(file) {
  const result = path.relative(ROOT, file).split(path.sep).join('/');
  if (result === '..' || result.startsWith('../') || path.isAbsolute(result)) {
    throw new Error(`Bundle input must be committed inside the repository: ${file}`);
  }
  return result;
}

function hash(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex'); }
function read(file) { return fs.readFileSync(file, 'utf8'); }
function readJSON(file) {
  try { return JSON.parse(read(file)); }
  catch (error) { throw new Error(`Cannot read ${relative(file)}: ${error.message}`); }
}
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  }
  return value;
}

function filesIn(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name < b.name ? -1 : a.name > b.name ? 1 : 0)
    .flatMap(entry => {
      const file = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) throw new Error(`Build sources cannot be symbolic links: ${relative(file)}`);
      return entry.isDirectory() ? filesIn(file) : entry.isFile() ? [file] : [];
    });
}

function hashes(files) {
  return Object.fromEntries([...new Set(files)].sort().map(file => [relative(file), hash(fs.readFileSync(file))]));
}

function tool(name, local = []) {
  const override = process.env[name];
  const candidates = override ? [override] : [...local, name.toLowerCase()];
  for (const candidate of candidates) {
    const executable = candidate.includes('/') || candidate.includes('\\') ? path.resolve(candidate) : candidate;
    // A bare command is resolved by spawnSync using PATH; executable paths work too.
    const probe = spawnSync(executable, [name === 'ZIG' ? 'version' : '--version'], { encoding: 'utf8' });
    if (!probe.error && probe.status === 0) return { executable, version: probe.stdout.trim() };
    if (override) {
      throw new Error(`${name}=${override} is not a usable executable: ${probe.error?.message || probe.stderr.trim() || `exit ${probe.status}`}`);
    }
  }
  throw new Error(`${name} was not found. Set ${name} to a local executable (tested ${EXPECTED[name.toLowerCase()]}). Run --help for dependencies.`);
}

function pythonTool() {
  const candidates = process.env.PYTHON ? [process.env.PYTHON] : ['python3', 'python'];
  for (const candidate of candidates) {
    const executable = candidate.includes('/') || candidate.includes('\\') ? path.resolve(candidate) : candidate;
    const probe = spawnSync(executable, ['--version'], { encoding: 'utf8' });
    if (!probe.error && probe.status === 0 && /^Python 3\./.test(probe.stdout.trim())) {
      return { executable, version: probe.stdout.trim().replace(/^Python /, '') };
    }
  }
  throw new Error('Python 3 is required for MakeHuman/BVH packing. Set PYTHON to its executable and install web/cloth-lab/requirements-build.txt.');
}

function run(executable, args, description) {
  process.stderr.write(`[cloth-lab] ${description}\n`);
  const result = spawnSync(executable, args, { cwd: ROOT, stdio: 'inherit' });
  if (result.error) throw new Error(`${description}: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`${description} failed (${result.signal || `exit ${result.status}`}).`);
}

function replaceOnce(text, token, content) {
  if (text.split(token).length !== 2) throw new Error(`HTML template must contain exactly one ${token} placeholder.`);
  return text.replace(token, () => content);
}

function validateBundle(meta, bundleFile) {
  const outputs = Object.entries(meta.outputs);
  if (outputs.length !== 1 || path.resolve(ROOT, outputs[0][0]) !== bundleFile || outputs[0][1].imports.length) {
    throw new Error('Standalone build must produce exactly one JavaScript bundle with no external imports or chunks.');
  }
  for (const [input, info] of Object.entries(meta.inputs)) {
    relative(path.resolve(ROOT, input));
    for (const item of info.imports) {
      if (item.external) throw new Error(`External runtime import in ${input}: ${item.path}`);
    }
  }
  return Object.keys(meta.inputs).map(input => path.resolve(ROOT, input)).sort();
}

function writeArtifacts(out, manifest, html, metadata) {
  fs.mkdirSync(path.dirname(out), { recursive: true });
  for (const file of [out, manifest]) {
    if (fs.existsSync(file) && !fs.lstatSync(file).isFile()) {
      throw new Error(`Output must be a regular file: ${file}`);
    }
  }
  // Prepare both complete files before replacing either deliverable. Renames are
  // atomic on the destination filesystem; restore the previous HTML if the
  // manifest replacement fails so a failed build does not leave a partial pair.
  const temporary = fs.mkdtempSync(path.join(path.dirname(out), '.cloth-lab-build-'));
  const previous = path.join(temporary, 'previous.html');
  try {
    const nextHTML = path.join(temporary, 'index.html');
    const nextManifest = path.join(temporary, 'build.json');
    fs.writeFileSync(nextHTML, html);
    fs.writeFileSync(nextManifest, JSON.stringify(metadata, null, 2)+'\n');
    const existed = fs.existsSync(out);
    if (existed) fs.copyFileSync(out, previous);
    fs.renameSync(nextHTML, out);
    try { fs.renameSync(nextManifest, manifest); }
    catch (error) {
      if (existed) fs.renameSync(previous, out);
      else fs.rmSync(out);
      throw error;
    }
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
}

function build(options) {
  if (Number(process.versions.node.split('.')[0]) < 18) throw new Error('Node.js >=18 is required.');
  const sourceFiles = filesIn(SRC);
  const fixedBuildFiles = [__filename, LEGACY_ENTRY, BODY_HELPER, path.join(APP, 'package.json'),
    path.join(APP, 'requirements-build.txt'), BODY_SOURCE, BODY_PROVENANCE, RENDERER_PROVENANCE, ...LICENSES];
  const lockfile = path.join(APP, 'package-lock.json');
  const buildFiles = () => [...fixedBuildFiles, ...(fs.existsSync(lockfile) ? [lockfile] : [])];
  // Detect edits during a build, including newly added source modules or vendor files.
  const watchFiles = () => [...filesIn(SRC), ...filesIn(VENDOR), ...buildFiles()];
  const before = hashes(watchFiles());
  const protectedDirs = [SRC, VENDOR, path.join(ROOT, 'scripts'), path.join(ROOT, 'web/human-studio/assets')];
  for (const [option, target] of [['--out', options.out], ['--work-dir', options.workDir]]) {
    if (target && protectedDirs.some(dir => target === dir || target.startsWith(dir+path.sep))) {
      throw new Error(`${option} must be outside the source, scripts, vendor and body-asset directories.`);
    }
  }
  const bodyHash = hash(fs.readFileSync(BODY_SOURCE));
  const fit = readJSON(path.join(SRC, 'avatar-fit.json'));
  if (fit.sourceBodySha256 !== bodyHash) {
    throw new Error('Stale waist arrangement: avatar-fit.json does not match the MakeHuman source. Run python tools/cloth_lab/build_avatar_fit.py.');
  }
  const zig = tool('ZIG');
  const esbuild = tool('ESBUILD', [path.join(APP, 'node_modules/.bin/esbuild'), path.join(ROOT, 'node_modules/.bin/esbuild')]);
  for (const [name, resolved] of Object.entries({ zig, esbuild })) {
    if (resolved.version !== EXPECTED[name]) {
      throw new Error(`Expected ${name} ${EXPECTED[name]}, got ${resolved.version}. Select the pinned executable with ${name.toUpperCase()}.`);
    }
  }
  const python = pythonTool();
  let workDir = options.workDir;
  if (!workDir) {
    const parent = path.join(ROOT, 'work/cloth-lab');
    fs.mkdirSync(parent, { recursive: true });
    workDir = fs.mkdtempSync(path.join(parent, 'build-'));
  } else fs.mkdirSync(workDir, { recursive: true });
  try {
    const wasmFile = path.join(workDir, 'solver.wasm');
    const bundleFile = path.join(workDir, 'app.js');
    const metaFile = path.join(workDir, 'bundle-meta.json');
    const bodyFile = path.join(workDir, 'body.json');
    run(zig.executable, ['cc', ...SOLVER_FLAGS,
      path.join(SRC, 'solver.c'), '-o', wasmFile], 'Compiling solver.c to the fixed-memory WASM solver');
    run(esbuild.executable, [path.join(SRC, 'app.js'), '--bundle', '--minify', '--format=iife',
      '--platform=browser', '--target=es2022', '--charset=utf8', '--tsconfig-raw={}',
      '--legal-comments=inline', `--metafile=${metaFile}`, `--outfile=${bundleFile}`], 'Bundling all runtime modules and renderer sources');
    const inputs = validateBundle(readJSON(metaFile), bundleFile);
    run(python.executable, [BODY_HELPER, '--out', bodyFile], 'Packing the original MakeHuman body and collision BVH');
    const body = readJSON(bodyFile);
    if (body.sourceSha256 !== bodyHash) throw new Error('MakeHuman source changed while preparing its body payload. Rebuild.');
    const wasm = fs.readFileSync(wasmFile);
    const script = read(bundleFile);
    if (/<\/script[\s>]/i.test(script)) throw new Error('JavaScript bundle contains an unsafe inline </script> terminator.');
    const renderer = readJSON(RENDERER_PROVENANCE);
    const tools = { node: process.versions.node, zig: zig.version, esbuild: esbuild.version, python: python.version };
    const sources = hashes([...sourceFiles, ...buildFiles(), ...inputs]);
    const bundle = { entryPoint: 'web/cloth-lab/src/app.js', format: 'iife', target: 'es2022',
      inputs: inputs.map(relative), sourceModules: inputs.filter(file => file.startsWith(SRC+path.sep) && file.endsWith('.js')).map(relative) };
    const wasmSha256 = hash(wasm);
    const fingerprint = hash(JSON.stringify(canonical({ sources, wasm: wasmSha256, body: bodyHash,
      bodyData: hash(JSON.stringify(body)), renderer: renderer.commit, bundle: hash(script) })));
    const payload = { body, wasm: wasm.toString('base64'), wasmSha256, sources, renderer, buildFingerprint: fingerprint };
    const notices = LICENSES.map(read).join('\n\n').replaceAll('--', '—');
    let html = replaceOnce(read(path.join(SRC, 'template.html')), '/*STYLE*/', read(path.join(SRC, 'style.css')));
    html = replaceOnce(html, '/*PAYLOAD*/', JSON.stringify(payload).replaceAll('<', '\\u003c'));
    html = replaceOnce(html, '/*APP*/', script);
    html = replaceOnce(html, '<!--NOTICES-->', `<!--\n${notices}\n-->`);
    html = html.split(/\r?\n/).map(line => line.trimEnd()).join('\n').replace(/\n*$/, '\n');
    if (JSON.stringify(before) !== JSON.stringify(hashes(watchFiles()))) {
      throw new Error('Source files changed during the build. Rebuild after saving all source files.');
    }
    const metadata = { fingerprint, htmlSha256: hash(html), htmlBytes: Buffer.byteLength(html), wasmSha256,
      bodySourceSha256: bodyHash, vertices: body.vertices, triangles: body.triangles, tools,
      format: 'standalone-html', releaseStripDebug: true,
      solver: { source: 'web/cloth-lab/src/solver.c', compiler: 'zig cc', flags: SOLVER_FLAGS }, bundle, sources };
    const manifest = path.join(path.dirname(options.out), path.basename(options.out).toLowerCase() === 'index.html'
      ? 'build.json' : path.basename(options.out, path.extname(options.out))+'.build.json');
    writeArtifacts(options.out, manifest, html, metadata);
    process.stderr.write(`[cloth-lab] Wrote ${options.out} (${metadata.htmlBytes} bytes)\n[cloth-lab] Manifest ${manifest}\n`);
    process.stdout.write(JSON.stringify(metadata, null, 2)+'\n');
    return metadata;
  } finally {
    if (!options.workDir) fs.rmSync(workDir, { recursive: true, force: true });
  }
}

if (require.main === module) {
  try {
    const options = parseArgs(process.argv.slice(2));
    if (options.help) process.stdout.write(HELP);
    else build(options);
  } catch (error) {
    process.stderr.write(`cloth-lab: ${error.message}\n`);
    process.exitCode = 1;
  }
}
