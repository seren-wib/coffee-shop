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
// Remove only file-list tables: a table block whose rows link files in the first cell. Other tables stay.
function dropFileTables(md) {
  return md.replace(/(?:^\|.*\|[ \t]*(?:\n|$))+/gm, block =>
    /^\|\s*\[[^\]]*\]\([^)]+\)/m.test(block) ? '' : block);
}
// Google Docs ignores % widths and max-width on imported images; only px works.
// Page body is 624px wide (Letter/A4 with 1in margins), so cap width there and scale height to match.
const MAX_W = 624;
function pngSize(buf) {
  if (buf.length < 24 || buf.toString('ascii', 12, 16) !== 'IHDR') return null;
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}
const esc = t => t.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
// A sub-folder README contributes its own text (heading and table removed) and then its files.
function withIndex(readme) {
  if (!fs.existsSync(readme)) return [];
  return [readme, ...ordered(readme)];
}

function clean(md, file) {
  let s = md.replace(/<!--[\s\S]*?-->\n?/g, '');
  // Drop the file table of a sub-folder README; the files follow anyway.
  if (path.basename(file) === 'README.md') s = dropFileTables(s);
  // Inline local images so Docs does not need a public URL.
  s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (all, alt, src) => {
    if (/^https?:|^data:/.test(src)) return all;
    let p = path.resolve(path.dirname(file), src);
    // Google Docs drops SVG; the workflow renders each SVG to <file>.svg.png first.
    if (p.endsWith('.svg') && fs.existsSync(p + '.png')) p += '.png';
    const type = MIME[path.extname(p).toLowerCase()];
    if (!type || !fs.existsSync(p)) return all;
    const buf = fs.readFileSync(p);
    const src64 = `data:${type};base64,${buf.toString('base64')}`;
    const size = type === 'image/png' ? pngSize(buf) : null;
    if (!size) return `![${alt}](${src64})`;
    const w = Math.min(size.w, MAX_W), h = Math.round(size.h * w / size.w);
    return `<img src="${src64}" alt="${esc(alt)}" width="${w}" height="${h}">`;
  });
  return s.trim();
}

fs.mkdirSync(out, { recursive: true });
for (const doc of DOCS) {
  const readme = path.join(specs, doc, 'README.md');
  if (!fs.existsSync(readme)) continue;
  const head = fs.readFileSync(readme, 'utf8').replace(/<!--[\s\S]*?-->\n?/g, '');
  const headText = dropFileTables(head).trim();
  const parts = ordered(readme).map(f => clean(fs.readFileSync(f, 'utf8'), f));
  const stamp = `> 이 문서는 레포 \`docs/specs/${doc}/\`의 커밋 \`${sha}\`에서 만들어졌다. 고칠 때는 레포를 고친다.`;
  const md = [headText, stamp, ...parts].join('\n\n') + '\n';
  fs.writeFileSync(path.join(out, `${doc}.md`), md);
  fs.writeFileSync(path.join(out, `${doc}.html`), `<html><head><meta charset="utf-8"></head><body>${marked.parse(md)}</body></html>\n`);
  console.log(`${doc}: ${parts.length} files`);
}
