"""Independent finite falsification for Brain PR #2223 Root3 channel dominator.

The candidate implementation is treated as the subject under test. This verifier
uses an independently written reachability oracle and exhaustively enumerates all
directed graphs on four fixed nodes (12 possible non-self edges = 4096 graphs).
It also checks malformed/dynamic/binding/digest failure modes.

This receipt verifies the algorithm on the frozen candidate blob only. It does
not prove the future current-runtime channel manifest is scope complete and does
not prove any predicate-specific guard is semantically sound.
"""
from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

CANDIDATE = Path("candidate/root3_channel_dominator_pr2223_v1.py")
EXPECTED_GIT_BLOB_SHA = "d8f0a4ace85e0a89343b96bb4e3a479c18e8db26"


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    payload = b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    return hashlib.sha1(payload).hexdigest()


def load_candidate():
    actual = git_blob_sha(CANDIDATE)
    assert actual == EXPECTED_GIT_BLOB_SHA, (actual, EXPECTED_GIT_BLOB_SHA)
    spec = importlib.util.spec_from_file_location("candidate_root3_dominator", CANDIDATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reachable(edges, starts, target, blocked=None):
    adjacency = {}
    for src, dst in edges:
        if src == blocked or dst == blocked:
            continue
        adjacency.setdefault(src, []).append(dst)
    seen = set()
    stack = [x for x in starts if x != blocked]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        if node == target:
            return True
        stack.extend(adjacency.get(node, ()))
    return False


def base_manifest(edge_pairs):
    ids = ["ENTRY", "CTRL", "AUTH", "SINK"]
    return {
        "source_blobs": [
            {"path": "canonical/runtime/frozen_subject.py", "git_blob_sha": "1" * 40}
        ],
        "entrypoints": ["ENTRY"],
        "nodes": [
            {"id": "ENTRY", "kind": "RUNTIME_ENTRYPOINT"},
            {"id": "CTRL", "kind": "CONTROL"},
            {"id": "AUTH", "kind": "MATERIAL_EFFECT_MEDIATOR"},
            {"id": "SINK", "kind": "MATERIAL_EFFECT_SINK"},
        ],
        "edges": [
            {
                "id": f"e{i}",
                "from": src,
                "to": dst,
                "dynamic": False,
            }
            for i, (src, dst) in enumerate(edge_pairs)
        ],
        "mediator_bindings": [
            {
                "sink_id": "SINK",
                "required_mediator_id": "AUTH",
                "mediator_class": "AUTHORITY_GUARD",
                "predicate_ids": ["IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS"],
            }
        ],
        "dynamic_edge_registry_complete": True,
        "unknown_dynamic_edges": [],
        "unclassified_load_bearing_channels": [],
    }


def expected_for_graph(edge_pairs):
    live = reachable(edge_pairs, ["ENTRY"], "SINK")
    bypass = reachable(edge_pairs, ["ENTRY"], "SINK", blocked="AUTH")
    return live and not bypass


def exhaustive_graph_check(candidate):
    nodes = ["ENTRY", "CTRL", "AUTH", "SINK"]
    possible = [(a, b) for a in nodes for b in nodes if a != b]
    checked = 0
    pass_expected = 0
    fail_expected = 0
    for mask in range(1 << len(possible)):
        edges = [possible[i] for i in range(len(possible)) if mask & (1 << i)]
        expected = expected_for_graph(edges)
        actual = bool(candidate.evaluate(base_manifest(edges))["pass"])
        if actual != expected:
            raise AssertionError({
                "mask": mask,
                "edges": edges,
                "expected": expected,
                "actual": actual,
                "result": candidate.evaluate(base_manifest(edges)),
            })
        checked += 1
        pass_expected += int(expected)
        fail_expected += int(not expected)
    return {
        "graph_universe_size": 1 << len(possible),
        "graphs_checked": checked,
        "pass_expected": pass_expected,
        "fail_expected": fail_expected,
    }


def targeted_falsification(candidate):
    results = {}

    linear = base_manifest([("ENTRY","CTRL"),("CTRL","AUTH"),("AUTH","SINK")])
    assert candidate.evaluate(linear)["pass"] is True
    results["linear_pass"] = True

    direct = base_manifest([
        ("ENTRY","CTRL"),("CTRL","AUTH"),("AUTH","SINK"),("CTRL","SINK")
    ])
    out = candidate.evaluate(direct)
    assert out["pass"] is False
    assert "MEDIATOR_BYPASS:SINK:AUTH" in out["errors"]
    assert out["bypasses"]
    results["direct_bypass_killed"] = True

    unknown = base_manifest([("ENTRY","AUTH"),("AUTH","SINK")])
    unknown["unknown_dynamic_edges"] = ["opaque-plugin-edge"]
    out = candidate.evaluate(unknown)
    assert out["pass"] is False
    assert "UNKNOWN_DYNAMIC_EDGE:opaque-plugin-edge" in out["errors"]
    results["unknown_dynamic_killed"] = True

    unclassified = base_manifest([("ENTRY","AUTH"),("AUTH","SINK")])
    unclassified["unclassified_load_bearing_channels"] = ["mystery-sink"]
    out = candidate.evaluate(unclassified)
    assert out["pass"] is False
    assert "UNCLASSIFIED_LOAD_BEARING_CHANNEL:mystery-sink" in out["errors"]
    results["unclassified_channel_killed"] = True

    unbound = base_manifest([("ENTRY","AUTH"),("AUTH","SINK")])
    unbound["mediator_bindings"] = []
    out = candidate.evaluate(unbound)
    assert out["pass"] is False
    assert "LOAD_BEARING_SINK_UNBOUND:SINK" in out["errors"]
    results["unbound_sink_killed"] = True

    unreachable = base_manifest([("ENTRY","CTRL"),("AUTH","SINK")])
    out = candidate.evaluate(unreachable)
    assert out["pass"] is False
    assert "DECLARED_LOAD_BEARING_SINK_UNREACHABLE:SINK" in out["errors"]
    results["unreachable_declared_sink_killed"] = True

    wrong_kind = base_manifest([("ENTRY","AUTH"),("AUTH","SINK")])
    wrong_kind["mediator_bindings"][0]["mediator_class"] = "STATE_CAPSULE"
    out = candidate.evaluate(wrong_kind)
    assert out["pass"] is False
    assert "STATE_CAPSULE_MEDIATOR_KIND_INVALID:SINK" in out["errors"]
    results["wrong_mediator_kind_killed"] = True

    digest_a = candidate.evaluate(linear)["graph_manifest_sha256"]
    drift = json.loads(json.dumps(linear))
    drift["source_blobs"][0]["git_blob_sha"] = "2" * 40
    digest_b = candidate.evaluate(drift)["graph_manifest_sha256"]
    assert digest_a != digest_b
    results["source_blob_drift_changes_digest"] = True

    mismatch = json.loads(json.dumps(linear))
    mismatch["expected_graph_manifest_sha256"] = "0" * 64
    out = candidate.evaluate(mismatch)
    assert out["pass"] is False
    assert "GRAPH_MANIFEST_DIGEST_MISMATCH" in out["errors"]
    results["declared_digest_mismatch_killed"] = True

    shared = base_manifest([("ENTRY","CTRL"),("CTRL","AUTH"),("AUTH","SINK")])
    shared["nodes"].extend([
        {"id":"CAPSULE","kind":"STATE_OR_EVIDENCE_MEDIATOR"},
        {"id":"STATE_USE","kind":"CROSS_ROLE_STATE_OR_EVIDENCE_USE"},
    ])
    shared["edges"].extend([
        {"id":"state1","from":"CTRL","to":"CAPSULE","dynamic":False},
        {"id":"state2","from":"CAPSULE","to":"STATE_USE","dynamic":False},
    ])
    shared["mediator_bindings"].append({
        "sink_id":"STATE_USE",
        "required_mediator_id":"CAPSULE",
        "mediator_class":"STATE_CAPSULE",
        "predicate_ids":[
            "COMPOSITION_COMPONENT_SCOPED_PROOFS",
            "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
        ],
    })
    out = candidate.evaluate(shared)
    assert out["pass"] is True, out
    assert out["load_bearing_sink_count"] == 2
    results["shared_if_composition_graph_pass"] = True

    return results


def main():
    candidate = load_candidate()
    exhaustive = exhaustive_graph_check(candidate)
    targeted = targeted_falsification(candidate)
    receipt = {
        "schema": "PROJECT_BRAIN_ROOT3_CHANNEL_DOMINATOR_PR2223_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__EXHAUSTIVE_4096_GRAPH_ORACLE_EQUIVALENCE_PLUS_TARGETED_FAIL_CLOSED_FALSIFICATION",
        "candidate_git_blob_sha": EXPECTED_GIT_BLOB_SHA,
        "independent_oracle": "SEPARATELY_IMPLEMENTED_REACHABILITY_WITH_MEDIATOR_REMOVAL",
        "exhaustive": exhaustive,
        "targeted": targeted,
        "verified": [
            "FINITE_GRAPH_MEDIATOR_DOMINANCE_DECISION_MATCHES_INDEPENDENT_ORACLE_ON_ALL_4096_FOUR_NODE_DIRECTED_GRAPHS",
            "BYPASS_PATHS_FAIL",
            "UNKNOWN_DYNAMIC_EDGES_FAIL",
            "UNCLASSIFIED_LOAD_BEARING_CHANNELS_FAIL",
            "UNBOUND_AND_UNREACHABLE_DECLARED_SINKS_FAIL",
            "MEDIATOR_CLASS_MISMATCH_FAILS",
            "SOURCE_BLOB_DRIFT_CHANGES_GRAPH_DIGEST",
            "DECLARED_DIGEST_MISMATCH_FAILS",
            "SHARED_IF_AND_COMPOSITION_MEDIATOR_GRAPH_IS_SUPPORTED",
        ],
        "not_verified": [
            "CURRENT_BRAIN_RUNTIME_CHANNEL_DISCOVERY_COMPLETENESS",
            "CURRENT_DYNAMIC_EDGE_REGISTRY_TOTALITY",
            "CURRENT_BLOB_BINDING",
            "IF_AUTHORITY_GUARD_SEMANTIC_SOUNDNESS",
            "COMPOSITION_INVARIANT_GUARD_SEMANTIC_SOUNDNESS",
            "ANY_ACCEPTANCE_PREDICATE_CLOSURE",
        ],
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

# PR synchronization marker: run the independent verifier on this frozen subject.
