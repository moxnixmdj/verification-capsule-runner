#!/usr/bin/env python3
import json
from pathlib import Path
x=json.loads(Path("root2_exact18_activation_candidate_v1.json").read_text())
assert x["schema"]=="PROJECT_BRAIN_ROOT2_POST_LIVEBENCH_EXACTPASS_18_REBIND_ACTIVATION_CANDIDATE_V1"
assert x["subject"]["git_blob_sha"]=="46411d83217b23c74ba700a6f065be49e20557df"
sv=x["subject_verification"]
assert sv["git_blob_sha"]=="16202325c9c43d95ee5f6e07bc9acdcdda740ed1"
assert sv["public_run_id"]==37239254248 and sv["public_job_id"]==111544455306
assert sv["conclusion"]=="success"
p=x["exact_preconditions"]
assert p["root_state_git_blob_sha"]=="7407b6aa35dbf3113fe5f9f4c4b2150b95504b47"
assert p["evidence_ledger_git_blob_sha"]=="56dcdc8a56c20b3ca26cb40fb6053945c3934daf"
assert p["root2_touching_count"]==18
assert p["unresolved_total"]==25
assert p["livebench_predicate_state"]=="PROVED"
a=x["authority"]
assert a["scheduling"] is True
assert a["execution"] is False
assert a["promotion"] is False
assert a["fresh_reality"] is False
assert a["acceptance_credit"] is False
assert "NO_LIVEBENCH_IF_GE_65_7_ROOT2_WORK" in x["scheduler_contract"]
assert any("FAIL_CLOSED" in s for s in x["scheduler_contract"])
assert x["accounting"]["incremental_spend_usd"]==0
assert x["accounting"]["acceptance_credit_delta"]==0
print(json.dumps({"status":"PASS","scheduling":True,"root2_touching":18,"execution":False,"fresh_reality":False},sort_keys=True))
