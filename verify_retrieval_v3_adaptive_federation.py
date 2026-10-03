#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/wikidata_language_bridge_v1.py": "1698a02f372a7ed6446d1519d9385dcff8619786",
    "canonical/runtime/adaptive_retrieval_query_expansion_v1.py": "180cce242914a0b7c0925c50579dd1e336b9ef35",
    "canonical/runtime/public_source_federation_v1.py": "3f69b3e8371fe3e5abc173c6c9fe17e9003a938b",
    "canonical/runtime/retrieval_adversarial_recall_benchmark_v1.py": "947f09640bc6e8ca98c4e3c2c975ab87071f6f1f",
    "canonical/tests/test_retrieval_v3_adaptive_federation.py": "b12ad4392cb5d7802507cce75dd90a3089169f4a",
}

def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

actual = {rel: git_blob_sha(ROOT / rel) for rel in EXPECTED}
assert actual == EXPECTED, {"expected": EXPECTED, "actual": actual}

cp = subprocess.run(
    [sys.executable, "-m", "unittest", "-v", "canonical.tests.test_retrieval_v3_adaptive_federation"],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
print(cp.stdout)
print(cp.stderr, file=sys.stderr)
assert cp.returncode == 0, cp.returncode

bp = subprocess.run(
    [sys.executable, "canonical/runtime/retrieval_adversarial_recall_benchmark_v1.py"],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
print(bp.stdout)
print(bp.stderr, file=sys.stderr)
assert bp.returncode == 0, bp.returncode
bench = json.loads(bp.stdout)
assert bench["status"] == "PASS", bench
assert bench["recall"] == 1.0, bench
assert bench["misses"] == [], bench
assert bench["unbridgeable_fixture"]["correct_state"] == "UNKNOWN", bench
assert bench["unbridgeable_fixture"]["nonexistence_allowed"] is False, bench

print("RETRIEVAL_V3_ADAPTIVE_FEDERATION_VERIFIED")
print(json.dumps({
    "exact_blobs": actual,
    "finite_declared_observable_recall": bench["recall"],
    "unbridgeable_state": bench["unbridgeable_fixture"]["correct_state"],
    "open_world_completeness_claim": False,
    "incremental_spend_usd": 0,
}, sort_keys=True))
