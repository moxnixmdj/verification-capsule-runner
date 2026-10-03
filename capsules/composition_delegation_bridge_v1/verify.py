from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def blob(path: Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

expected=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
mirrors={
 "canonical/governance/COMPOSITION_DELEGATION_SCOPE_COMPLETE_BRIDGE_V1.json":ROOT/"bridge.json",
 "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json":ROOT/"envelope.json",
 "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":ROOT/"protocols.json",
 "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json":ROOT/"manifest.json",
 "canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":ROOT/"universal.json",
 "canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":ROOT/"acceptance.json",
}
actual={k:blob(v) for k,v in mirrors.items()}
assert actual==expected["exact_brain_blobs"],(actual,expected["exact_brain_blobs"])

bridge=json.loads((ROOT/"bridge.json").read_text())
env=json.loads((ROOT/"envelope.json").read_text())
protocols=json.loads((ROOT/"protocols.json").read_text())
manifest=json.loads((ROOT/"manifest.json").read_text())
universal=json.loads((ROOT/"universal.json").read_text())
acceptance=json.loads((ROOT/"acceptance.json").read_text())

assert bridge["schema"]=="PROJECT_BRAIN_COMPOSITION_DELEGATION_SCOPE_COMPLETE_BRIDGE_V1"
assert bridge["status"].startswith("CANDIDATE__CURRENT_SOURCE_BOUND_DELEGATION_COMPONENT_BRIDGE")
assert bridge["claim_id"]=="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"
for key,path in [
 ("terminal_envelope","canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json"),
 ("terminal_protocols","canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
 ("composition_manifest","canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"),
 ("delegation_universal_scope_verification","canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
 ("delegation_acceptance_reduction","canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
]:
    a=bridge["authority"][key]
    assert a["path"]==path,(key,a,path)
    assert a["git_blob_sha"]==actual[path],(key,a["git_blob_sha"],actual[path])

binding=bridge["component_binding"]
assert binding=={
 "component_id":"delegation",
 "interface_id":"delegation+evidence synthesis+artifact production",
 "proved_properties_after_independent_verification":["SCOPED_ACCEPTANCE_PROOF"],
}

families={x["id"]:x for x in env["families"]}
assert env["target_family_count"]==19
source=families["SUBAGENT_DELEGATION_AND_COORDINATION"]
assert source["useful_behavior"]=="Delegate to multiple workers/subagents, coordinate results and check delegated work."
assert "delegation" in families["MULTI_CAPABILITY_COMPOSITION"]["useful_behavior"].lower() or "compose" in families["MULTI_CAPABILITY_COMPOSITION"]["useful_behavior"].lower()

rows={x["family"]:x for x in protocols["protocols"]}
d=rows["SUBAGENT_DELEGATION_AND_COORDINATION"]
c=rows["MULTI_CAPABILITY_COMPOSITION"]
assert d["status"]=="PASS",d
assert d["closure_receipt"]=="canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
assert d["closure_basis"]=="ABSOLUTE_DOMINANCE_WITH_INDEPENDENT_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS"
assert bridge["scope_guard"]["included_scope"]==d["task_dimensions"]
assert c["status"]=="DEFINED_RESULT_OPEN"
assert "delegation+evidence synthesis+artifact production" in c["task_dimensions"]
assert "Every isolated component used in the claim has its own scoped proof" in c["acceptance"]

ifs=[x for x in manifest["interfaces"] if x["component_id"]=="delegation"]
assert len(ifs)==1
assert ifs[0]["interface_id"]=="delegation+evidence synthesis+artifact production"
assert ifs[0]["required_properties"]==["SCOPED_ACCEPTANCE_PROOF"]

assert universal["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert universal["target_predicate"]=="DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"
assert universal["target_proof_atom"]=="INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_DELEGATION_PROTOCOL"
assert "UNIVERSAL_SCOPE_PROVED_TRUE" in universal["verified"]
assert "BASIS_KIND_UNIVERSAL_FORMAL_SCOPE_PROOF" in universal["verified"]
assert universal["new_reality_units_consumed"]==0
assert universal["capability_credit_delta"]==0 and universal["family_credit_delta"]==0

assert acceptance["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
vr=acceptance["verified_result"]
assert vr["newly_closed_families"]==["SUBAGENT_DELEGATION_AND_COORDINATION"]
assert vr["scope_completeness_basis"]=="UNIVERSAL_FORMAL_SCOPE_PROOF"
assert vr["closed_family_count"]==3
assert set(vr["preserved_closed_families"])=={"EXACT_SYMBOLIC_COMPUTATION","LONG_HORIZON_MEMORY_AND_CONTINUITY"}
assert acceptance["promotion_scope"]==["SUBAGENT_DELEGATION_AND_COORDINATION","DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"]
assert acceptance["new_reality_units_consumed"]==0
assert acceptance["capability_credit_delta"]==0 and acceptance["family_credit_delta"]==0

q=bridge["quarantine_relation"]
assert q["historical_receipt_restored"] is False
assert q["new_receipt_required"] is True
assert bridge["candidate_receipt"]["verified"] is False
assert bridge["candidate_receipt"]["independent"] is False
assert bridge["candidate_receipt"]["component_id"]=="delegation"
assert bridge["candidate_receipt"]["acceptance_scoped"] is True
assert bridge["candidate_receipt"]["contamination_clean"] is True
assert set(bridge["scope_guard"]["excluded_scope"])=={
 "EVIDENCE_SYNTHESIS_COMPONENT","ARTIFACT_PRODUCTION_COMPONENT",
 "GENERAL_MULTI_CAPABILITY_COMPOSITION_INTERACTION_SUCCESS",
 "CROSS_CAPABILITY_STATE_HANDOFF_AND_ROLLBACK"
}
assert bridge["new_reality_units_consumed"]==0 and bridge["terminal_results_replayed"]==0
assert bridge["capability_credit_delta"]==0 and bridge["family_credit_delta"]==0
assert bridge["execution_authority"] is False and bridge["promotion_authority"] is False

print(json.dumps({
 "status":"PASS",
 "component":"delegation",
 "source_family":"SUBAGENT_DELEGATION_AND_COORDINATION",
 "source_protocol_status":d["status"],
 "scope_basis":"UNIVERSAL_FORMAL_SCOPE_PROOF",
 "historical_receipt_reused":False,
 "adjacent_component_credit":False,
 "current_source_bound":True,
 "credit_delta":0
},indent=2,sort_keys=True))
