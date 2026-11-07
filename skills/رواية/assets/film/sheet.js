// node sheet.js out.png frameDir fps cols width t1,t2,...
const path=require('path'),fs=require('fs');const sharp=require(path.join(__dirname,'../vendor/node_modules/sharp'));
(async()=>{const[,,out,dir,fps,cols,w,ts]=process.argv;const W=+w,H=Math.round(W*16/9),T=ts.split(',').map(Number),c=+cols,r=Math.ceil(T.length/c);
const tiles=[];for(const t of T){const f=path.join(dir,String(Math.round(t*fps)).padStart(5,'0')+'.jpg');
const label=Buffer.from(`<svg width="${W}" height="26"><rect width="84" height="26" fill="#000"/><text x="5" y="19" font-size="17" fill="#fff" font-family="Arial">${t}s</text></svg>`);
tiles.push(await sharp(f).resize(W,H).composite([{input:label,top:0,left:0}]).png().toBuffer())}
await sharp({create:{width:c*W+(c+1)*6,height:r*H+(r+1)*6,channels:3,background:'#888'}}).composite(tiles.map((d,i)=>({input:d,left:6+(i%c)*(W+6),top:6+Math.floor(i/c)*(H+6)}))).png().toFile(out)})();
