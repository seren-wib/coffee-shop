// Builds one HTML file per stage document from docs/specs/<doc>/ for upload to Google Docs.
// Usage: node build-docs.mjs [specsDir=docs/specs] [outDir=dist/docs]
// Order comes from each folder's README.md file table; sub-folders are followed through their own README.md.
// Mermaid blocks must already be rendered to images (mmdc) before this runs; local images are inlined as data URIs.
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { marked } from 'marked';

const specs = path.resolve(process.argv[2] ?? 'docs/specs');
const out = path.resolve(process.argv[3] ?? 'dist/docs');
const DOCS = ['spmp', 'srs', 'sdd', 'stp', 'sip', 'smp'];
const MIME = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.svg': 'image/svg+xml' };

const sha = (() => { try { return execSync('git rev-parse --short HEAD', { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); } catch { return 'unknown'; } })();

// Files linked from a README table, in table order: | [name](path) | ... |
function ordered(readme) {
  const dir = path.dirname(readme);
  const text = fs.readFileSync(readme, 'utf8');
  const files = [];
  for (const m of text.matchAll(/^\|\s*\[[^\]]*\]\(([^)]+)\)/gm)) {
    if (m[1].includes('<')) { console.warn(`${path.relative(specs, readme)}: skipped template link ${m[1]}`); continue; }
    const target = path.join(dir, m[1]);
    if (fs.existsSync(target) && fs.statSync(target).isDirectory()) files.push(...withIndex(path.join(target, 'README.md')));
    else if (!fs.existsSync(target)) throw new Error(`${path.relative(specs, readme)} links a missing file: ${m[1]}`);
    else if (target.endsWith('.md') && path.basename(target) !== 'README.md') files.push(target);
    else if (path.basename(target) === 'README.md') files.push(...withIndex(target));
  }
  return files;
}
// A sub-folder README contributes its own text (heading and table removed) and then its files.
function withIndex(readme) {
  if (!fs.existsSync(readme)) return [];
  return [readme, ...ordered(readme)];
}

function clean(md, file) {
  let s = md.replace(/<!--[\s\S]*?-->\n?/g, '');
  // Drop the file table of a sub-folder README; the files follow anyway.
  if (path.basename(file) === 'README.md') s = s.replace(/^\|.*\|\s*$\n?/gm, '');
  // Inline local images so Docs does not need a public URL.
  s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (all, alt, src) => {
    if (/^https?:|^data:/.test(src)) return all;
    let p = path.resolve(path.dirname(file), src);
    // Google Docs drops SVG; the workflow renders each SVG to <file>.svg.png first.
    if (p.endsWith('.svg') && fs.existsSync(p + '.png')) p += '.png';
    const type = MIME[path.extname(p).toLowerCase()];
    if (!type || !fs.existsSync(p)) return all;
    return `![${alt}](data:${type};base64,${fs.readFileSync(p).toString('base64')})`;
  });
  return s.trim();
}

fs.mkdirSync(out, { recursive: true });
for (const doc of DOCS) {
  const readme = path.join(specs, doc, 'README.md');
  if (!fs.existsSync(readme)) continue;
  const head = fs.readFileSync(readme, 'utf8').replace(/<!--[\s\S]*?-->\n?/g, '').replace(/^\|.*\|\s*$\n?/gm, '').trim();
  const parts = ordered(readme).map(f => clean(fs.readFileSync(f, 'utf8'), f));
  const stamp = `> 이 문서는 레포 \`docs/specs/${doc}/\`의 커밋 \`${sha}\`에서 만들어졌다. 고칠 때는 레포를 고친다.`;
  const md = [head, stamp, ...parts].join('\n\n') + '\n';
  fs.writeFileSync(path.join(out, `${doc}.md`), md);
  fs.writeFileSync(path.join(out, `${doc}.html`), `<html><head><meta charset="utf-8"></head><body>${marked.parse(md)}</body></html>\n`);
  console.log(`${doc}: ${parts.length} files`);
}
