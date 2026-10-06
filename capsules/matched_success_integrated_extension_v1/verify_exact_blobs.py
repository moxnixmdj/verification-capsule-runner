from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor"
manifest = json.loads((ROOT / "blob_manifest.json").read_text())
errors = []
for rel, expected in sorted(manifest.items()):
    path = VENDOR / rel
    if not path.exists():
        errors.append("MISSING:" + rel)
        continue
    data = path.read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + bytes([0]) + data).hexdigest()
    if actual != expected:
        errors.append("SHA_MISMATCH:" + rel + ":" + actual + ":" + expected)
if errors:
    raise SystemExit("\n".join(errors))
print("EXACT_BLOB_VERIFICATION_PASS:" + str(len(manifest)))
