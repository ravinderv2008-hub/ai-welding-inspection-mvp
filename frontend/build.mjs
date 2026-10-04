import { build } from 'esbuild';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const root = resolve('.');
const dist = resolve('dist');
await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });
await build({
  entryPoints: [resolve(root, 'src/main.jsx')],
  bundle: true,
  outdir: resolve(dist, 'assets'),
  entryNames: 'app',
  loader: { '.jsx': 'jsx', '.css': 'css' },
  jsx: 'automatic',
  format: 'esm',
  minify: true,
});
const template = await readFile(resolve(root, 'index.html'), 'utf8');
const html = template.replace('<script type="module" src="/src/main.jsx"></script>', '<link rel="stylesheet" href="/assets/app.css"><script type="module" src="/assets/app.js"></script>');
await writeFile(resolve(dist, 'index.html'), html);
console.log('Production bundle written to dist/');
