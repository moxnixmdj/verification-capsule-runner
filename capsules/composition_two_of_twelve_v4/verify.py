from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
C=ROOT/"canonical"

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()

expected=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))
mirrors={k:ROOT/k for k in expected["exact_brain_blobs"]}
actual={k:blob(p) for k,p in mirrors.items()}
assert actual==expected["exact_brain_blobs"],(actual,expected["exact_brain_blobs"])

inp=json.loads((C/"governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V4.json").read_text(encoding="utf-8"))
dv=json.loads((C/"verification/COMPOSITION_DELEGATION_SCOPE_COMPLETE_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json").read_text(encoding="utf-8"))
mv=json.loads((C/"verification/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json").read_text(encoding="utf-8"))

assert dv["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),dv
assert dv["public_runner"]["conclusion"]=="success",dv
assert dv["verified_component_receipt"]["verified"] is True
assert dv["verified_component_receipt"]["independent"] is True
assert dv["verified_component_receipt"]["component_id"]=="delegation"
assert dv["verified_component_receipt"]["receipt_id"]=="COMPOSITION_SCOPE_COMPLETE_BRIDGE::SUBAGENT_DELEGATION_AND_COORDINATION::delegation::V1"
assert mv["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),mv
assert mv["public_runner"]["conclusion"]=="success",mv
assert mv["verified_component_receipt"]["verified"] is True
assert mv["verified_component_receipt"]["independent"] is True
assert mv["verified_component_receipt"]["component_id"]=="memory"

rv=inp["receipt_verification"]
assert rv["delegation"]["git_blob_sha"]==actual["canonical/verification/COMPOSITION_DELEGATION_SCOPE_COMPLETE_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"]
assert rv["memory"]["git_blob_sha"]==actual["canonical/verification/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"]
assert inp["receipts"]==[mv["verified_component_receipt"],dv["verified_component_receipt"]],inp["receipts"]

spec=importlib.util.spec_from_file_location("slicer",C/"runtime/composition_component_proof_slicer_v1.py")
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
out=mod.evaluate(inp)
(C/"verification").mkdir(parents=True,exist_ok=True)
(ROOT/"composition-component-proof-slice-v4.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")

proved=[x["component_id"] for x in out["interfaces"] if x["state"]=="SCOPED_PROVED"]
opened=[x["component_id"] for x in out["interfaces"] if x["state"]=="OPEN"]
assert out["status"]=="RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN",out
assert out["errors"]==[],out
assert len(out["interfaces"])==12,out
assert proved==["memory","delegation"],proved
assert len(opened)==10,opened
for must_open in ["tool discovery","evidence synthesis","artifact production","research","coding","recovery"]:
    assert must_open in opened,(must_open,opened)
assert out["all_used_component_interfaces_scoped_proved"] is False
assert out["new_reality_units_consumed"]==0
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0

print(json.dumps({
 "status":"PASS",
 "frozen_interface_count":12,
 "scoped_proved_count":2,
 "scoped_proved_components":proved,
 "open_count":10,
 "parent_composition_predicate_closed":False,
 "component_proofs_revalidated":["memory","delegation"],
 "credit_delta":0
},indent=2,sort_keys=True))
