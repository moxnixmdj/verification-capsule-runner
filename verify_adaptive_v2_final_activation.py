#!/usr/bin/env python3
import json
from pathlib import Path
R=Path(__file__).resolve().parent
def J(n): return json.loads((R/n).read_text())
a=J("ADAPTIVE_FINAL_ACTIVATION_V1.json")
root=J("ADAPTIVE_FINAL_ROOT_STATE_V1.json")
term=J("ADAPTIVE_FINAL_TERMINAL_AUTHORITY_V1.json")

assert a["schema"]=="PROJECT_BRAIN_TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V2_FINAL_ACTIVATION_V1"
assert a["status"].startswith("ACTIVE__")
assert a["candidate_activation"]["git_blob_sha"]=="0a70eb7ff3cfbe07e4765f2e490351fbaa505030"
assert a["candidate_verification"]["git_blob_sha"]=="61e374593ab3ef2867021532f92be06580c348b0"
assert a["candidate_verification"]["conclusion"]=="success"
assert a["active_subject"]["policy_git_blob_sha"]=="c5b9a287b51c0594f7925770f0f22fbbbb2738dc"
assert a["active_subject"]["runtime_git_blob_sha"]=="bfffe6dff32f5445a0c52657f7d9ec8d544b1f79"
assert a["authority"]=={"scheduling":True,"meta_scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}
assert a["accounting"]["incremental_spend_usd"]==0
assert a["accounting"]["terminal_cases_consumed"]==0

rp=root["scheduler_policy"]["adaptive_meta_scheduler"]
assert rp["final_activation_git_blob_sha"]=="637e8802e33856ba6760aaaf4999993f6df8b338"
assert rp["status"].startswith("ACTIVE__")
assert rp["execution_authority"] is False
assert rp["promotion_authority"] is False
assert rp["fresh_reality_authority"] is False
assert root["scheduler_policy"]["root2_effective_scheduling_authority"] is True
assert root["root3_current_execution_state"]["currently_runnable_event_count"]==0

tp=term["authorities"]["terminal_adaptive_minimum_action_policy_v2"]
assert tp["final_activation_git_blob_sha"]=="637e8802e33856ba6760aaaf4999993f6df8b338"
assert tp["status"].startswith("ACTIVE__")
assert tp["execution_authority"] is False
assert tp["promotion_authority"] is False
assert tp["fresh_reality_authority"] is False
assert tp["precedence"]=="META_SCHEDULER_AFTER_ROOT2_V10_ROOT3_V2_DOMAIN_GATES"
assert term["truth"]["achieved"] is False

print(json.dumps({
 "status":"PASS","adaptive_v2":"ACTIVE","root2_v10":True,
 "root3_v2_zero_runnable":True,"execution":False,"fresh_reality":False,
 "zero_spend":True
},sort_keys=True))
