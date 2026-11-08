// Render Arabic on-screen text cards as transparent PNGs with Chromium (right shaping, Google Fonts).
//   NODE_PATH=$(npm root -g) node text_cards.js cards.json outdir
// cards.json: {"width":1080,"height":1920,"font":"Cairo","bottom":430,
//              "cards":[{"id":"t1","big":"","small":"داخل كل معالج","start":0.3,"end":2.3}, ...]}
// start/end are only used by assemble.py; here we just draw.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [, , cfgPath, outDir] = process.argv;
if (!cfgPath || !outDir) { console.error('usage: node text_cards.js cards.json outdir'); process.exit(1); }
const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
const W = cfg.width || 1080, H = cfg.height || 1920, font = cfg.font || 'Cairo', bottom = cfg.bottom ?? 430;
const esc = s => String(s || '').replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  for (const c of cfg.cards) {
    await page.setContent(`<html dir="rtl"><head>
<link href="https://fonts.googleapis.com/css2?family=${encodeURIComponent(font)}:wght@600;900&display=block" rel="stylesheet">
<style>html,body{margin:0;background:transparent;width:${W}px;height:${H}px}
.w{position:absolute;left:0;right:0;bottom:${bottom}px;text-align:center;font-family:'${font}',sans-serif;color:#fff;
text-shadow:0 0 30px rgba(0,0,0,.85),0 4px 14px rgba(0,0,0,.9)}
.big{font-size:${c.bigSize || 150}px;font-weight:900;line-height:1.1;text-shadow:0 0 40px ${c.glow || 'rgba(80,180,255,.75)'},0 4px 18px rgba(0,0,0,.9)}
.small{font-size:${c.smallSize || 66}px;font-weight:600;line-height:1.35;padding:0 70px}</style></head>
<body><div class="w">${c.big ? `<div class="big">${esc(c.big)}</div>` : ''}${c.small ? `<div class="small">${esc(c.small)}</div>` : ''}</div></body></html>`);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(300);
    const ok = await page.evaluate(f => document.fonts.check(`600 40px '${f}'`), font);
    const out = path.join(outDir, `${c.id}.png`);
    await page.screenshot({ path: out, omitBackground: true });
    console.log(out, ok ? `(${font})` : '(FONT NOT LOADED: fallback font used)');
  }
  await browser.close();
})();
