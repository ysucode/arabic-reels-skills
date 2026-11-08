// node render.js <fps> <outDir> [workers] [from] [to]
// Renders comp.html frame by frame with a 180-degree shutter. Existing frames are kept, so a stopped run can resume.
const path=require('path'),fs=require('fs');
const {chromium}=require(path.join(__dirname,'../vendor/node_modules/playwright-core'));
const END=+fs.readFileSync(path.join(__dirname,'comp.src.html'),'utf8').match(/const END=([\d.]+)/)[1];
const [,,fpsArg='30',out='frames',wArg='4',fromArg='0',toArg='']=process.argv;
const fps=+fpsArg,total=Math.ceil(END*fps),from=+fromArg,to=toArg?+toArg:total,workers=+wArg,dur=.5/fps;
const msp=path.join(process.env.LOCALAPPDATA,'ms-playwright');const newest=fs.readdirSync(msp).filter(d=>/^chromium-\d+$/.test(d)).sort((a,b)=>+b.split('-')[1]-+a.split('-')[1])[0];const base=path.join(msp,newest);const dir=fs.readdirSync(base).find(d=>d.startsWith('chrome'));
const url=require('url').pathToFileURL(path.join(__dirname,'comp.html')).href;
fs.mkdirSync(out,{recursive:true});
let next=from,done=0,captures=0;const t0=Date.now();
async function worker(i){
  const b=await chromium.launch({executablePath:path.join(base,dir,'chrome.exe'),args:['--use-angle=d3d11','--ignore-gpu-blocklist','--enable-gpu-rasterization']});
  const pg=await b.newPage({viewport:{width:1080,height:1920}});
  pg.on('pageerror',e=>console.log('pageerror',e.message));
  await pg.goto(url);await pg.evaluate('window.__ready');
  while(next<to){
    const f=next++;const file=path.join(out,String(f).padStart(5,'0')+'.jpg');
    if(fs.existsSync(file)){done++;continue}
    const n=await pg.evaluate(`window.__seek(${f/fps},${dur})`);captures+=n;
    await pg.screenshot({path:file+'.tmp',type:'jpeg',quality:96});fs.renameSync(file+'.tmp',file);
    done++;if(done%100===0)console.log(done,'/',to-from,((Date.now()-t0)/done).toFixed(0)+' ms/frame','avg samples',(captures/done).toFixed(1));
  }
  await b.close();
}
Promise.all(Array.from({length:workers},(_,i)=>worker(i))).then(()=>console.log('done',to-from,'frames in',((Date.now()-t0)/1000).toFixed(0)+'s'));
