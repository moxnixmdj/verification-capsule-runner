#!/usr/bin/env python3
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

paths={
  "root3":"canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json",
  "activation":"canonical/governance/UNIVERSAL_LEARNING_DECISION_ROUTER_V3_ACTIVATION_V1.json",
  "receipt":"canonical/verification/UNIVERSAL_LEARNING_DECISION_ROUTER_V3_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
}
expected={
  "root3":"6082b3302927a8b1a287df6977041b2820eee07c",
  "activation":"b212fe38f3211e99f1a2c7a2ab04f09ee246149d",
  "receipt":"6810cce4dfeee587fde449951f17da8d37c1eb6e",
}
for k,p in paths.items():
    got=blob(ROOT/p)
    assert got==expected[k],(k,got,expected[k])

root3=json.loads((ROOT/paths["root3"]).read_text())
activation=json.loads((ROOT/paths["activation"]).read_text())
receipt=json.loads((ROOT/paths["receipt"]).read_text())

auth=root3["authority"]["universal_learning_v3_overlay"]
assert auth["activation_git_blob_sha"]==expected["activation"]
assert auth["verification_git_blob_sha"]==expected["receipt"]
assert "INDEPENDENT_PUBLIC_RUNNER_PASS" in auth["status"]

target=next(x for x in root3["compressed_residuals"] if x["predicate_id"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT")
assert target["operative_learning_overlay"]=="UNIVERSAL_LEARNING_DECISION_ROUTER_V3"
assert target["operative_learning_overlay_verified"] is True
assert target["current_residual"]=="TWO_FROZEN_INFORMATION_SAFE_DIRECT_ORACLE_LEAVES__OPERATIVE_V3_LEARNING_OVERLAY_VERIFIED"
assert "USE_THE_VERIFIED_V3_OPERATIVE_LEARNING_OVERLAY" in target["next"]

assert activation["status"]=="ACTIVE_MAIN__INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_CREDIT__UNKNOWN_DOMAIN_LEAVES_PRESERVED"
assert activation["activation_scope"]=="CANONICAL_MAIN"

pres=activation["preserved_residual"]
assert pres["predicate_id"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
assert pres["acceptance_proved"] is False
assert pres["leaves_closed"]==0
assert pres["leaves_open"]==2
assert "TWO_FROZEN_INFORMATION_SAFE_DIRECT_ORACLE_LEAVES" in pres["current_residual"]

assert receipt["independent_runner"]["conclusion"]=="success"
assert receipt["acceptance_credit_delta"]==0
assert receipt["family_credit_delta"]==0
assert receipt["capability_credit_delta"]==0
assert receipt["ownership_credit_delta"]==0
assert receipt["fresh_reality_authority"] is False

assert root3["acceptance_credit_delta"]==0
assert root3["family_credit_delta"]==0
assert root3["capability_credit_delta"]==0
assert root3["ownership_credit_delta"]==0
assert root3["fresh_reality_authority"] is False

print(json.dumps({
  "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V3_MAIN_STATUS_PROJECTION_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__EXACT_POINTER_CHAIN__TWO_OPEN_ZERO_CLOSED__ZERO_CREDIT",
  "pass":True,
  "exact_blob_identities":True,
  "root3_to_activation_pointer":True,
  "root3_to_verification_pointer":True,
  "unknown_domain_leaves_open":2,
  "unknown_domain_leaves_closed":0,
  "acceptance_proved":False,
  "acceptance_credit_delta":0,
  "ownership_credit_delta":0,
  "new_reality_units_consumed":0
},indent=2,sort_keys=True))
