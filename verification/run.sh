#!/usr/bin/env bash
set -euo pipefail
python -m unittest canonical.tests.test_terminal_causal_depth_controller_v1
python - <<'PY'
import hashlib
from pathlib import Path
expected = {
  "canonical/runtime/terminal_causal_depth_controller_v1.py": "61bb94594808d6028af8a581a97e9118e801b4b2",
  "canonical/tests/test_terminal_causal_depth_controller_v1.py": "59516587e33c194820c1553c9cfbfadb7307fb46",
}
for p, git_blob in expected.items():
    data=Path(p).read_bytes()
    blob=("blob "+str(len(data))+"\0").encode()+data
    got=hashlib.sha1(blob).hexdigest()
    if got != git_blob:
        raise SystemExit(f"blob mismatch {p}: {got} != {git_blob}")
print("exact candidate blobs and behavior pass")
PY
