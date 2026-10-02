from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def blob(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

expected=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
mirrors={
 "canonical/governance/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V1.json":ROOT/"bridge.json",
 "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json":ROOT/"envelope.json",
 "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":ROOT/"protocols.json",
 "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json":ROOT/"manifest.json",
 "canonical/capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json":ROOT/"memory_package.json",
}
actual={k:blob(v) for k,v in mirrors.items()}
assert actual==expected["exact_brain_blobs"], (actual,expected["exact_brain_blobs"])

bridge=json.loads((ROOT/"bridge.json").read_text())
env=json.loads((ROOT/"envelope.json").read_text())
protocols=json.loads((ROOT/"protocols.json").read_text())
manifest=json.loads((ROOT/"manifest.json").read_text())
memory=json.loads((ROOT/"memory_package.json").read_text())

assert bridge["status"].startswith("CANDIDATE__")
assert bridge["claim_id"]=="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"
binding=bridge["component_binding"]
assert binding=={
 "component_id":"memory",
 "interface_id":"browser/computer action+memory+recovery",
 "proved_properties_after_independent_verification":["SCOPED_ACCEPTANCE_PROOF"],
}

assert env["target_family_count"]==19
families=env["families"]
composition=next(x for x in families if x["id"]=="MULTI_CAPABILITY_COMPOSITION")
memory_family=next(x for x in families if x["id"]=="LONG_HORIZON_MEMORY_AND_CONTINUITY")
noncomposition_memory=[
 x["id"] for x in families
 if x["id"]!="MULTI_CAPABILITY_COMPOSITION" and "memory" in x["useful_behavior"].lower()
]
assert noncomposition_memory==["LONG_HORIZON_MEMORY_AND_CONTINUITY"], noncomposition_memory
assert "memory" in composition["useful_behavior"].lower()
assert memory_family["useful_behavior"]=="Use memory across sessions, preserve project state and resume long-running work coherently."

mem_protocol=[x for x in protocols["protocols"] if x["family"]=="LONG_HORIZON_MEMORY_AND_CONTINUITY"]
assert len(mem_protocol)==1 and mem_protocol[0]["status"]=="PASS"
comp_protocol=[x for x in protocols["protocols"] if x["family"]=="MULTI_CAPABILITY_COMPOSITION"]
assert len(comp_protocol)==1
assert comp_protocol[0]["status"]=="DEFINED_RESULT_OPEN"
assert "browser/computer action+memory+recovery" in comp_protocol[0]["task_dimensions"]
assert "Every isolated component used in the claim has its own scoped proof" in comp_protocol[0]["acceptance"]

mem_interfaces=[
 x for x in manifest["interfaces"]
 if x["component_id"]=="memory"
]
assert len(mem_interfaces)==1
mi=mem_interfaces[0]
assert mi["interface_id"]=="browser/computer action+memory+recovery"
assert mi["required_properties"]==["SCOPED_ACCEPTANCE_PROOF"]

assert memory["status"]=="VERIFIED_OWNED_EQUAL_OR_BETTER"
assert memory["family"]=="LONG_HORIZON_MEMORY_AND_CONTINUITY"
assert memory["decision"]["ownership_status"]=="VERIFIED_OWNED_EQUAL_OR_BETTER"
assert memory["decision"]["parent_family_closed_for_claim_scope"] is True
assert memory["brain_owned_route"]["external_hidden_capability_provider_required"] is False
assert memory["brain_owned_route"]["incremental_spend_usd"]==0

scope=bridge["scope_guard"]
assert scope["included_scope"]==memory["claim_scope"]
assert set(scope["excluded_scope"])==set(memory["excluded_scope"])

receipt=bridge["candidate_receipt"]
assert receipt["component_id"]=="memory"
assert receipt["interface_id"]=="browser/computer action+memory+recovery"
assert receipt["proved_properties"]==["SCOPED_ACCEPTANCE_PROOF"]
assert receipt["acceptance_scoped"] is True
assert receipt["contamination_clean"] is True
assert receipt["binds_frozen_claim"]=="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"
assert receipt["source_family"]=="LONG_HORIZON_MEMORY_AND_CONTINUITY"
assert receipt["verified"] is False and receipt["independent"] is False

assert bridge["capability_credit_delta"]==0 and bridge["family_credit_delta"]==0
assert bridge["execution_authority"] is False and bridge["promotion_authority"] is False

print(json.dumps({
 "status":"PASS",
 "exact_blob_shas":actual,
 "unique_noncomposition_memory_family":noncomposition_memory,
 "memory_protocol_status":mem_protocol[0]["status"],
 "source_ownership_status":memory["status"],
 "scope_exactly_preserved":True,
 "composition_component":"memory",
 "credit_delta":0
},indent=2,sort_keys=True))
