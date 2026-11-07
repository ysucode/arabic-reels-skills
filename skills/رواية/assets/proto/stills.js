// node stills.js out.png 0,5,13 [cols]
const path=require('path');const {chromium}=require(path.join(__dirname,'../vendor/node_modules/playwright-core'));const sharp=require(path.join(__dirname,'../vendor/node_modules/sharp'));const fs=require('fs');
(async()=>{const[,,out,ts,cols='6',tw='300']=process.argv;const msp=path.join(process.env.LOCALAPPDATA,'ms-playwright');const newest=fs.readdirSync(msp).filter(d=>/^chromium-\d+$/.test(d)).sort((a,b)=>+b.split('-')[1]-+a.split('-')[1])[0];const base=path.join(msp,newest);const dir=fs.readdirSync(base).find(d=>d.startsWith('chrome'));
const b=await chromium.launch({executablePath:path.join(base,dir,'chrome.exe'),args:['--use-angle=d3d11','--ignore-gpu-blocklist','--enable-unsafe-swiftshader']});
const pg=await b.newPage({viewport:{width:1080,height:1920}});const errs=[];pg.on('pageerror',e=>errs.push(e.message));pg.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
await pg.goto('file:///'+require('url').pathToFileURL(path.join(__dirname,'comp.html')).href.replace('file:///','')) ;await pg.evaluate('window.__ready');
const T=ts.split(',').map(Number),tiles=[],W=+tw,H=Math.round(W*16/9);
for(const t of T){const s0=Date.now();await pg.evaluate(`window.__seek(${t})`);const buf=await pg.screenshot({type:'png'});
 const label=Buffer.from(`<svg width="${W}" height="30"><rect width="70" height="30" fill="#000"/><text x="6" y="22" font-size="20" fill="#fff" font-family="Arial">${t}s</text></svg>`);
 tiles.push(await sharp(buf).resize(W,H).composite([{input:label,top:0,left:0}]).png().toBuffer());}
const c=+cols,r=Math.ceil(T.length/c);await sharp({create:{width:c*W+(c+1)*8,height:r*H+(r+1)*8,channels:3,background:'#888'}}).composite(tiles.map((d,i)=>({input:d,left:8+(i%c)*(W+8),top:8+Math.floor(i/c)*(H+8)}))).png().toFile(out);
console.log('errors:',errs.slice(0,6));await b.close()})().catch(e=>{console.error(e);process.exit(1)})
