#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime import livebench_legacy15_end2end_exact_synthetic_audit_v2 as audit

EXPECTED_BLOBS = {
    "canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py": "e986035ff68b53c0dc7a7eb478f6e3d8882214aa",
    "canonical/runtime/livebench_legacy_visible_constraint_compiler_v4.py": "721207ba39d502e3f610289578e9d5bab78b1fcc",
    "canonical/runtime/livebench_frozen_active_legacy15_v1.py": "34440ee69322e9d519cbe656cb03c55683a8b9c6",
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_general_composer_v1.py": "34ecf1a082faae4e6ac273689101f8e8d75933e4",
    "canonical/runtime/livebench_legacy15_joint_witness_v1.py": "6b83d32be3840f815cb04afb51e473069dc17fe2",
    "canonical/runtime/livebench_legacy15_joint_router_v2.py": "e133432996a927e0f8fc3ed9a3cddf1479feba7f",
    "canonical/runtime/livebench_legacy15_end2end_exact_synthetic_audit_v2.py": "7ea615d11c0ceea95b4fb7a2143d37887bc3b80a",
}

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def main() -> int:
    actual = {p: git_blob_sha(Path(p)) for p in EXPECTED_BLOBS}
    if actual != EXPECTED_BLOBS:
        print(json.dumps({"status":"FAIL_SUBJECT_BLOB_MISMATCH","expected":EXPECTED_BLOBS,"actual":actual}, sort_keys=True))
        return 2

    result = audit.audit(Path("/tmp/livebench"), 250)
    summary = {
        "status": result["status"],
        "bindings": result["bindings"],
        "scope": result["scope"],
        "results": result["results"],
        "by_archetype": result["by_archetype"],
        "by_profile": result["by_profile"],
        "by_size": result["by_size"],
        "runtime_errors": result["runtime_errors"],
        "exact_failed_instruction_ids": result["exact_failed_instruction_ids"],
        "failed_identity_shapes_top": result["failed_identity_shapes_top"],
        "failure_samples": result["failure_samples"],
        "subject_blobs": actual,
        "hard_nonclaims": result["hard_nonclaims"],
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if result["status"].startswith("PASS__") else 1

if __name__ == "__main__":
    raise SystemExit(main())
