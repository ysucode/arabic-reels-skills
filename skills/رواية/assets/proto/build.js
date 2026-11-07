const fs=require('fs'),p=require('path');const f=p.join(__dirname,'../../node_modules/@fontsource/ibm-plex-sans-arabic/files/ibm-plex-sans-arabic-');
const b=x=>fs.readFileSync(f+x+'-700-normal.woff2').toString('base64');
fs.writeFileSync(p.join(__dirname,'comp.html'),fs.readFileSync(p.join(__dirname,'comp.src.html'),'utf8').replace('__AR__',b('arabic')).replace('__LA__',b('latin')));
