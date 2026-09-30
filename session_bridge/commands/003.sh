set -e
cd /app
cp visibility.json /tmp/visibility.orig
cp src/client-entry.ts /tmp/client-entry.orig
cleanup() {
  cp /tmp/visibility.orig visibility.json
  cp /tmp/client-entry.orig src/client-entry.ts
  rm -f src/private-helper.ts
}
trap cleanup EXIT

cat > src/private-helper.ts <<'TS'
export function identityForPrivateProbe(value: string): string {
  return value;
}
TS
node - <<'NODE'
const fs=require('fs')
const p='visibility.json'
const v=JSON.parse(fs.readFileSync(p,'utf8'))
v.privateSources.push('src/private-helper.ts')
fs.writeFileSync(p,JSON.stringify(v,null,2)+'\n')
NODE
cat > src/client-entry.ts <<'TS'
import { renderGreeting } from "./client/render";
import { identityForPrivateProbe } from "./private-helper";

if (Bun.argv.includes("--trace-probe")) {
  renderGreeting("__TRACE_PROBE__");
} else {
  console.log(renderGreeting(identityForPrivateProbe("Ada")));
}
TS

bun run release
node - <<'NODE'
const fs=require('fs'),path=require('path')
const map=JSON.parse(fs.readFileSync('dist/client-entry.js.map','utf8'))
if(!map.sources.includes('[private]')) throw new Error('mixed map did not redact private source')
for(let i=0;i<map.sources.length;i++){
  const s=map.sources[i]
  if(s==='[private]'){
    if(map.sourcesContent?.[i]!==null) throw new Error('private sourcesContent not redacted')
  } else {
    const resolved=path.relative('/app',path.resolve('/app/dist',s)).split(path.sep).join('/')
    const pub=JSON.parse(fs.readFileSync('visibility.json','utf8')).publicSources
    if(!pub.includes(resolved)) throw new Error('non-public map source '+s)
  }
}
console.log('MIXED_MAP_REDACTION_PASS')
NODE
test "$(bun dist/client-entry.js)" = "Hello, Ada!"
cleanup
trap - EXIT
bun run release

node - <<'NODE'
const fs=require('fs'),path=require('path')
const root='/app',dist='/app/dist'
const vis=JSON.parse(fs.readFileSync(root+'/visibility.json','utf8'))
const manifest=JSON.parse(fs.readFileSync(dist+'/release-manifest.json','utf8'))
const actual=[]
function walk(d){for(const e of fs.readdirSync(d,{withFileTypes:true})){const p=path.join(d,e.name);if(e.isDirectory())walk(p);else actual.push(path.relative(root,p).split(path.sep).join('/'))}}
walk(dist); actual.sort()
const listed=[...manifest.artifacts].sort()
if(JSON.stringify(actual)!==JSON.stringify(listed)) throw new Error('manifest artifact set mismatch')
for(const p of [...(manifest.originalSources||[]),...(manifest.publicSources||[]),...((manifest.provenance||{}).publicSources||[])]){
  if(path.isAbsolute(p)||p.startsWith('../')||!vis.publicSources.includes(p)) throw new Error('unsafe manifest provenance '+p)
}
const corpus=actual.map(p=>fs.readFileSync(path.join(root,p),'utf8')).join('\n')
for(const priv of vis.privateSources){
  if(corpus.includes(priv)||corpus.includes(path.basename(priv))) throw new Error('private path leak '+priv)
  const body=fs.readFileSync(path.join(root,priv),'utf8')
  const secrets=[...body.matchAll(/(["'`])((?:\\.|(?!\1)[\s\S])*?)\1/g)].map(m=>m[2].trim()).filter(s=>s.length>=8)
  for(const s of secrets) if(corpus.includes(s)) throw new Error('private literal leak')
}
if(corpus.includes('/app')) throw new Error('absolute local path leak')
console.log('MANIFEST_AND_LEAK_SCAN_PASS')
NODE

client="$(bun dist/client-entry.js)"
server="$(bun dist/server-entry.js)"
test "$client" = "Hello, Ada!"
test "$server" = "PUBLIC_RESPONSE: Hello, Ada!"
set +e
trace="$(bun dist/client-entry.js --trace-probe 2>&1)"
code=$?
set -e
test "$code" -ne 0
printf '%s' "$trace" | grep -F "PUBLIC_RENDER_PROBE" >/dev/null
printf '%s' "$trace" | grep -F "/app/src/client/render.ts" >/dev/null
echo "FINAL_PROSPECTIVE_PROBES_PASS"
