from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()

exp=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
actual={
 "canonical/runtime/composition_component_proof_slicer_v1.py":blob(ROOT/"composition_component_proof_slicer_v1.py"),
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V4.json":blob(ROOT/"input.json"),
 "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json":blob(ROOT/"manifest.json"),
 "canonical/verification/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":blob(ROOT/"memory_verification.json"),
 "canonical/verification/COMPOSITION_DELEGATION_BRIDGE_V1_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":blob(ROOT/"delegation_verification.json"),
}
assert actual==exp["exact_brain_blobs"],(actual,exp["exact_brain_blobs"])
spec=importlib.util.spec_from_file_location("slicer",ROOT/"composition_component_proof_slicer_v1.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
doc=json.loads((ROOT/"input.json").read_text())
manifest=json.loads((ROOT/"manifest.json").read_text())
memory_ver=json.loads((ROOT/"memory_verification.json").read_text())
delegation_ver=json.loads((ROOT/"delegation_verification.json").read_text())

# Bind the V4 interface universe to the independently frozen 12-interface manifest.
assert doc["claim_id"]==manifest["claim_id"]
assert doc["source_manifest_git_blob_sha"]==actual["canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"]
manifest_interfaces=[
    {
        "component_id":r["component_id"],
        "interface_id":r["interface_id"],
        "required_properties":r["required_properties"],
    }
    for r in manifest["interfaces"]
]
assert doc["interfaces"]==manifest_interfaces,(doc["interfaces"],manifest_interfaces)
assert manifest["isolated_component_interface_count"]==12

# Bind each admitted receipt byte-for-byte to its independent verifier output.
by_component={r["component_id"]:r for r in doc["receipts"]}
assert set(by_component)=={"memory","delegation"}
assert by_component["memory"]==memory_ver["verified_component_receipt"]
assert by_component["delegation"]==delegation_ver["verified_component_receipt"]
assert memory_ver["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert delegation_ver["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert memory_ver["public_runner"]["conclusion"]=="success"
assert delegation_ver["public_runner"]["conclusion"]=="success"
assert memory_ver["public_runner"]["pull_request"]==1120
assert delegation_ver["public_runner"]["pull_request"]==1129
assert memory_ver["new_reality_units_consumed"]==0
assert delegation_ver["new_reality_units_consumed"]==0
assert memory_ver["capability_credit_delta"]==0 and memory_ver["family_credit_delta"]==0
assert delegation_ver["capability_credit_delta"]==0 and delegation_ver["family_credit_delta"]==0

# Input provenance pointers must name those exact successful verifications.
sv={r["component_id"]:r for r in doc["source_verifications"]}
assert set(sv)=={"memory","delegation"}
assert sv["memory"]["path"]=="canonical/verification/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
assert sv["memory"]["public_runner_pr"]==memory_ver["public_runner"]["pull_request"]
assert sv["memory"]["workflow_run_id"]==memory_ver["public_runner"]["workflow_run_id"]
assert sv["memory"]["conclusion"]==memory_ver["public_runner"]["conclusion"]
assert sv["delegation"]["path"]=="canonical/verification/COMPOSITION_DELEGATION_BRIDGE_V1_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
assert sv["delegation"]["public_runner_pr"]==delegation_ver["public_runner"]["pull_request"]
assert sv["delegation"]["workflow_run_id"]==delegation_ver["public_runner"]["workflow_run_id"]
assert sv["delegation"]["conclusion"]==delegation_ver["public_runner"]["conclusion"]

out=mod.evaluate(doc)
assert out["status"]=="RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN"
assert out["all_used_component_interfaces_scoped_proved"] is False
rows=out["interfaces"]
assert len(rows)==12
proved=[r for r in rows if r["state"]=="SCOPED_PROVED"]
opened=[r for r in rows if r["state"]=="OPEN"]
assert len(proved)==2 and len(opened)==10,(proved,opened)
assert [r["component_id"] for r in proved]==["memory","delegation"],proved
by={r["component_id"]:r for r in proved}
assert by["memory"]["supporting_receipt_ids"]==["COMPOSITION_OWNED_FAMILY_BRIDGE_V2::LONG_HORIZON_MEMORY_AND_CONTINUITY::memory"]
assert by["delegation"]["supporting_receipt_ids"]==["COMPOSITION_SCOPE_COMPLETE_BRIDGE::SUBAGENT_DELEGATION_AND_COORDINATION::delegation::V1"]
for r in proved:
    assert r["proved_properties"]==["SCOPED_ACCEPTANCE_PROOF"]
    assert r["missing_properties"]==[]
assert "evidence synthesis" in [r["component_id"] for r in opened]
assert "artifact production" in [r["component_id"] for r in opened]
assert "tool discovery" in [r["component_id"] for r in opened]
assert out["new_reality_units_consumed"]==0
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0
print(json.dumps({"status":"PASS","authority_bindings":"EXACT","scoped_proved":2,"open":10,"proved_components":["memory","delegation"],"parent_open":True,"slicer_output":out},indent=2,sort_keys=True))
