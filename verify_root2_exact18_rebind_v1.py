#!/usr/bin/env python3
import json
from pathlib import Path
x=json.loads(Path("root2_post_livebench_exactpass_18_predicate_rebind_v1.json").read_text())
assert x["schema"]=="PROJECT_BRAIN_ROOT2_POST_LIVEBENCH_EXACTPASS_18_PREDICATE_REBIND_V1"
p=x["exact_partition"]
assert p["root1_only_count"]==0
assert p["root2_only_count"]==15
assert p["root3_only_count"]==7
assert p["root2_and_root3_count"]==3
assert p["root2_touching_count"]==18
assert p["unresolved_total"]==25
ids=p["root2_touching_predicates"]
assert len(ids)==18 and len(set(ids))==18
assert "LIVEBENCH_IF_GE_65_7" not in ids
assert set(ids)=={q["id"] for q in x["predicates"]}
rp=x["removed_predicate"]
assert rp["id"]=="LIVEBENCH_IF_GE_65_7"
assert rp["current_class"]=="PROVED__REMOVED_FROM_RESIDUAL_PARTITION"
assert rp["measurement_state"]=="RESOLVED_POSITIVELY"
assert rp["brain_percent"]>=rp["stricter_public_opus_floor_percent"]>=rp["threshold_percent"]
assert x["bindings"]["current_root_state"]["git_blob_sha"]=="7407b6aa35dbf3113fe5f9f4c4b2150b95504b47"
assert x["bindings"]["current_evidence_ledger"]["git_blob_sha"]=="56dcdc8a56c20b3ca26cb40fb6053945c3934daf"
assert x["bindings"]["livebench_exact200_verification"]["git_blob_sha"]=="82d5e90cb1662013eb452eade7815a04469749c4"
assert x["authority"]=={"scheduling":False,"execution":False,"promotion":False,"fresh_reality":False,"acceptance_credit":False}
expected_precedence=[
 "FORMAL_IMPLICATION_OR_OBJECTIVE_CEILING",
 "EXISTING_CONTENT_ADDRESSED_RECEIPT",
 "DETERMINISTIC_SCORER_OR_INVARIANT_CERTIFIED_MASS",
 "OWNER_SIDE_BLIND_SCORE_RECEIPT",
 "MINIMUM_EMPIRICAL_RESIDUAL",
 "FULL_BENCHMARK"
]
assert x["proof_precedence"]==expected_precedence
assert any("NO_RELATIVE_ELO_OR_RATING_INFERENCE" in z for z in x["hard_rules"])
assert any("NO_FRESH_REALITY_BEFORE_SEPARATE_EXPLICIT_AUTHORITY" in z for z in x["hard_rules"])
print(json.dumps({"status":"PASS","root2_touching":18,"unresolved":25,"root1":0,"livebench_removed":True},sort_keys=True))
