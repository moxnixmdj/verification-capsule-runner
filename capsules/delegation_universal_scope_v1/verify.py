from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

ROOT=pathlib.Path(__file__).resolve().parent
manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))

def git_blob_sha(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,expected in manifest["exact_brain_blobs"].items():
    path=ROOT/rel
    assert path.exists(),("missing",rel)
    actual=git_blob_sha(path)
    assert actual==expected,(rel,actual,expected)

sys.path.insert(0,str(ROOT))

subprocess.run([
    sys.executable,"-m","py_compile",
    str(ROOT/"canonical/runtime/delegation_protocol_scope_completeness_verifier_v1.py"),
    str(ROOT/"canonical/runtime/delegation_whole_scope_candidate_v2.py"),
    str(ROOT/"canonical/runtime/delegation_whole_scope_proof_v2.py"),
    str(ROOT/"canonical/runtime/delegation_structural_variety_proof_v3.py"),
    str(ROOT/"canonical/runtime/scope_equivalent_proof_gate_v2.py"),
],check=True)

subprocess.run([
    sys.executable,"-m","unittest",
    "canonical.tests.test_delegation_protocol_scope_completeness_v1","-v"
],cwd=ROOT,check=True)

from canonical.runtime.delegation_protocol_scope_completeness_verifier_v1 import execute
out=execute()

assert out["status"].startswith("PASS"),out
assert out["scope_complete"] is True,out
assert out["basis"]=="UNIVERSAL_FORMAL_SCOPE_PROOF",out
assert out["finite_sample_used_as_exhaustive_proof"] is False,out
assert out["family_to_contract_mapping"]==["TASK_TO_DELEGATION_GRAPH_001"],out
assert out["population_relation"]=="CANDIDATE_SUPERSET_PROVEN",out
assert out["environment_relation"]=="EXACT",out
assert out["information_relation"]=="EXACT_CANDIDATE_VISIBLE_INFORMATION",out
assert out["oracle_relation"]=="CANDIDATE_STRONGER_PROVEN",out
assert out["unresolved_required_dimensions"]==[],out
assert out["new_reality_units_consumed"]==0
assert out["capability_credit_delta"]==0
assert out["family_credit_delta"]==0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

cert=json.loads((ROOT/"canonical/governance/DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE_V1.json").read_text())
assert cert["admissible_basis"]=="UNIVERSAL_FORMAL_SCOPE_PROOF"
assert "DO_NOT_RELABEL_132_FINITE_CASES_AS_EXHAUSTIVE" in cert["hard_rules"]
assert cert["capability_credit_delta"]==0
assert cert["family_credit_delta"]==0

print(json.dumps({
    "status":"PASS",
    "exact_brain_blob_count":len(manifest["exact_brain_blobs"]),
    "scope_complete":True,
    "basis":"UNIVERSAL_FORMAL_SCOPE_PROOF",
    "family":"SUBAGENT_DELEGATION_AND_COORDINATION",
    "behavior_id":"TASK_TO_DELEGATION_GRAPH_001",
    "finite_sample_used_as_exhaustive_proof":False,
    "new_reality_units_consumed":0,
    "credit_delta":0,
},indent=2,sort_keys=True))
