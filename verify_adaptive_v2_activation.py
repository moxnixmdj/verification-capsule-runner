#!/usr/bin/env python3
import json
from pathlib import Path

R=Path(__file__).resolve().parent
def J(n): return json.loads((R/n).read_text())

a=J("ADAPTIVE_ACTIVATION_V1.json")
root=J("ADAPTIVE_ACTIVATION_ROOT_STATE_V1.json")
term=J("ADAPTIVE_ACTIVATION_TERMINAL_AUTHORITY_V1.json")

assert a["schema"]=="PROJECT_BRAIN_TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V2_ACTIVATION_V1"
assert a["authority"]=={
  "scheduling":True,
  "meta_scheduling":True,
  "execution":False,
  "promotion":False,
  "fresh_reality":False
}
assert a["subject"]["policy_git_blob_sha"]=="c5b9a287b51c0594f7925770f0f22fbbbb2738dc"
assert a["subject"]["runtime_git_blob_sha"]=="bfffe6dff32f5445a0c52657f7d9ec8d544b1f79"
assert a["domain_authorities"]["root2"]["frontier"].endswith("ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json")
assert a["domain_authorities"]["root3"]["minimum_cut"].endswith("ROOT3_MINIMUM_ACTION_CUT_V2.json")
assert a["domain_authorities"]["retrieval"]["mandatory_entrypoint"].endswith("global_retrieval_entrypoint_v4.py")
assert "META_SCHEDULER_CANNOT_CREATE_EXECUTION_AUTHORITY" in a["hard_rules"]
assert a["accounting"]["incremental_spend_usd"]==0
assert a["accounting"]["terminal_cases_consumed"]==0

rp=root["scheduler_policy"]["adaptive_meta_scheduler"]
assert rp["activation_git_blob_sha"]=="0a70eb7ff3cfbe07e4765f2e490351fbaa505030"
assert rp["policy_git_blob_sha"]=="c5b9a287b51c0594f7925770f0f22fbbbb2738dc"
assert rp["runtime_git_blob_sha"]=="bfffe6dff32f5445a0c52657f7d9ec8d544b1f79"
assert rp["execution_authority"] is False
assert rp["promotion_authority"] is False
assert rp["fresh_reality_authority"] is False
assert root["scheduler_policy"]["root2_effective_scheduling_authority"] is True
assert root["root3_current_execution_state"]["currently_runnable_event_count"]==0
assert root["root3_current_execution_state"]["fresh_reality_authority"] is False

tp=term["authorities"]["terminal_adaptive_minimum_action_policy_v2"]
assert tp["activation_git_blob_sha"]=="0a70eb7ff3cfbe07e4765f2e490351fbaa505030"
assert tp["policy_git_blob_sha"]=="c5b9a287b51c0594f7925770f0f22fbbbb2738dc"
assert tp["runtime_git_blob_sha"]=="bfffe6dff32f5445a0c52657f7d9ec8d544b1f79"
assert tp["precedence"]=="META_SCHEDULER_AFTER_ROOT2_V10_ROOT3_V2_DOMAIN_GATES"
assert tp["execution_authority"] is False
assert tp["promotion_authority"] is False
assert tp["fresh_reality_authority"] is False
assert term["truth"]["achieved"] is False

print(json.dumps({
 "status":"PASS",
 "adaptive_meta_scheduler":"V2",
 "root2":"V10_DOMAIN_GATE_PRESERVED",
 "root3":"V2_ZERO_RUNNABLE_PRESERVED",
 "execution":False,
 "fresh_reality":False,
 "zero_spend":True
},sort_keys=True))
