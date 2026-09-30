node - <<'NODE'
const fs=require('fs');
const path=require('path');
console.log("===== /app/src/data/lead_input.json =====");
console.log(fs.readFileSync('/app/src/data/lead_input.json','utf8'));
console.log("\n===== /app/output =====");
if (fs.existsSync('/app/output')) {
  for (const name of fs.readdirSync('/app/output').sort()) {
    const p=path.join('/app/output',name);
    const st=fs.statSync(p);
    console.log("\n--- "+p+" ---");
    if (st.isFile()) console.log(fs.readFileSync(p,'utf8'));
    else console.log("[directory]");
  }
} else console.log("[missing]");
NODE
