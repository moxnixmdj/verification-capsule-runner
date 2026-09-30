cd /app && asset=$(find dist/assets -name '*.js' -type f | head -1) && echo "ASSET=$asset" && grep -o -n -E '__vite-browser-external|Module "node:(fs|path)"|node:fs|node:path' "$asset" | head -30 || true && node - <<'NODE'
const fs=require('fs');
const f=fs.readdirSync('/app/dist/assets').find(x=>x.endsWith('.js'));
const s=fs.readFileSync('/app/dist/assets/'+f,'utf8');
for (const needle of ['browser-external','readFileSync','existsSync','.join']) {
  const i=s.indexOf(needle);
  console.log('\nNEEDLE',needle,'INDEX',i);
  if(i>=0) console.log(s.slice(Math.max(0,i-240),Math.min(s.length,i+520)));
}
NODE
