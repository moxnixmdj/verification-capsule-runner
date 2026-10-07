from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from canonical.runtime.channel_dominator_verifier_v1 import SCHEMA, verify_channel_graph

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/channel_dominator_verifier_v1.py": "598727a9b7c1b624e89ea00ef7760955892e61e9",
    "canonical/tests/test_channel_dominator_verifier_v1.py": "1d2bb4de093ac3532301dd4a9774ba3674ed7f0a",
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def require(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def cert():
    return {
        "schema": SCHEMA,
        "source_bindings": [
            {
                "path": "canonical/runtime/channel_dominator_verifier_v1.py",
                "git_blob_sha": EXPECTED["canonical/runtime/channel_dominator_verifier_v1.py"],
            }
        ],
        "channel_totality_receipt": {
            "path": "canonical/verification/placeholder-totality-receipt.json",
            "git_blob_sha": "2" * 40,
            "scope_complete": True,
            "static_edges_complete": True,
            "dynamic_edges_complete": True,
            "independent_or_objective": True,
        },
        "nodes": ["ENTRY", "PRE", "AUTH", "CAPSULE", "ACTION", "EFFECT", "STATE"],
        "entrypoints": ["ENTRY"],
        "mediators": [
            {"node": "AUTH", "class": "AUTHORITY_GUARD"},
            {"node": "CAPSULE", "class": "STATE_CAPSULE"},
        ],
        "edges": [
            {"id": "e0", "from": "ENTRY", "to": "PRE", "kind": "CONTROL", "load_bearing": False, "required_mediators": []},
            {"id": "e1", "from": "PRE", "to": "AUTH", "kind": "CONTROL", "load_bearing": False, "required_mediators": []},
            {"id": "e2", "from": "AUTH", "to": "CAPSULE", "kind": "CONTROL", "load_bearing": False, "required_mediators": []},
            {"id": "e3", "from": "CAPSULE", "to": "ACTION", "kind": "CONTROL", "load_bearing": False, "required_mediators": []},
            {"id": "effect", "from": "ACTION", "to": "EFFECT", "kind": "MATERIAL_EFFECT", "load_bearing": True, "required_mediators": ["AUTH"]},
            {"id": "state", "from": "ACTION", "to": "STATE", "kind": "STATE_USE", "load_bearing": True, "required_mediators": ["CAPSULE"]},
        ],
        "dynamic_sites": [
            {
                "id": "dispatch",
                "status": "REGISTERED",
                "source_ref": "independent:dispatch",
                "registered_edge_ids": ["effect"],
            }
        ],
    }


def main():
    for rel, expected in EXPECTED.items():
        actual = git_blob_sha((ROOT / rel).read_bytes())
        require(actual == expected, f"exact blob mismatch {rel}: {actual} != {expected}")

    good = cert()
    verdict = verify_channel_graph(good, root=ROOT)
    require(verdict["status"] == "PASS", f"baseline rejected: {verdict}")

    bypasses = 0
    for src in ("ENTRY", "PRE"):
        bad = copy.deepcopy(good)
        bad["edges"].append({
            "id": "bypass-" + src,
            "from": src,
            "to": "ACTION",
            "kind": "CONTROL",
            "load_bearing": False,
            "required_mediators": [],
        })
        result = verify_channel_graph(bad, root=ROOT)
        require(result["status"] == "FAIL_CLOSED", f"bypass admitted: {src}: {result}")
        require("MEDIATOR_BYPASS" in result["reason"], f"wrong bypass failure: {result}")
        bypasses += 1

    bad = copy.deepcopy(good)
    bad["dynamic_sites"][0]["status"] = "UNKNOWN"
    require(verify_channel_graph(bad, root=ROOT)["status"] == "FAIL_CLOSED", "unknown dynamic site admitted")

    bad = copy.deepcopy(good)
    bad["channel_totality_receipt"]["dynamic_edges_complete"] = False
    require(verify_channel_graph(bad, root=ROOT)["status"] == "FAIL_CLOSED", "false dynamic totality admitted")

    bad = copy.deepcopy(good)
    bad["edges"][4]["required_mediators"] = []
    require(verify_channel_graph(bad, root=ROOT)["status"] == "FAIL_CLOSED", "unmediated effect admitted")

    bad = copy.deepcopy(good)
    bad["source_bindings"][0]["git_blob_sha"] = "f" * 40
    result = verify_channel_graph(bad, root=ROOT)
    require(result["status"] == "FAIL_CLOSED", "source drift admitted")
    require("SOURCE_BINDING_DRIFT" in result["reason"], f"wrong drift failure: {result}")

    print(json.dumps({
        "status": "PASS",
        "brain_pr": 2208,
        "brain_head": "16938d6abd953eb7751c1452713e7e1eb40346cd",
        "exact_blobs": EXPECTED,
        "independent_bypass_variants_checked": bypasses,
        "verified": [
            "exact_blob_identity",
            "multi_mediator_dominance",
            "bypass_rejection",
            "unknown_dynamic_site_rejection",
            "false_dynamic_totality_rejection",
            "unmediated_load_bearing_edge_rejection",
            "source_binding_drift_rejection",
        ],
        "not_verified": [
            "scope_completeness_of_any_real_astra_runtime_channel_graph",
            "semantic_soundness_of_authority_or_invariant_guards",
            "terminal_acceptance_credit",
        ],
        "fresh_reality_units_consumed": 0,
        "acceptance_credit_delta": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
