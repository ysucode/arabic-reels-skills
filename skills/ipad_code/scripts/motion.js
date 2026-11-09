// Render an HTML motion graphic to PNG frames with Chromium. No GPU and no Blender needed.
//   NODE_PATH=$(npm root -g) node motion.js comp.html outdir --fps 30 --seconds 8 [--width 1080 --height 1920] [--from 1 --to 240] [--step 30]
//
// The page must define window.seek(t), where t is seconds and everything on screen is a pure
// function of t: no CSS animations, no timers, no Math.random without a seed.
// Frames are f_0001.png ... and finished frames are skipped, so re-running continues.
// Exits with code 2 if the page declares data-font and that font did not load.
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require('playwright');

const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 ? Number(argv[i + 1]) : d; };
const [comp, out] = argv;
if (!comp || !out || comp.startsWith('--') || out.startsWith('--')) {
  console.error('usage: node motion.js comp.html outdir --fps 30 --seconds 8'); process.exit(1);
}
const fps = opt('fps', 30), W = opt('width', 1080), H = opt('height', 1920), step = opt('step', 1);
const total = Math.round(fps * opt('seconds', 8));
const from = opt('from', 1), to = Math.min(opt('to', total), total);
fs.mkdirSync(out, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  page.on('pageerror', e => { console.error('PAGE ERROR', e.message); process.exitCode = 1; });
  await page.goto(pathToFileURL(path.resolve(comp)).href, { waitUntil: 'networkidle' });
  await page.evaluate(() => { if (typeof window.seek !== 'function') throw new Error('window.seek(t) is missing'); window.seek(0); });
  await page.evaluate(() => document.fonts.ready);

  const font = await page.evaluate(() => document.documentElement.dataset.font || '');
  if (font) {
    const ok = await page.evaluate(f => [...document.fonts].some(x => x.family.replace(/["']/g, '') === f && x.status === 'loaded'), font);
    if (!ok) { console.error(`FONT NOT LOADED: ${font}`); await browser.close(); process.exit(2); }
    console.log(`FONT OK: ${font}`);
  }

  const t0 = Date.now(); let done = 0;
  const todo = [];
  for (let f = from; f <= to; f += step) if (!fs.existsSync(path.join(out, `f_${String(f).padStart(4, '0')}.png`))) todo.push(f);
  console.log(`RENDER ${todo.length} frames to go -> ${out}`);
  for (const f of todo) {
    const name = path.join(out, `f_${String(f).padStart(4, '0')}.png`);
    await page.evaluate(t => window.seek(t), (f - 1) / fps);
    await page.screenshot({ path: name + '.part.png' });
    fs.renameSync(name + '.part.png', name);
    if (++done % 30 === 0) console.log(`FRAME ${f} | ${done}/${todo.length} | ${((Date.now() - t0) / done).toFixed(0)} ms/frame`);
  }
  console.log(`RENDER DONE in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
