#!/usr/bin/env python3
import json
from pathlib import Path
R=Path(__file__).resolve().parent
def J(n): return json.loads((R/n).read_text())
x=J("ADAPTIVE_RECOMPUTE_V1.json")
f=J("RECOMPUTE_FINANCE_SATURATION_V1.json")
o=J("RECOMPUTE_OSWORLD_GITLAB_V1.json")
a=J("RECOMPUTE_ADAPTIVE_FINAL_ACTIVATION_V1.json")

assert x["schema"]=="PROJECT_BRAIN_TERMINAL_ADAPTIVE_RECOMPUTE_20261004_V1"
assert x["scheduler_authority"]["git_blob_sha"]=="637e8802e33856ba6760aaaf4999993f6df8b338"
assert a["status"].startswith("ACTIVE__")
assert x["prior_state"]["unresolved_atomic"]==26
assert x["recomputed_state"]["unresolved_atomic"]==26
assert x["prior_state"]["prior_primary_source_deletions"]==6
assert x["recomputed_state"]["deterministic_new_deletions"]==4
assert x["recomputed_state"]["effective_known_action_deletions"]==10
assert x["recomputed_state"]["root2_self_service_facts"]==9
assert x["recomputed_state"]["root2_owner_exclusive_facts"]==6
assert x["recomputed_state"]["root2_owner_or_direct_platform_facts"]==1
assert x["recomputed_state"]["root2_dormant_facts"]==2
assert x["recomputed_state"]["root3_current_runnable_events"]==0
assert x["recomputed_state"]["fresh_reality_authority"] is False
assert x["accounting"]["incremental_spend_usd"]==0
assert x["accounting"]["terminal_cases_consumed"]==0

finance_delete=set(f["scheduler_effect_if_independently_verified"]["delete"])
osworld_delete={o["verified_if_passes"]["delete"]}
declared=set()
for d in x["deterministic_new_deltas"]:
    declared.update(d.get("delete",[]))
assert finance_delete | osworld_delete == declared
assert len(declared)==4
assert "REPEAT_GENERIC_PUBLIC_SEARCH_FOR_FINANCE_CAPABILITY_INNER_TRANSFORM" in declared
assert "GENERIC_TASK_WEB_GITLAB_REVISION_DISCOVERY_SEARCH" in declared
assert "NO_FRESH_REALITY" in x["hard_rules"]

print(json.dumps({
 "status":"PASS",
 "prior_deletions":6,
 "new_deletions":4,
 "effective_deletions":10,
 "unresolved_atomic":26,
 "fresh_reality":False,
 "zero_spend":True
},sort_keys=True))
