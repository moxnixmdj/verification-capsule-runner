#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python - <<'PY'
from pathlib import Path
from hashlib import sha1
expected = {
    "canonical/runtime/terminal_autopilot_v1.py": "6a3309dc598a1f7587d1bec09006729edbf7440e",
    "canonical/tests/test_terminal_autopilot_v1.py": "01f4808cde3bcf118a6316b5991cbdca1aea08ca",
}
for rel, want in expected.items():
    data = Path(rel).read_bytes()
    got = sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    assert got == want, (rel, got, want)
    print("EXACT_BLOB_PASS", rel, got)
PY
PYTHONPATH=. python -m unittest canonical.tests.test_terminal_autopilot_v1 -v
