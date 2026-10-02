from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

expected=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))
paths={
    "canonical/runtime/abductive_residual_theorem_v2.py":ROOT/"runtime.py",
    "canonical/tests/test_abductive_residual_theorem_v2.py":ROOT/"test.py",
    "canonical/governance/ABDUCTIVE_RESIDUAL_THEOREM_V2_CANDIDATE.json":ROOT/"governance.json",
}
actual={k:git_blob_sha(v) for k,v in paths.items()}
assert actual==expected["exact_brain_blobs"], (actual,expected["exact_brain_blobs"])

spec=importlib.util.spec_from_file_location("abductive_v2",ROOT/"runtime.py")
mod=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod)

def edge(edge_id,lhs,rhs):
    return {
        "edge_id":edge_id,
        "if_all":lhs,
        "then":rhs,
        "verified":True,
        "independent":True,
        "receipt":"r://"+edge_id,
    }

# Basic exact reduction.
out=mod.evaluate({
    "targets":["T"],
    "baseline_facts":["A"],
    "implications":[edge("e1",["A","B"],["T"])],
})
assert out["exact"] is True, out
assert out["minimum_joint_residual_size"]==1, out
assert out["minimum_joint_residual_sets"]==[["B"]], out

# Critical global-joint regression: locally shortest {A} is globally worse
# than locally longer {B,C} shared with T2.
out=mod.evaluate({
    "targets":["T1","T2"],
    "baseline_facts":[],
    "implications":[
        edge("t1-short",["A"],["T1"]),
        edge("t1-shared",["B","C"],["T1"]),
        edge("t2-shared",["B","C"],["T2"]),
    ],
})
assert out["exact"] is True, out
assert out["target_residuals"]["T1"]["minimum_residual_sets"]==[["A"]], out
assert ["B","C"] in out["target_residuals"]["T1"]["all_inclusion_minimal_residual_sets"], out
assert out["minimum_joint_residual_size"]==2, out
assert out["minimum_joint_residual_sets"]==[["B","C"]], out

# More than 128 inclusion-minimal alternatives must never be labelled exact.
imp=[]; groups=[]
for i in range(8):
    g=f"G{i}"; groups.append(g)
    imp.append(edge(f"x{i}",[f"X{i}"],[g]))
    imp.append(edge(f"y{i}",[f"Y{i}"],[g]))
imp.append(edge("terminal",groups,["T"]))
out=mod.evaluate({"targets":["T"],"baseline_facts":[],"implications":imp})
assert out["status"]=="BOUNDED_INCOMPLETE__NO_GLOBAL_EXACTNESS_CLAIM", out
assert out["exact"] is False and out["bounded_incomplete"] is True, out
assert out["bounded_events"], out

# Cycles unsupported by facts/leaves cannot self-prove.
out=mod.evaluate({
    "targets":["T"],
    "baseline_facts":[],
    "implications":[edge("e1",["A"],["T"]),edge("e2",["T"],["A"])],
})
assert out["status"]=="RESIDUAL_GRAPH_CONTAINS_UNREACHABLE_TARGETS", out
assert out["exact"] is False, out

# Governance remains zero-credit/no authority.
gov=json.loads((ROOT/"governance.json").read_text(encoding="utf-8"))
assert gov["capability_credit_delta"]==0 and gov["family_credit_delta"]==0
assert gov["execution_authority"] is False and gov["promotion_authority"] is False
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0
assert out["execution_authority"] is False and out["promotion_authority"] is False

print(json.dumps({
    "status":"PASS",
    "exact_blob_shas":actual,
    "global_joint_nonshortest_regression":"PASS",
    "cap_bound_fail_closed":"PASS",
    "cycle_self_proof_rejected":"PASS",
    "credit_delta":0
},indent=2,sort_keys=True))
