#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"terminal_finality_guard_v3"
OUT=ROOT/"terminal_finality_guard_v3_receipt.json"
EXPECTED={
  "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json": "f64901d9cde8eb8997f61ae15f885286001dabb7",
  "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json": "bcf12c8845e90e6bfdd689458586bdebd59824a3",
  "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json": "01abb91c114576ac340816b052724150258726ff",
  "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json": "a3fd20e58fdbd9b86278b7de0c245de3063dce27",
  "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json": "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
  "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json": "661a57f839101fbf54c7e4edc76166c65ce9327d",
  "canonical/governance/OPUS55_MATERIAL_CONDITION_REGISTRY_V1.json": "9248a6d848aa43b9cdd8877bf8a8f0bad7563758",
  "canonical/governance/OPUS55_MATERIAL_CONDITION_EVIDENCE_BINDINGS_V1.json": "5b7371fa97afdecce1360b0be157367fa42da03e",
  "canonical/runtime/material_condition_closure_v1.py": "283f3870c2c90a6d60e8f0013dce2bcfd33a4dd9",
  "canonical/runtime/terminal_projection_consistency_v1.py": "aab1b6973fd38fe5273f84a5eaa87e9a4162a738",
  "canonical/tests/test_material_condition_closure_v1.py": "50d66534eed5f44374b1c392f1c2875d479091da",
  "canonical/tests/test_terminal_projection_consistency_v1.py": "0f94788b4bb68317ba0605bb42c1fa22d84cd93c",
  "canonical/governance/TERMINAL_PROJECTION_CONSISTENCY_V3.json": "41397da07498953a933d8b1c433df25ee4f79053",
  "canonical/governance/OPUS55_OPEN_WORLD_TARGET_CERTIFICATION_BOUNDARY_20261005_V1.json": "2476ab2d8220994d7858c80409b563e1582c88e6",
  "canonical/governance/LITERAL_ALL_CAPABILITY_UNIVERSE_EXHAUSTIVENESS_THEOREM_V1.json": "2ee40ca11e58f19b34fc8cd1bb849a4b4cf08ec1",
  "canonical/governance/OPUS55_PUBLIC_CAPABILITY_SOURCE_UNIVERSE_V1.json": "26814f5bad298e1d73b257f5289051744ca381f3",
  "canonical/governance/TERMINAL_ACCEPTANCE_BASIS_REPAIR_MINIMUM_CUT_20261005_V3.json": "09503a3485a101b45f29c17d6af4f8c488351aad",
  ".github/workflows/verify-terminal-projection-consistency.yml": "a70fc8af46828827fd403652b01a29a01b4edc85"
}

def blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\\0"+data).hexdigest()

for rel, expected in EXPECTED.items():
    got=blob(SUB/rel)
    assert got==expected,(rel,got,expected)

