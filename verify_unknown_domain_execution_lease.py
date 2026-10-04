from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LEASE=ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_V1.json"
raw=LEASE.read_bytes()
lease=json.loads(raw)
assert lease["schema"]=="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_V1"
assert lease["target_predicate"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
assert set(lease["authorized_leaves"])=={
 "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE",
 "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"
}
assert lease["limits"]=={
 "production_populations":1,
 "production_cases":27,
 "max_transfer_probes_per_case":2,
 "replay_allowed":False,
 "replacement_allowed":False,
 "post_result_tuning_allowed":False
}
assert lease["resources"]=={
 "persistent_learned_bytes":0,
 "external_frontier_model_calls":0,
 "external_learned_capability_calls":0,
 "incremental_spend_usd":0
}
assert lease["verification_chain"]["qualification"]["conclusion"]=="success"
assert lease["verification_chain"]["qualification"]["fresh_hidden_scored_cases"]==81
assert lease["verification_chain"]["final_activation"]["conclusion"]=="success"
assert lease["verification_chain"]["point_of_use_preflight"]["status"]=="READY_FOR_ATOMIC_ONE_USE_CLAIM_ONLY"
assert lease["verification_chain"]["production_launcher"]["conclusion"]=="success"
assert lease["atomic_claim"]["required_first_claim_create_http_status"]==201
assert lease["atomic_claim"]["claim_uniqueness_source"]=="ATOMIC_CREATE_RESPONSE"
assert lease["authority"]=={"global_fresh_reality":False,"promotion":False,"acceptance_credit":False}
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,expected in lease["exact_components"].items():
 p=ROOT/rel
 assert p.is_file(),rel
 got=blob(p.read_bytes())
 assert got==expected,(rel,got,expected)
digest=hashlib.sha256(raw).hexdigest()
print(json.dumps({
 "status":"INDEPENDENT_EXECUTION_LEASE_PASS",
 "execution_lease_git_blob_sha":blob(raw),
 "execution_lease_sha256":digest,
 "exact_component_count":len(lease["exact_components"]),
 "production_cases_allowed":27,
 "persistent_learned_bytes":0,
 "global_fresh_reality":False
},sort_keys=True))
