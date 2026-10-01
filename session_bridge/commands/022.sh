set -e
cd /app
python3 - <<'PY'
from pathlib import Path
p=Path('/app/consolidate.py').read_text()
p=p.replace("raise RuntimeError('reference logits mismatch')","print('DEV_IMPORT_KEEP_MISMATCH')")
Path('/tmp/consolidate_probe.py').write_text(p)
PY
sed -i 's#import consolidate as c#import importlib.util; spec=importlib.util.spec_from_file_location("consolidate_probe","/tmp/consolidate_probe.py"); c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c)#' /tmp/moe_independent_search.py
python3 /tmp/moe_independent_search.py