v3=json.loads((SUB/"canonical/governance/TERMINAL_PROJECTION_CONSISTENCY_V3.json").read_text())
authority=json.loads((SUB/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json").read_text())

assert v3["runtime"]["git_blob_sha"]==EXPECTED["canonical/runtime/terminal_projection_consistency_v1.py"]
assert v3["tests"]["git_blob_sha"]==EXPECTED["canonical/tests/test_terminal_projection_consistency_v1.py"]
assert v3["workflow"]["git_blob_sha"]==EXPECTED[".github/workflows/verify-terminal-projection-consistency.yml"]
mg=v3["material_condition_gate"]
assert mg["registry_git_blob_sha"]==EXPECTED["canonical/governance/OPUS55_MATERIAL_CONDITION_REGISTRY_V1.json"]
assert mg["evidence_git_blob_sha"]==EXPECTED["canonical/governance/OPUS55_MATERIAL_CONDITION_EVIDENCE_BINDINGS_V1.json"]
assert mg["runtime_git_blob_sha"]==EXPECTED["canonical/runtime/material_condition_closure_v1.py"]
assert mg["tests_git_blob_sha"]==EXPECTED["canonical/tests/test_material_condition_closure_v1.py"]
basis=v3["logical_basis"]
assert basis["open_world_boundary"]["git_blob_sha"]==EXPECTED["canonical/governance/OPUS55_OPEN_WORLD_TARGET_CERTIFICATION_BOUNDARY_20261005_V1.json"]
assert basis["literal_exhaustiveness_theorem"]["git_blob_sha"]==EXPECTED["canonical/governance/LITERAL_ALL_CAPABILITY_UNIVERSE_EXHAUSTIVENESS_THEOREM_V1.json"]
assert basis["public_source_universe"]["git_blob_sha"]==EXPECTED["canonical/governance/OPUS55_PUBLIC_CAPABILITY_SOURCE_UNIVERSE_V1.json"]
assert basis["known_basis_repair_cut"]["git_blob_sha"]==EXPECTED["canonical/governance/TERMINAL_ACCEPTANCE_BASIS_REPAIR_MINIMUM_CUT_20261005_V3.json"]

ap=authority["sources"]["terminal_projection_consistency"]
assert ap["governance_git_blob_sha"]==EXPECTED["canonical/governance/TERMINAL_PROJECTION_CONSISTENCY_V3.json"]
assert ap["runtime_git_blob_sha"]==EXPECTED["canonical/runtime/terminal_projection_consistency_v1.py"]
assert ap["tests_git_blob_sha"]==EXPECTED["canonical/tests/test_terminal_projection_consistency_v1.py"]
assert ap["workflow_git_blob_sha"]==EXPECTED[".github/workflows/verify-terminal-projection-consistency.yml"]
assert authority["truth"]["achieved"] is False

env=os.environ.copy()
env["PYTHONPATH"]=str(SUB)+(os.pathsep+env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
tests=subprocess.run(
    [sys.executable,"-m","unittest",
     "canonical.tests.test_material_condition_closure_v1",
     "canonical.tests.test_terminal_projection_consistency_v1","-v"],
    cwd=SUB,env=env,text=True,capture_output=True
)
assert tests.returncode==0,tests.stdout+"\n"+tests.stderr

live=subprocess.run(
    [sys.executable,"canonical/runtime/terminal_projection_consistency_v1.py"],
    cwd=SUB,env=env,text=True,capture_output=True
)
assert live.returncode==0,live.stdout+"\n"+live.stderr
out=json.loads(live.stdout)
assert out["pass"] is True,out
assert out["terminal_goal_achieved"] is False
assert out["terminal_finality_eligible"] is False
assert out["material_condition_gate_pass"] is False
assert out["material_conditions_open"]>0
assert out["material_condition_source_universe_sealed"] is False

spec=importlib.util.spec_from_file_location("material_condition_closure_v1",SUB/"canonical/runtime/material_condition_closure_v1.py")
mod=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(mod)
reg=json.loads((SUB/"canonical/governance/OPUS55_MATERIAL_CONDITION_REGISTRY_V1.json").read_text())
evid=json.loads((SUB/"canonical/governance/OPUS55_MATERIAL_CONDITION_EVIDENCE_BINDINGS_V1.json").read_text())
envdoc=json.loads((SUB/"canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json").read_text())
base=mod.compile_material_condition_closure(reg,evid,envdoc)
assert base["pass"] is True and base["terminal_condition_gate_pass"] is False

grown=copy.deepcopy(reg)
grown["conditions"].append({
  "id":"INDEPENDENT_VERIFIER_FUTURE_MATERIAL_CONDITION",
  "kind":"CROSS_CUTTING_VERIFIER_CONDITION",
  "families":["COMMUNICATION_AND_SYNTHESIS"],
  "source":"independent_verifier",
  "acceptance":"verifier-only synthetic condition"
})
gout=mod.compile_material_condition_closure(grown,evid,envdoc)
assert gout["condition_count"]==base["condition_count"]+1
assert "INDEPENDENT_VERIFIER_FUTURE_MATERIAL_CONDITION" in gout["open_conditions"]

allproved=copy.deepcopy(evid)
allproved["claims"]=[{"condition_id":r["id"],"state":"PROVED","scope_complete":True} for r in reg["conditions"]]
known=mod.compile_material_condition_closure(reg,allproved,envdoc)
assert known["proved_condition_count"]==known["condition_count"]
assert known["terminal_condition_gate_pass"] is False

fake=copy.deepcopy(reg)
fake["source_universe"]["sealed"]=True
fake["source_universe"]["independent_seal_receipt"]={
  "path":"canonical/verification/fake.json",
  "git_blob_sha":"b"*40,
  "state":"INDEPENDENT_PASS"
}
fakeout=mod.compile_material_condition_closure(fake,allproved,envdoc,verified_source_universe_receipt_sha=None)
assert fakeout["pass"] is False
assert "SOURCE_UNIVERSE_SEAL_RECEIPT_BLOB_NOT_VERIFIED" in fakeout["errors"]
assert fakeout["terminal_condition_gate_pass"] is False

receipt={
 "schema":"PROJECT_BRAIN_TERMINAL_FINALITY_GUARD_V3_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__EXACT_BLOBS__UNIT_TESTS__LIVE_PROJECTION__DYNAMIC_CONDITION_GROWTH__UNSEALED_UNIVERSE_FIREWALL__FAKE_SEAL_REJECTED__ZERO_CREDIT",
 "brain_pr":2088,
 "brain_subject_head":"1879035cbb5bb83fa8902b8a879fb232842ac577",
 "subject_blobs":EXPECTED,
 "checks":{
  "exact_subject_blobs":True,
  "v3_content_addresses_recomputed":True,
  "authority_projection_pointers_recomputed":True,
  "material_condition_unit_tests_pass":True,
  "terminal_projection_unit_tests_pass":True,
  "live_projection_pass":True,
  "live_terminal_false_preserved":True,
  "future_condition_changes_denominator_without_code_change":True,
  "all_known_conditions_insufficient_while_source_universe_unsealed":True,
  "fake_unverified_source_universe_seal_rejected":True
 },
 "live_projection_summary":{
  "acceptance_closed_families":out["acceptance_closed_families"],
  "acceptance_open_families":out["acceptance_open_families"],
  "atomic_predicates_proved":out["atomic_predicates_proved"],
  "atomic_predicates_unresolved":out["atomic_predicates_unresolved"],
  "material_conditions_total":out["material_conditions_total"],
  "material_conditions_open":out["material_conditions_open"],
  "terminal_finality_eligible":out["terminal_finality_eligible"],
  "terminal_goal_achieved":out["terminal_goal_achieved"]
 },
 "authority":{"scheduling":False,"execution":False,"promotion":False,"fresh_reality":False},
 "accounting":{"incremental_spend_usd":0,"new_reality_units_consumed":0,"terminal_cases_consumed":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0}
}
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
