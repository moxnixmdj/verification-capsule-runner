set -e
cd /app
python - <<'PY'
import importlib.util, sys
print(sys.version)
for m in ['numpy','scipy','sklearn','pandas']:
    print(m, bool(importlib.util.find_spec(m)))
PY
