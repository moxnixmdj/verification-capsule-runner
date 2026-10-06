from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from canonical.runtime.h100_zero_learned_tool_trace_normalizer_v1 import (
    normalize_tool_trace,
)

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/governance/H100_ZERO_LEARNED_TOOL_TRACE_VARIATION_PREEXPOSURE_V1.json":
        "b280663c459d72e3e6081130a3cdb8680a668b64",
    "canonical/governance/H100_ZERO_LEARNED_TOOL_TRACE_NORMALIZER_CANDIDATE_V1.json":
        "6f9b10c905ba3b33e5c687a1253655ead997747a",
    "canonical/runtime/h100_zero_learned_tool_trace_normalizer_v1.py":
        "c5b8018c9a62fcec85de46b0ace1be0bd0ddbd06",
    "canonical/tests/test_h100_zero_learned_tool_trace_normalizer_v1.py":
        "d8e61fbd11e377c77df0ee49e593fdad8f7bf53a",
}
ALLOWED_IMPORT_ROOTS = {"__future__", "math", "typing"}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def verify_exact_blobs() -> None:
    for rel, expected in EXPECTED.items():
        got = git_blob_sha((ROOT / rel).read_bytes())
        assert got == expected, (rel, got, expected)


def verify_runtime_dependency_surface() -> None:
    path = ROOT / "canonical/runtime/h100_zero_learned_tool_trace_normalizer_v1.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots <= ALLOWED_IMPORT_ROOTS, roots


def check(payload, hint, status, rows) -> None:
    out = normalize_tool_trace(payload, inputs=["x", "z"], target="y", format_hint=hint)
    assert out["status"] == status, out
    assert out["rows"] == rows, out
    assert out["persistent_learned_bytes"] == 0
    assert out["external_frontier_model_calls"] == 0
    assert out["external_learned_capability_calls"] == 0


def verify_fresh_challenges() -> None:
    check(
        [{"params":{"x":7,"z":2},"output":{"y":9}}],
        "JSON_ROWS",
        "TYPED_NUMERIC_SCHEMA_COMPILED",
        [{"x":7.0,"z":2.0,"y":9.0}],
    )
    check(
        [
            {"call_id":"q","attempt":1,"event":"request","data":{"x":1,"z":4}},
            {"call_id":"q","attempt":1,"event":"error","data":{"kind":"transient"}},
            {"call_id":"q","attempt":2,"event":"request","data":{"x":1,"z":4}},
            {"call_id":"q","attempt":2,"event":"response","data":{"y":5}},
        ],
        "EVENT_STREAM",
        "TYPED_NUMERIC_SCHEMA_COMPILED",
        [{"x":1.0,"z":4.0,"y":5.0}],
    )
    check(
        [
            {"call_id":"q","attempt":1,"event":"request","data":{"x":1,"z":4}},
            {"call_id":"q","attempt":1,"event":"error","data":{"kind":"transient"}},
            {"call_id":"q","attempt":2,"event":"request","data":{"x":2,"z":4}},
            {"call_id":"q","attempt":2,"event":"response","data":{"y":6}},
        ],
        "EVENT_STREAM",
        "ABSTAIN_TRACE_CONFLICT",
        [],
    )
    check(
        [
            {"call_id":"q","event":"request","data":{"x":2,"z":2}},
            {"call_id":"q","event":"response","data":{"y":4}},
            {"call_id":"q","event":"response","data":{"y":4}},
        ],
        "EVENT_STREAM",
        "TYPED_NUMERIC_SCHEMA_COMPILED",
        [{"x":2.0,"z":2.0,"y":4.0}],
    )
    check(
        [
            {"call_id":"b","event":"request","data":{"x":4,"z":5}},
            {"call_id":"a","event":"request","data":{"x":1,"z":1}},
            {"call_id":"a","event":"response","data":{"y":2}},
            {"call_id":"b","event":"response","data":{"y":9}},
        ],
        "EVENT_STREAM",
        "TYPED_NUMERIC_SCHEMA_COMPILED",
        [{"x":4.0,"z":5.0,"y":9.0},{"x":1.0,"z":1.0,"y":2.0}],
    )


if __name__ == "__main__":
    verify_exact_blobs()
    verify_runtime_dependency_surface()
    verify_fresh_challenges()
    print("PASS exact blobs, dependency surface, and 5 fresh tool-trace challenges")
