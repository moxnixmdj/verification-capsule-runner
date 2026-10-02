from __future__ import annotations
import hashlib, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))

def blob_sha(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,expected in m["exact_brain_blobs"].items():
    actual=blob_sha(ROOT/rel)
    assert actual==expected,(rel,actual,expected)

adj=json.loads((ROOT/"canonical/governance/TB4_PROOF_ATOM_FALSIFICATION_ADJUDICATION_V1.json").read_text())
assert str(adj["status"]).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert adj["atom"]["parent_certificate_id"]=="TB4_ATTAINABLE_ROUTE_CERTIFICATE"
assert adj["atom"]["proposition"]=="MACHINE_VERIFIED_TB4_ROUTE_UPPER_BOUND_GE_220"
assert adj["atom"]["target_predicate"]=="CODING_TB4_GE_66_4"
assert adj["proof"]["maximum_attainable_successes"]==180
assert adj["proof"]["required_successes"]==220
assert adj["proof"]["inequality"]=="180_LT_220"
assert adj["public_reverification"]["conclusion"]=="success"

sys.path.insert(0,str(ROOT))
subprocess.run([sys.executable,"-m","py_compile",
 str(ROOT/"canonical/runtime/terminal_certificate_cut_v1.py"),
 str(ROOT/"canonical/runtime/canonical_proof_atom_basis_v2.py"),
 str(ROOT/"canonical/runtime/terminal_certificate_falsification_pruner_v1.py")],check=True)
subprocess.run([sys.executable,"-m","unittest",
 "canonical.tests.test_terminal_certificate_falsification_pruner_v1","-v"],cwd=ROOT,check=True)

p=subprocess.run([sys.executable,"-m","canonical.runtime.terminal_certificate_falsification_pruner_v1"],
 cwd=ROOT,check=True,capture_output=True,text=True)
out=json.loads(p.stdout)
assert out["status"].startswith("PASS"),out
assert out["input_unresolved_predicate_count"]==31
assert out["input_certificate_count"]==17
assert out["active_certificate_count"]==16
assert out["pruned_certificate_ids"]==["TB4_ATTAINABLE_ROUTE_CERTIFICATE"]
assert out["covered_predicate_count_after_pruning"]==30
assert out["uncovered_predicates_after_pruning"]==["CODING_TB4_GE_66_4"]
assert out["executable_leaf_atom_count_after_pruning"]==39
assert out["executable_leaf_requirement_occurrence_count_after_pruning"]==39
assert out["capability_credit_delta"]==0
assert out["family_credit_delta"]==0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False
print(json.dumps({
 "status":"PASS",
 "exact_brain_blob_count":len(m["exact_brain_blobs"]),
 "route_falsification_consumed":True,
 "target_falsification_inferred":False,
 "active_certificates":out["active_certificate_count"],
 "covered_predicates":out["covered_predicate_count_after_pruning"],
 "uncovered_predicates":out["uncovered_predicates_after_pruning"],
 "executable_leaf_atoms":out["executable_leaf_atom_count_after_pruning"],
 "credit_delta":0
},indent=2,sort_keys=True))
