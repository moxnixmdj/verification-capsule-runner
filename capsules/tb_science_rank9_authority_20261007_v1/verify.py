from __future__ import annotations
import hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
PUBLIC_ROOT=ROOT.parents[1]
EXPECTED={
 "ACTION_INTENT_TB_SCIENCE_RANK9_ONE_SHOT_20261007_V1.json":"54dfd6dbdf858b386b8a6fa303b55e6ea5803f04",
 "TB_SCIENCE_RANK9_ONE_SLOT_EXECUTION_AUTHORITY_20261007_V1.json":"af464670453e432367531edb17e8590959ae5c41",
 "TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261007_V6.json":"b82cffd09260c6792f473c952d2f0644bb2ca1fa",
 "TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261007_V1.json":"4b2a4fb3bd85b066e642a0253d4c325dbb431237",
 "TB_SCIENCE_TRANSITIVE_CARRIER_CLOSURE_PUBLIC_VERIFICATION_20261007_V1.json":"cb8c4e36ee47dc2542b120a4a631de6ebdd4e8c5",
 "TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json":"6dfa880b1f68881531afbba6ca211681801fd19b",
}
EPOCH_PATH=PUBLIC_ROOT/"tb_science_rank9_20261007_v1/RANK9_EPOCH_V1.json"
EPOCH_SHA="a172896454ef0faf405dc371ac06a01acc866c76"

def blob(p):
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

for name,want in EXPECTED.items():
 got=blob(ROOT/name); assert got==want,(name,got,want)
assert EPOCH_PATH.is_file(),EPOCH_PATH
assert blob(EPOCH_PATH)==EPOCH_SHA,(blob(EPOCH_PATH),EPOCH_SHA)

load=lambda name: json.loads((ROOT/name).read_text())
intent=load("ACTION_INTENT_TB_SCIENCE_RANK9_ONE_SHOT_20261007_V1.json")
auth=load("TB_SCIENCE_RANK9_ONE_SLOT_EXECUTION_AUTHORITY_20261007_V1.json")
ledger=load("TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261007_V6.json")
closure=load("TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261007_V1.json")
closure_receipt=load("TB_SCIENCE_TRANSITIVE_CARRIER_CLOSURE_PUBLIC_VERIFICATION_20261007_V1.json")
manifest=load("TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json")
epoch=json.loads(EPOCH_PATH.read_text())

slot="terminal-bench-science/neo-orbit-determination::trial-0"
digest="sha256:b0038fd39395b57f2036b2c0271f37b508e1250fc97d12c899590b61e997cada"
route={
 "agent":"5bc8ebac26bb7c809d4698f535eff43b667b30df",
 "planner":"c3e36eba57c450f325c8a9476ee048c841bbdbc8",
 "raw_task_contract":"d54d5a2f7efa76b653d288f4f53da4883644baa6",
 "raw_task_localizer":"f29616cf7726959aa28db4ed6541a9fc0bc2ac76",
}

truth=ledger["truth_repair"]
assert len(truth["consumed_slots"])==8
assert slot not in truth["consumed_slots"]
assert truth["next_untouched_slot"]["schedule_rank"]==9
assert truth["next_untouched_slot"]["slot_id"]==slot
assert truth["next_untouched_slot"]["task_digest"]==digest
assert truth["consumed_successes"]==0
assert truth["consumed_final_failures"]==8
assert truth["pass_still_mathematically_reachable"] is True

