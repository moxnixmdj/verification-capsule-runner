from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject/composition_synthesis_scope_bridge_v1"

PATHS={
 "bridge":"canonical/governance/COMPOSITION_SYNTHESIS_SCOPE_COMPLETE_BRIDGE_V1.json",
 "v7":"canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V7.json",
 "authority":"canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V7.json",
 "v6":"canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V6.json",
 "cert":"canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json",
 "cert_verify":"canonical/verification/SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
 "manifest":"canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json",
 "slicer":"canonical/runtime/composition_component_proof_slicer_v1.py",
}
EXPECTED={
 PATHS["v6"]:"cb15018cd7a913bdf250d1cef884d4b1005d3d67",
 PATHS["cert"]:"dea9028f92f111ee3c8be71615fa4b02e8a8bfb6",
 PATHS["cert_verify"]:"1852516f725f5b72badfc2f65be22e542ed83623",
 PATHS["manifest"]:"9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
 PATHS["slicer"]:"0e5028d8547bc3e17e7128b6311f734ac30a16d8",
}

def p(rel:str)->Path:
    return SUB/rel

def load(rel:str):
    return json.loads(p(rel).read_text(encoding="utf-8"))

def blob(rel:str)->str:
    b=p(rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,sha in EXPECTED.items():
    got=blob(rel)
    assert got==sha,(rel,got,sha)

cert=load(PATHS["cert"])
cv=load(PATHS["cert_verify"])
manifest=load(PATHS["manifest"])
bridge=load(PATHS["bridge"])
v6=load(PATHS["v6"])
v7=load(PATHS["v7"])
auth=load(PATHS["authority"])

assert cert["verified"] is True
assert cert["independent"] is True
assert cert["scope_relation"]=="PROVEN_STRONGER"
assert cert["coverage_complete"] is True
assert cert["coverage_relation"]=="EXACT_UNION"
assert cert["consequence"]["root3_scope_relation_closed"] is True
assert cert["consequence"]["predicate_remains_open_for_root2"] is True
assert cert["acceptance_credit_delta"]==0
assert cert["fresh_reality_authority"] is False

assert cv["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert cv["independent_runner"]["conclusion"]=="success"
assert cv["verified"]["root3_scope_relation_closed"] is True
assert cv["verified"]["acceptance_closed"] is False
assert cv["new_reality_units_consumed"]==0

row=next(x for x in manifest["interfaces"] if x["component_id"]=="evidence synthesis")
assert row["interface_id"]=="delegation+evidence synthesis+artifact production"
assert row["required_properties"]==["SCOPED_ACCEPTANCE_PROOF"]

assert bridge["component_id"]=="evidence synthesis"
assert bridge["interface_id"]==row["interface_id"]
assert bridge["source_predicate"]=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
adm=bridge["admissibility"]
assert adm["verified"] is True
assert adm["independent"] is True
assert adm["contamination_clean"] is True
assert adm["acceptance_scoped"] is True
assert adm["binds_frozen_claim"]=="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"
assert adm["proved_properties"]==["SCOPED_ACCEPTANCE_PROOF"]
assert bridge["exact_consequence_if_verified"]["synthesis_acceptance_closed"] is False
assert bridge["exact_consequence_if_verified"]["synthesis_performance_credit"] is False
assert bridge["exact_consequence_if_verified"]["parent_composition_predicate_closed"] is False

spec=importlib.util.spec_from_file_location("slicer",p(PATHS["slicer"]))
mod=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

o6=mod.evaluate(v6)
o7=mod.evaluate(v7)

def states(out):
    return {x["component_id"]:x["state"] for x in out["interfaces"]}

s6=states(o6); s7=states(o7)
assert sum(v=="SCOPED_PROVED" for v in s6.values())==4
assert sum(v=="SCOPED_PROVED" for v in s7.values())==5
changed={k for k in s6 if s6[k]!=s7[k]}
assert changed=={"evidence synthesis"},changed
assert s6["evidence synthesis"]=="OPEN"
assert s7["evidence synthesis"]=="SCOPED_PROVED"
assert s7["artifact production"]=="OPEN"
assert s7["delegation"]=="SCOPED_PROVED"

assert len(v7["receipts"])==len(v6["receipts"])+1
new_ids={r["receipt_id"] for r in v7["receipts"]}-{r["receipt_id"] for r in v6["receipts"]}
assert new_ids=={"COMPOSITION_SCOPE_COMPLETE_BRIDGE::COMMUNICATION_AND_SYNTHESIS::evidence_synthesis::V1"}

assert auth["truth"]["candidate_admissible_scoped_proved"]==5
assert auth["truth"]["candidate_open"]==7
assert auth["truth"]["parent_composition_predicate_closed"] is False
assert auth["truth"]["strict_opus55_acceptance_delta"]==0
assert auth["accounting"]["acceptance_credit_delta"]==0
assert auth["accounting"]["capability_credit_delta"]==0
assert auth["fresh_reality_authority"] is False

print(json.dumps({
 "status":"PASS__EXACT_SYNTHESIS_SCOPE_BRIDGE__COMPOSITION_4_TO_5_ONLY__ZERO_PARENT_OR_PERFORMANCE_CREDIT",
 "source_blobs":{k:blob(k) for k in EXPECTED},
 "candidate_blobs":{
   "bridge":blob(PATHS["bridge"]),
   "v7":blob(PATHS["v7"]),
   "authority":blob(PATHS["authority"]),
 },
 "v6_scoped":sorted(k for k,v in s6.items() if v=="SCOPED_PROVED"),
 "v7_scoped":sorted(k for k,v in s7.items() if v=="SCOPED_PROVED"),
 "changed_components":sorted(changed),
 "parent_composition_closed":False,
 "synthesis_performance_credit":False,
 "fresh_reality":False,
 "acceptance_credit":0,
},indent=2,sort_keys=True))
