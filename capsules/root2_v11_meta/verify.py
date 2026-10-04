from __future__ import annotations
import hashlib, json, py_compile
from pathlib import Path

B=Path("capsules/root2_v11_meta")
EXPECTED={
 "v11.json":"6857750dea3a0af48a5acc545b6f66b619d4335b",
 "v11_verification.json":"89884cc421eb8c7aff3e2bf9a17666478a31db94",
 "v11_activation.json":"3bcd26a57e1b81d0eb5245312e98520b5704febf",
 "policy_v2.json":"c5b9a287b51c0594f7925770f0f22fbbbb2738dc",
 "policy_v3.json":"e3d4bb102d8825798cb42b5f45382420fef41fbf",
 "meta_v3_activation.json":"ea10d3f8ef25add304dbc4b19c4f5ce712e3d7ce",
 "root3_v2.json":"4d8ce78ebe312100bbfc524062199961c0c6479d",
 "retrieval.json":"55b1d411561f720fcd9d66c127cecd63ef0b5f5e",
 "scheduler_runtime.py":"bfffe6dff32f5445a0c52657f7d9ec8d544b1f79",
}
def blob(p:Path):
 b=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,h in EXPECTED.items():
 assert blob(B/n)==h,(n,h,blob(B/n))

v11=json.loads((B/"v11.json").read_text())
v11v=json.loads((B/"v11_verification.json").read_text())
v11a=json.loads((B/"v11_activation.json").read_text())
p2=json.loads((B/"policy_v2.json").read_text())
p3=json.loads((B/"policy_v3.json").read_text())
m3=json.loads((B/"meta_v3_activation.json").read_text())
r3=json.loads((B/"root3_v2.json").read_text())
ret=json.loads((B/"retrieval.json").read_text())

assert v11v["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert v11v["subject_git_blob_sha"]==EXPECTED["v11.json"]
assert v11a["subject"]["git_blob_sha"]==EXPECTED["v11.json"]
assert v11a["verification"]["git_blob_sha"]==EXPECTED["v11_verification.json"]
assert v11a["authority"]["scheduling_authority"] is True
assert v11a["authority"]["effective_scheduling_authority"] is False
assert v11a["authority"]["execution_authority"] is False
assert v11a["authority"]["promotion_authority"] is False
assert v11a["authority"]["fresh_reality_authority"] is False

assert p3["schema"]=="PROJECT_BRAIN_TERMINAL_ADAPTIVE_MINIMUM_ACTION_POLICY_V3"
assert p3["verified_runtime"]==p2["verified_runtime"]
assert p3["optimization"]==p2["optimization"]
assert p3["exact_live_state"]==p2["exact_live_state"]
assert p3["exact_live_state"]["accepted_families"]==5
assert p3["exact_live_state"]["proved_atomic"]==12
assert p3["exact_live_state"]["unresolved_atomic"]==26

assert p3["authority_bindings"]["root2"]["frontier_git_blob_sha"]==EXPECTED["v11.json"]
assert p3["authority_bindings"]["root2"]["final_activation_git_blob_sha"]==EXPECTED["v11_activation.json"]
assert p3["authority_bindings"]["root2"]["effective_scheduling_authority"] is False
assert p3["authority_bindings"]["root2"]["execution_authority"] is False
assert p3["authority_bindings"]["root2"]["fresh_reality_authority"] is False

assert p3["authority_bindings"]["root3"]==p2["authority_bindings"]["root3"]
assert p3["authority_bindings"]["retrieval"]==p2["authority_bindings"]["retrieval"]
assert p3["authority_bindings"]["root3"]["cut_git_blob_sha"]==EXPECTED["root3_v2.json"]
assert p3["authority_bindings"]["retrieval"]["current_authority_git_blob_sha"]==EXPECTED["retrieval.json"]

assert p3["execution_authority"] is False
assert p3["promotion_authority"] is False
assert p3["fresh_reality_authority"] is False
assert p3["accounting"]["incremental_spend_usd"]==0
assert p3["accounting"]["terminal_cases_consumed"]==0
assert p3["accounting"]["acceptance_credit_delta"]==0

assert m3["subject"]["policy_git_blob_sha"]==EXPECTED["policy_v3.json"]
assert m3["subject"]["root2_activation_git_blob_sha"]==EXPECTED["v11_activation.json"]
assert m3["domain_authorities"]["root3"]["git_blob_sha"]==EXPECTED["root3_v2.json"]
assert m3["domain_authorities"]["retrieval"]["git_blob_sha"]==EXPECTED["retrieval.json"]
assert m3["authority"]["scheduling"] is True
assert m3["authority"]["meta_scheduling"] is True
assert m3["authority"]["effective_meta_scheduling"] is False
assert m3["authority"]["execution"] is False
assert m3["authority"]["promotion"] is False
assert m3["authority"]["fresh_reality"] is False

assert "FINANCE_INDEX_GENERIC_PUBLIC_INNER_TRANSFORM_SEARCH" in p3["preserved_search_deletions"]
assert "OSWORLD_GENERIC_TASK_WEB_GITLAB_REVISION_DISCOVERY_SEARCH" in p3["preserved_search_deletions"]
assert "FINANCE_INDEX_GENERIC_PUBLIC_INNER_TRANSFORM_SEARCH" not in p2["preserved_search_deletions"]
assert "OSWORLD_GENERIC_TASK_WEB_GITLAB_REVISION_DISCOVERY_SEARCH" not in p2["preserved_search_deletions"]

assert r3.get("fresh_reality_authority") is False
assert ret["status"]
py_compile.compile(str(B/"scheduler_runtime.py"),doraise=True)
print("ROOT2_V11_META_V3_PACKAGE_PASS__SCHEDULER_SEMANTICS_PRESERVED__ZERO_CREDIT__NO_FRESH_REALITY")
