from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path("capsules/terminal_atomic_closure_v4")
SNAP=ROOT/"snapshot"
MAN=ROOT/"manifests"
CAP=ROOT/"TERMINAL_ATOMIC_CLOSURE_CAPSULE_V4.json"

def git_blob(p):
    b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def canon(o):
    return json.dumps(o,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def sha256(b): return hashlib.sha256(b).hexdigest()

def main():
    cap=json.loads(CAP.read_text())
    assert cap["schema"]=="PROJECT_BRAIN_TERMINAL_ATOMIC_CLOSURE_CAPSULE_V4"
    assert cap["execution_snapshot"]["commit_sha"]=="3757d6777ef0122d21ce1f1ee2e6d6a5e560aeb5"
    assert cap["verified_for_beacon"] is False
    assert cap["prebeacon_invariants"]["post_freeze_beacon"] is None
    assert cap["prebeacon_invariants"]["terminal_results_observed"]==0
    ids=[]; encoded=[]
    for row in cap["ordered_components"]:
        ids.append(row["id"])
        p=MAN/Path(row["path"]).name
        assert p.is_file(),p
        assert git_blob(p)==row["git_blob_sha"],(p,git_blob(p),row["git_blob_sha"])
        obj=json.loads(p.read_text())
        assert obj["execution_snapshot_commit"]==cap["execution_snapshot"]["commit_sha"]
        cj=canon(obj)
        assert sha256(cj)==row["canonical_json_sha256"],row["id"]
        encoded.append(cj)
        for rel,expected in (obj.get("bindings") or {}).items():
            q=SNAP/rel
            assert q.is_file(),rel
            assert git_blob(q)==expected,(rel,git_blob(q),expected)
    assert ids==["candidate_blob_manifest","evaluator_oracle_manifest","population_manifest","dependency_manifest","acceptance_rule_manifest"]
    pkg=sha256(b"".join(encoded))
    assert pkg==cap["package_commitment"],(pkg,cap["package_commitment"])
    # Cross-manifest safety invariants.
    assert cap["prebeacon_invariants"]["all_component_execution_snapshot_commits_identical"] is True
    assert cap["prebeacon_invariants"]["beacon_known_before_freeze"] is False
    assert cap["prebeacon_invariants"]["candidate_mutation_after_freeze_allowed"] is False
    assert cap["prebeacon_invariants"]["case_replacement"] is False
    assert cap["prebeacon_invariants"]["tuning_replay"] is False
    auth=json.loads((SNAP/"canonical/governance/TERMINAL_WAVE_EXECUTION_AUTHORITY_V1.json").read_text())
    routes=json.loads((SNAP/"canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json").read_text())
    assert auth.get("execution_authority") is True
    assert auth.get("terminal_results_observed")==0
    assert auth.get("fresh_terminal_evidence_consumed")==0
    assert routes.get("launch_authority") is True
    assert routes.get("route_count")==12 and routes.get("bound_executor_count")==12
    assert routes.get("terminal_results_observed")==0
    print("TERMINAL_ATOMIC_CLOSURE_V4_PASS",pkg)
    return 0
if __name__=="__main__": raise SystemExit(main())