assert intent["status"]=="READY_AFTER_TRANSITIVE_CARRIER_CLOSURE_AND_LIVE_EPOCH_BINDING"
assert intent["slot"]=={"id":slot,"digest":digest,"rank":9}
assert intent["exact_route"]==route
assert intent["current_ledger"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261007_V6.json"]
assert intent["transitive_runtime_closure"]["manifest"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261007_V1.json"]
assert intent["transitive_runtime_closure"]["independent_verification"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_TRANSITIVE_CARRIER_CLOSURE_PUBLIC_VERIFICATION_20261007_V1.json"]
assert intent["transitive_runtime_closure"]["exact_file_count"]==14
assert intent["public_epoch"]["git_blob_sha"]==EPOCH_SHA
assert intent["controls"]["attempts"]==1 and intent["controls"]["retries"]==0
assert intent["controls"]["replacement_allowed"] is False
assert intent["controls"]["precheck_failure_consumes_slot"] is False
assert intent["credit"] is False

assert auth["status"].startswith("ACTIVE__TRANSITIVE_CARRIER_PREFLIGHT_REQUIRED")
assert auth["slot"]=={"id":slot,"rank":9,"digest":digest}
assert auth["exact_route"]=={**route,"transitive_runtime_file_count":14}
assert auth["source_bindings"]["intent"]["git_blob_sha"]==EXPECTED["ACTION_INTENT_TB_SCIENCE_RANK9_ONE_SHOT_20261007_V1.json"]
assert auth["source_bindings"]["ledger"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261007_V6.json"]
assert auth["source_bindings"]["carrier_closure_manifest"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261007_V1.json"]
assert auth["source_bindings"]["carrier_closure_verification"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_TRANSITIVE_CARRIER_CLOSURE_PUBLIC_VERIFICATION_20261007_V1.json"]
assert auth["source_bindings"]["manifest"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json"]
assert auth["live_epoch"]["git_blob_sha"]==EPOCH_SHA
assert auth["live_epoch"]["epoch_id"]=="TBSCI-RANK9-20261007-E1"
c=auth["controls"]
assert c["exact_slot_count"]==1 and c["attempts"]==1 and c["retries"]==0
assert c["replacement_allowed"] is False
assert c["recompute_current_transitive_closure_before_task_start"] is True
assert c["exact_carrier_blob_identity_required"] is True
assert c["agent_and_planner_import_required_before_task_start"] is True
assert c["precheck_failure_consumes_slot"] is False
assert c["after_task_start_result_is_irreversible"] is True
assert c["after_task_start_missing_or_zero_verifier_result_counts_as_final_zero"] is True
assert auth["current_truth"]["slot_is_next_untouched"] is True
assert auth["current_truth"]["rank8_infrastructure_failure_class_closed"] is True
assert auth["current_truth"]["task_started"] is False
assert auth["current_truth"]["result_present"] is False
assert auth["current_truth"]["acceptance_credit"] is False
assert auth["current_truth"]["terminal_credit"] is False

assert len(closure["closure"])==14
assert closure["rank8_counterexample"]["omitted_transitive_file_count"]==10
assert closure_receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_14_FILE_CLOSURE")
v=closure_receipt["verified"]
assert v["exact_science_runtime_closure_file_count"]==14
assert v["complete_exact_carrier_closure_gate_pass"] is True
assert v["harbor_science_agent_import_pass"] is True
assert v["harbor_science_planner_import_pass"] is True
assert v["benchmark_task_exposure"]==0
assert closure_receipt["causal_effect"]["rank8_failure_class_closed_as_preexposure_infrastructure_prerequisite"] is True

assert epoch["status"]=="CURRENT__ONE_USE_PREEXPOSURE_GATE"
assert epoch["epoch_id"]=="TBSCI-RANK9-20261007-E1"
assert epoch["slot_id"]==slot and epoch["task_digest"]==digest
assert epoch["attempts"]==1 and epoch["retries"]==0
assert epoch["precheck_failure_consumes_slot"] is False
assert epoch["after_task_start_result_is_irreversible"] is True
assert epoch["reuse_authority"] is False
assert manifest["fixed_denominator"]==210
assert manifest["required_successes"]==124

print(json.dumps({
 "status":"PASS",
 "rank9_slot_untouched":True,
 "exact_authority_blob":EXPECTED["TB_SCIENCE_RANK9_ONE_SLOT_EXECUTION_AUTHORITY_20261007_V1.json"],
 "exact_epoch_blob":EPOCH_SHA,
 "exact_transitive_runtime_file_count":14,
 "agent_and_planner_import_precondition_independently_bound":True,
 "benchmark_task_exposure":0,
 "incremental_spend_usd":0,
 "acceptance_credit_delta":0,
 "terminal_credit_delta":0
},sort_keys=True))
