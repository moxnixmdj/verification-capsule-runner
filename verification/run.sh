#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python - <<'PY'
from pathlib import Path
from hashlib import sha1
expected = {
    "canonical/runtime/terminal_autopilot_v1.py": "78fa2cbabf8ed5e70de8b3ed987b510ca033076b",
    "canonical/tests/test_terminal_autopilot_v1.py": "0d21826088c58bf5d3d885610c82061bd5f148b4",
}
for rel, want in expected.items():
    data = Path(rel).read_bytes()
    got = sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    assert got == want, (rel, got, want)
    print("EXACT_BLOB_PASS", rel, got)
PY
PYTHONPATH=. python -m unittest canonical.tests.test_terminal_autopilot_v1 -v
