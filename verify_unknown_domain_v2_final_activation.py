from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED={
"canonical/governance/UNKNOWN_DOMAIN_DIRECT_PREDICATE_LOCAL_ACTIVATION_V1.json":"337bb7ee777e8b0f7f6340f395ca6c50e466594c",
"canonical/verification/UNKNOWN_DOMAIN_V2_ACTIVATION_CANDIDATE_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"32d6dc95d81211be13fd96aa91165ebf321197a0",
"canonical/governance/UNKNOWN_DOMAIN_DIRECT_PREDICATE_LOCAL_ACTIVATION_CANDIDATE_V1.json":"1d05dc42fc34b1d97d3d6c12addfe690f475a505",
"canonical/verification/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"36452412fb60ce38405f139111eba98b5cebc040"
}
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for p,e in EXPECTED.items():
 g=blob((ROOT/p).read_bytes()); assert g==e,(p,g,e)
a=json.loads((ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_PREDICATE_LOCAL_ACTIVATION_V1.json").read_text())
assert a["active"] is True
assert a["target_predicate"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
assert a["authorized_predicates"]==["UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"]
assert set(a["authorized_leaves"])=={"CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE","CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"}
assert a["authority"]["execution"] is True
assert a["authority"]["predicate_local_fresh_reality"] is True
assert a["authority"]["global_fresh_reality"] is False
assert a["authority"]["promotion"] is False
assert a["authority"]["acceptance_credit"] is False
assert a["authority"]["all_other_unresolved_predicates_authorized"] is False
assert a["resource_boundary"]=={"persistent_learned_bytes":0,"external_frontier_model_calls":0,"external_learned_capability_calls":0,"incremental_spend_usd":0}
assert a["production_budget"]["production_populations_allowed"]==1
assert a["production_budget"]["production_cases_allowed"]==27
assert a["production_budget"]["replay_allowed"] is False
assert "ONE_USE_CLAIM_IS_MANDATORY_BEFORE_BEACON_OR_CASE_GENERATION" in a["hard_rules"]
print(json.dumps({"status":"INDEPENDENT_FINAL_ACTIVATION_PASS","target_predicate":a["target_predicate"],"predicate_local_fresh_reality":True,"global_fresh_reality":False,"persistent_learned_bytes":0},sort_keys=True))
