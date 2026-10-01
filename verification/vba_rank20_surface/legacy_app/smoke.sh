#!/usr/bin/env bash
set -euo pipefail
python -m venv /tmp/r20venv
/tmp/r20venv/bin/python -m pip install --upgrade pip
/tmp/r20venv/bin/pip install fastapi uvicorn
/tmp/r20venv/bin/python - <<'PY'
import fastapi,uvicorn,sqlite3
print("PY_RUNTIME_PASS",fastapi.__version__,uvicorn.__version__,sqlite3.sqlite_version)
PY
node --version
npm --version
sqlite3 --version
mkdir -p /tmp/r20ui/src
cd /tmp/r20ui
cat > package.json <<'JSON'
{"scripts":{"build":"vite build","preview":"vite preview"},"dependencies":{"@vitejs/plugin-react":"latest","vite":"latest","react":"latest","react-dom":"latest"},"devDependencies":{}}
JSON
cat > index.html <<'HTML'
<div id="root"></div><script type="module" src="/src/main.jsx"></script>
HTML
cat > src/main.jsx <<'JS'
import React from 'react'; import {createRoot} from 'react-dom/client';
createRoot(document.getElementById('root')).render(React.createElement('div',{'data-testid':'form:smoke'},'ready'));
JS
npm install
npm run build
cat > /tmp/r20app.py <<'PY'
from fastapi import FastAPI
app=FastAPI()
@app.get("/api/health")
def health(): return {"ok":True}
PY
/tmp/r20venv/bin/python -m uvicorn r20app:app --app-dir /tmp --host 127.0.0.1 --port 8111 >/tmp/backend.log 2>&1 &
B=$!
npm run preview -- --host 127.0.0.1 --port 4173 >/tmp/frontend.log 2>&1 &
F=$!
ok=0
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8111/api/health >/dev/null && curl -fsS http://127.0.0.1:4173/ >/dev/null; then ok=1; break; fi
  sleep 1
done
kill $B $F || true
test "$ok" = 1
echo EXACT_SURFACE_REACT_FASTAPI_SQLITE_STARTUP_SMOKE_PASS
