// Render Arabic on-screen text cards as transparent PNGs with Chromium (right shaping, Google Fonts).
//   NODE_PATH=$(npm root -g) node text_cards.js cards.json outdir
// cards.json: {"width":1080,"height":1920,"font":"Cairo","bottom":520,
//              "cards":[{"id":"t1","big":"","small":"داخل كل معالج","start":0.3,"end":2.3}, ...]}
// start/end are only used by assemble.py; here we just draw.
// On vertical video the text stays inside x200-880, y270-1400, clear of the Reels and TikTok buttons:
// big text shrinks to fit, and the script fails if a card still leaves that area.
// Exit codes: 2 = font did not load, 3 = a card left the safe area.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [, , cfgPath, outDir] = process.argv;
if (!cfgPath || !outDir) { console.error('usage: node text_cards.js cards.json outdir'); process.exit(1); }
const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
const W = cfg.width || 1080, H = cfg.height || 1920, font = cfg.font || 'Cairo';
const vertical = H > W;
const bottom = cfg.bottom ?? (vertical ? 520 : 120), side = cfg.side ?? (vertical ? 200 : 70);
// Fixed limits, scaled from 1080x1920. They must not depend on cfg.bottom or cfg.side, which are what gets checked.
const sx = W / 1080, sy = H / 1920;
const safe = vertical ? { x0: 200 * sx, x1: 880 * sx, y0: 270 * sy, y1: 1400 * sy } : { x0: 0, x1: W, y0: 0, y1: H };
const esc = s => String(s || '').replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  let failed = 0;
  for (const c of cfg.cards) {
    await page.setContent(`<html dir="rtl"><head>
<link href="https://fonts.googleapis.com/css2?family=${encodeURIComponent(font)}:wght@600;900&display=block" rel="stylesheet">
<style>html,body{margin:0;background:transparent;width:${W}px;height:${H}px}
.w{position:absolute;left:${side}px;right:${side}px;bottom:${bottom}px;text-align:center;font-family:'${font}',sans-serif;color:#fff;
text-shadow:0 0 30px rgba(0,0,0,.85),0 4px 14px rgba(0,0,0,.9)}
.big{display:inline-block;white-space:nowrap;font-size:${c.bigSize || 150}px;font-weight:900;line-height:1.1;text-shadow:0 0 40px ${c.glow || 'rgba(80,180,255,.75)'},0 4px 18px rgba(0,0,0,.9)}
.small{font-size:${c.smallSize || 66}px;font-weight:600;line-height:1.35}</style></head>
<body><div class="w">${c.big ? `<div><div class="big">${esc(c.big)}</div></div>` : ''}${c.small ? `<div class="small">${esc(c.small)}</div>` : ''}</div></body></html>`, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(300);
    const ok = await page.evaluate(f => [...document.fonts].some(x => x.family.replace(/["']/g, '') === f && x.status === 'loaded'), font);
    if (!ok) { console.error(`FONT NOT LOADED: ${font}`); await browser.close(); process.exit(2); }

    const box = await page.evaluate(maxW => {
      const big = document.querySelector('.big');
      if (big) {
        const size = parseFloat(getComputedStyle(big).fontSize);
        const w = big.getBoundingClientRect().width;
        if (w > maxW) big.style.fontSize = Math.floor(size * maxW / w) + 'px';
      }
      // Width comes from the text itself, height from the line boxes (a Range is taller than the glyphs in Cairo).
      const els = [...document.querySelectorAll('.big,.small')];
      const rs = els.map(e => { const r = document.createRange(); r.selectNodeContents(e); return r.getBoundingClientRect(); });
      const bs = els.map(e => e.getBoundingClientRect());
      return { x0: Math.min(...rs.map(r => r.left)), x1: Math.max(...rs.map(r => r.right)), y0: Math.min(...bs.map(r => r.top)), y1: Math.max(...bs.map(r => r.bottom)) };
    }, safe.x1 - safe.x0);

    const out = path.join(outDir, `${c.id}.png`);
    await page.screenshot({ path: out, omitBackground: true });
    const inside = !vertical || (box.x0 >= safe.x0 - 1 && box.x1 <= safe.x1 + 1 && box.y0 >= safe.y0 - 1 && box.y1 <= safe.y1 + 1);
    if (!inside) failed++;
    console.log(out, `(${font})`, inside ? 'safe' : `OUTSIDE SAFE AREA x${Math.round(box.x0)}-${Math.round(box.x1)} y${Math.round(box.y0)}-${Math.round(box.y1)}`);
  }
  await browser.close();
  if (failed) process.exit(3);
})();
