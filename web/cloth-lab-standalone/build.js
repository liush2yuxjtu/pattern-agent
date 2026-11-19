#!/usr/bin/env node
'use strict';

// Keep one canonical source tree and publish its complete standalone HTML here.
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const args = process.argv.slice(2);
if (args.length === 1 && ['--help', '-h'].includes(args[0])) {
  process.stdout.write(`Build the Pattern Agent standalone cloth distribution.

Usage: node web/cloth-lab-standalone/build.js [--out file.html] [--work-dir directory]

Default output: web/cloth-lab-standalone/index.html and build.json.
--out paths are relative to the current working directory.
The canonical modules and compiler entry are in web/cloth-lab/.
Requires Node >=18, Zig 0.14.1, esbuild 0.25.12, Python 3 and NumPy.
ZIG, ESBUILD and PYTHON select existing local build tools. No downloads occur.
`);
} else {
  const forwarded = args.includes('--out')
    ? args
    : ['--out', path.join(__dirname, 'index.html'), ...args];
  const result = spawnSync(process.execPath, [
    path.resolve(__dirname, '../cloth-lab/build.js'), ...forwarded,
  ], { stdio: 'inherit' });
  if (result.error) {
    process.stderr.write(`cloth-lab-standalone: ${result.error.message}\n`);
    process.exitCode = 1;
  } else process.exitCode = result.status ?? 1;
}
