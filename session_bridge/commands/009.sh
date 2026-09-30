node - <<'NODE'
const fs=require('fs')
const p='/app/tests/submitLead.test.ts'
let s=fs.readFileSync(p,'utf8')
s=s.replace("import * as os from 'node:os'\n","")
s=s.replace("let tmp = ''\nlet oldCwd = ''\n","const tmp = '/app'\n")
s=s.replace("beforeEach(() => {\n  oldCwd = process.cwd()\n  tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lead-pipeline-'))\n  process.chdir(tmp)\n})\n\nafterEach(() => {\n  process.chdir(oldCwd)\n  fs.rmSync(tmp, { recursive: true, force: true })\n})",
"beforeEach(() => {\n  fs.rmSync(path.join(tmp, 'output'), { recursive: true, force: true })\n})\n\nafterEach(() => {\n  fs.rmSync(path.join(tmp, 'output'), { recursive: true, force: true })\n})")
fs.writeFileSync(p,s)
NODE
