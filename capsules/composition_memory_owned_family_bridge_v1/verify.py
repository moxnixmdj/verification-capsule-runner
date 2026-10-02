from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED={
  "envelope.json": "661a57f839101fbf54c7e4edc76166c65ce9327d",
  "protocols.json": "eb4bca0fe6a015d49d2854998fbe046c979c7ea9",
  "manifest.json": "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
  "memory_package.json": "2d912cf8df64bd806fffb6a1070d95644d005470",
  "bridge.json": "d073b395c3ec335e5aebe45e100a8a9a345905f6",
  "slice_v2.json": "714d1771ad2fa3ca240c0fb73609dc4873ea4390"
}

def blob_sha(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,e in EXPECTED.items():
    g=blob_sha(ROOT/n)
    assert g==e,(n,g,e)

env=json.loads((ROOT/"envelope.json").read_text())
prot=json.loads((ROOT/"protocols.json").read_text())
man=json.loads((ROOT/"manifest.json").read_text())
mem=json.loads((ROOT/"memory_package.json").read_text())
bridge=json.loads((ROOT/"bridge.json").read_text())
slice2=json.loads((ROOT/"slice_v2.json").read_text())

assert env["target_family_count"]==19
hits=[f for f in env["families"] if "memory" in str(f.get("useful_behavior","")).lower()]
non_comp=[f for f in hits if f["id"]!="MULTI_CAPABILITY_COMPOSITION"]
assert len(non_comp)==1,[(x["id"],x["useful_behavior"]) for x in non_comp]
assert non_comp[0]["id"]=="LONG_HORIZON_MEMORY_AND_CONTINUITY"
assert non_comp[0]["useful_behavior"]=="Use memory across sessions, preserve project state and resume long-running work coherently."

p=[x for x in prot["protocols"] if x["family"]=="LONG_HORIZON_MEMORY_AND_CONTINUITY"]
assert len(p)==1
assert p[0]["status"]=="PASS"
assert p[0]["proof_mode"]=="ABSOLUTE_SCOPED_CEILING"

interfaces=[x for x in man["interfaces"] if x["component_id"]=="memory"]
assert len(interfaces)==1
iface=interfaces[0]
assert iface["interface_id"]=="browser/computer action+memory+recovery"
assert iface["required_properties"]==["SCOPED_ACCEPTANCE_PROOF"]
assert iface["source_component_literal"]=="memory"

assert mem["family"]=="LONG_HORIZON_MEMORY_AND_CONTINUITY"
assert mem["status"]=="VERIFIED_OWNED_EQUAL_OR_BETTER"
assert mem["decision"]["parent_family_closed_for_claim_scope"] is True
assert mem["decision"]["global_memory_superiority_claim"] is False
assert mem["target_basis"]["useful_behavior"]==non_comp[0]["useful_behavior"]
assert mem["claim_scope"]==bridge["scope_guard"]["included_scope"]
assert mem["excluded_scope"]==bridge["scope_guard"]["excluded_scope"]

r=bridge["candidate_receipt"]
assert r["component_id"]=="memory"
assert r["interface_id"]==iface["interface_id"]
assert r["proved_properties"]==iface["required_properties"]
assert r["acceptance_scoped"] is True
assert r["contamination_clean"] is True
assert r["source_family"]=="LONG_HORIZON_MEMORY_AND_CONTINUITY"
assert r["binds_frozen_claim"]=="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"

# Existing slice is exactly 2/12; this bridge may add only memory, not parent composition credit.
assert len(slice2["interfaces"])==12
proved=[x for x in slice2["interfaces"] if x["state"]=="SCOPED_PROVED"]
assert sorted(x["component_id"] for x in proved)==["delegation","tool discovery"]
memory=[x for x in slice2["interfaces"] if x["component_id"]=="memory"][0]
assert memory["state"]=="OPEN"

projected_proved=sorted([x["component_id"] for x in proved]+["memory"])
assert projected_proved==["delegation","memory","tool discovery"]

out={
 "schema":"PROJECT_BRAIN_COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_PUBLIC_RUNNER_VERIFICATION_V1",
 "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__MEMORY_COMPONENT_SCOPED_PROOF_BINDING_ADMISSIBLE__PROJECTED_3_OF_12__PARENT_COMPOSITION_OPEN__ZERO_CREDIT",
 "exact_brain_blobs":EXPECTED,
 "verified":{
   "unique_noncomposition_terminal_memory_family":"LONG_HORIZON_MEMORY_AND_CONTINUITY",
   "source_protocol_status":"PASS",
   "source_ownership_status":"VERIFIED_OWNED_EQUAL_OR_BETTER",
   "source_parent_family_closed_for_claim_scope":True,
   "frozen_component_id":"memory",
   "frozen_interface_id":"browser/computer action+memory+recovery",
   "required_property":"SCOPED_ACCEPTANCE_PROOF",
   "scope_exclusions_preserved":True,
   "prior_scoped_proved_count":2,
   "projected_scoped_proved_count_after_binding":3,
   "parent_composition_acceptance_granted":False,
 },
 "new_reality_units_consumed":0,
 "incremental_spend_usd":0,
 "capability_credit_delta":0,
 "family_credit_delta":0,
 "execution_authority":False,
 "promotion_authority":False,
}
print(json.dumps(out,indent=2,sort_keys=True))
