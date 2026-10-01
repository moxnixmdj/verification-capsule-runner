#!/usr/bin/env python3
"""Stage-B-only equivalent-surface feasibility smoke. Does not run rank20 task."""
import json, subprocess, sys, textwrap, time

def run(cmd, **kw):
    return subprocess.run(cmd, text=True, capture_output=True, check=False, **kw)

name="vba-rank20-stageb-surface"
run(["docker","rm","-f",name])
try:
    cp=run(["docker","run","-d","--name",name,"python:3.12-slim","sh","-lc","trap : TERM INT; while :; do sleep 3600; done"])
    if cp.returncode: raise SystemExit(cp.stderr)
    apt=run(["docker","exec",name,"sh","-lc","apt-get update >/dev/null && apt-get install -y --no-install-recommends bash ca-certificates curl nodejs npm sqlite3 >/dev/null"],timeout=300)
    if apt.returncode: raise SystemExit(apt.stderr[-4000:])
    py=run(["docker","exec",name,"sh","-lc","python3 -m venv /tmp/appvenv && /tmp/appvenv/bin/pip install --disable-pip-version-check -q fastapi==0.115.12 uvicorn==0.34.2 && /tmp/appvenv/bin/python -c 'import fastapi,uvicorn,sqlite3; print(fastapi.__version__)'"],timeout=300)
    if py.returncode: raise SystemExit(py.stderr[-4000:])
    npm_script=r"""
set -eu
mkdir -p /tmp/frontend && cd /tmp/frontend
cat > package.json <<'JSON'
{"scripts":{"build":"vite build"},"dependencies":{"@vitejs/plugin-react":"4.3.4","vite":"5.4.20","typescript":"5.7.3","react":"18.3.1","react-dom":"18.3.1"},"devDependencies":{}}
JSON
npm install --ignore-scripts --no-audit --no-fund >/dev/null
mkdir -p src
cat > index.html <<'EOF'
<div id="root"></div><script type="module" src="/src.jsx"></script>
EOF
cat > src.jsx <<'EOF'
import React from 'react'; import {createRoot} from 'react-dom/client'; createRoot(document.getElementById('root')).render(<div data-testid="form:frmCustomers">ok</div>);
EOF
cat > vite.config.js <<'EOF'
import {defineConfig} from 'vite'; import react from '@vitejs/plugin-react'; export default defineConfig({plugins:[react()]});
EOF
npm run build >/dev/null
test -f dist/index.html
"""
    npm=run(["docker","exec",name,"sh","-lc",npm_script],timeout=300)
    if npm.returncode: raise SystemExit(npm.stderr[-4000:])
    vers=run(["docker","exec",name,"sh","-lc","printf 'python='; python3 --version; printf 'node='; node --version; printf 'npm='; npm --version; printf 'sqlite='; sqlite3 --version | cut -d' ' -f1"])
    print(json.dumps({"schema":"VBA_RANK20_STAGE_B_EQUIVALENT_SURFACE_V1","pass":True,"versions":vers.stdout.strip().splitlines(),"task_execution":False,"hidden_verifier_read":False},indent=2))
finally:
    run(["docker","rm","-f",name])
