from __future__ import annotations
import hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
PUBLIC_ROOT=ROOT.parent
EXPECTED={
 "ACTION_INTENT_TB_SCIENCE_RANK10_ONE_SHOT_20261007_V1.json":"325a27f5559c1839c839c8cca0626b6c5c22f95c",
 "TB_SCIENCE_RANK10_ONE_SLOT_EXECUTION_AUTHORITY_20261007_V1.json":"075cd46fed1504c4295249d5da4c1782bde253b3",
 "TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261007_V8.json":"d826315ba393c93f52a24aab9568691948b7cdf3",
 "TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261007_V2.json":"31656d35034338dfcb699672bcd4788b283b83c9",
 "TB_SCIENCE_REPAIRED_TRANSITIVE_CARRIER_CLOSURE_PUBLIC_VERIFICATION_20261007_V1.json":"61495f5977ea745e63ca14136875b97e3e95cd45",
 "TB_SCIENCE_PLANNER_TRANSPORT_REPAIR_LIVE_VERIFICATION_20261007_V1.json":"877e5ddf815c1958f4ab41f8462ad54af87f0c87",
 "TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json":"6dfa880b1f68881531afbba6ca211681801fd19b",
}
EPOCH_PATH=PUBLIC_ROOT/"tb_science_rank10_20261007_v1/RANK10_EPOCH_V1.json"
EPOCH_SHA="8d0bc7999769a32147eab08acb31436e7abe743c"
SLOT="terminal-bench-science/rdkit-ic-constraints::trial-0"
TASK="terminal-bench-science/rdkit-ic-constraints"
DIGEST="sha256:17e356ab255088712c7dfa9765bf077b33a3da221f4a03d4770576857f9c0b6f"
ROUTE={
 "agent":"5bc8ebac26bb7c809d4698f535eff43b667b30df",
 "planner":"01d859c8f27b317893027e693c9aa49e833a256f",
 "raw_task_contract":"d54d5a2f7efa76b653d288f4f53da4883644baa6",
 "raw_task_localizer":"f29616cf7726959aa28db4ed6541a9fc0bc2ac76",
}

def blob(p:pathlib.Path)->str:
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

for name,want in EXPECTED.items():
 got=blob(ROOT/name)
 assert got==want,(name,got,want)
assert EPOCH_PATH.is_file()
assert blob(EPOCH_PATH)==EPOCH_SHA,(blob(EPOCH_PATH),EPOCH_SHA)

load=lambda name: json.loads((ROOT/name).read_text())
intent=load("ACTION_INTENT_TB_SCIENCE_RANK10_ONE_SHOT_20261007_V1.json")
auth=load("TB_SCIENCE_RANK10_ONE_SLOT_EXECUTION_AUTHORITY_20261007_V1.json")
ledger=load("TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261007_V8.json")
closure=load("TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261007_V2.json")
closure_receipt=load("TB_SCIENCE_REPAIRED_TRANSITIVE_CARRIER_CLOSURE_PUBLIC_VERIFICATION_20261007_V1.json")
transport=load("TB_SCIENCE_PLANNER_TRANSPORT_REPAIR_LIVE_VERIFICATION_20261007_V1.json")
manifest=load("TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json")
epoch=json.loads(EPOCH_PATH.read_text())

truth=ledger["truth_repair"]
assert len(truth["consumed_slots"])==9
assert SLOT not in truth["consumed_slots"]
assert truth["consumed_successes"]==0
assert truth["consumed_final_failures"]==9
assert truth["next_untouched_slot"]=={"schedule_rank":10,"slot_id":SLOT,"task_digest":DIGEST}
assert truth["pass_still_mathematically_reachable"] is True
pre=ledger["rank10_preflight"]
assert pre["next_untouched_slot"]==truth["next_untouched_slot"]
assert pre["infrastructure_preconditions_closed"] is True
assert pre["task_started"] is False and pre["result_present"] is False
assert pre["planner_transport"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_PLANNER_TRANSPORT_REPAIR_LIVE_VERIFICATION_20261007_V1.json"]
assert pre["planner_transport"]["independently_verified"] is True
assert pre["repaired_transitive_closure"]["manifest_git_blob_sha"]==EXPECTED["TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261007_V2.json"]
assert pre["repaired_transitive_closure"]["verification_git_blob_sha"]==EXPECTED["TB_SCIENCE_REPAIRED_TRANSITIVE_CARRIER_CLOSURE_PUBLIC_VERIFICATION_20261007_V1.json"]
assert pre["repaired_transitive_closure"]["exact_file_count"]==14
assert pre["public_epoch"]["git_blob_sha"]==EPOCH_SHA

assert transport["status"].startswith("INDEPENDENT_LIVE_LLAMA_CPP_TRANSPORT_PASS")
tv=transport["verified"]
for k in ("exact_byte_gate_passed","planner_unit_tests_passed","clean_llama_cpp_build_passed","exact_model_hash_passed","local_endpoint_health_passed","live_tool_schema_and_decode_probe_passed","decoded_command_bound_enforced"):
 assert tv[k] is True,k
assert tv["benchmark_task_exposure"]==0
assert transport["subject"]["planner_git_blob_sha"]==ROUTE["planner"]

assert len(closure["closure"])==14
assert closure["planner_transport_repair_blob"]==ROUTE["planner"]
assert closure_receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__REPAIRED_14_FILE_CLOSURE")
cv=closure_receipt["verified"]
for k in ("exact_repaired_closure_recomputed","all_manifest_blob_identities_match","complete_exact_carrier_closure_gate_pass","agent_import_pass","planner_import_pass","adversarial_missing_dependency_gate_pass","adversarial_mutated_dependency_gate_pass","dynamic_local_import_fail_closed_pass","path_escape_fail_closed_pass"):
 assert cv[k] is True,k
assert cv["exact_science_runtime_closure_file_count"]==14
assert cv["benchmark_task_exposure"]==0

assert intent["status"].startswith("READY__INFRASTRUCTURE_PREFLIGHTS_VERIFIED")
assert intent["slot"]=={"id":SLOT,"digest":DIGEST,"rank":10}
assert intent["exact_route"]==ROUTE
assert intent["current_ledger"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261007_V8.json"]
assert intent["planner_transport_verification"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_PLANNER_TRANSPORT_REPAIR_LIVE_VERIFICATION_20261007_V1.json"]
assert intent["transitive_runtime_closure"]["manifest"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261007_V2.json"]
assert intent["transitive_runtime_closure"]["independent_verification"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_REPAIRED_TRANSITIVE_CARRIER_CLOSURE_PUBLIC_VERIFICATION_20261007_V1.json"]
assert intent["public_epoch"]["git_blob_sha"]==EPOCH_SHA
ic=intent["controls"]
assert ic["attempts"]==1 and ic["retries"]==0 and ic["replacement_allowed"] is False
assert ic["incremental_spend_usd_max"]==0 and ic["precheck_failure_consumes_slot"] is False
assert intent["credit"] is False

assert auth["status"].startswith("ACTIVE__VERIFIED_TRANSPORT_AND_REPAIRED_TRANSITIVE_CARRIER_PREFLIGHT_BOUND")
assert auth["slot"]=={"id":SLOT,"rank":10,"digest":DIGEST}
assert {k:auth["exact_route"][k] for k in ROUTE}==ROUTE
assert auth["exact_route"]["closure_compiler"]=="43d502c621c219632fa0f9a19632dfc0228e4847"
assert auth["exact_route"]["transitive_runtime_file_count"]==14
bind=auth["source_bindings"]
assert bind["intent"]["git_blob_sha"]==EXPECTED["ACTION_INTENT_TB_SCIENCE_RANK10_ONE_SHOT_20261007_V1.json"]
assert bind["ledger"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261007_V8.json"]
assert bind["planner_transport_verification"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_PLANNER_TRANSPORT_REPAIR_LIVE_VERIFICATION_20261007_V1.json"]
assert bind["carrier_closure_manifest"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261007_V2.json"]
assert bind["carrier_closure_verification"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_REPAIRED_TRANSITIVE_CARRIER_CLOSURE_PUBLIC_VERIFICATION_20261007_V1.json"]
assert bind["frozen_manifest"]["git_blob_sha"]==EXPECTED["TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json"]
assert auth["live_epoch"]["git_blob_sha"]==EPOCH_SHA
ac=auth["controls"]
assert ac["exact_slot_count"]==1 and ac["attempts"]==1 and ac["retries"]==0
assert ac["replacement_allowed"] is False and ac["incremental_spend_usd_max"]==0
for k in ("exact_carrier_blob_identity_required","recompute_current_transitive_closure_before_task_start","agent_and_planner_import_required_before_task_start","planner_transport_repair_must_match_verified_blob","current_public_epoch_must_match_immediately_before_task_start"):
 assert ac[k] is True,k
assert ac["precheck_failure_consumes_slot"] is False
assert ac["after_task_start_result_is_irreversible"] is True
assert ac["after_task_start_missing_or_zero_verifier_result_counts_as_final_zero"] is True
at=auth["current_truth"]
assert at["slot_is_next_untouched"] is True and at["prior_consumed_slots"]==9
assert at["planner_transport_precondition_closed"] is True
assert at["repaired_transitive_carrier_precondition_closed"] is True
assert at["task_started"] is False and at["result_present"] is False
assert at["acceptance_credit"] is False and at["terminal_credit"] is False

assert epoch["status"]=="CURRENT__ONE_USE_PREEXPOSURE_GATE"
assert epoch["epoch_id"]=="TBSCI-RANK10-20261007-E1"
assert epoch["slot_id"]==SLOT and epoch["task_digest"]==DIGEST and epoch["schedule_rank"]==10
assert epoch["benchmark_task_exposure_authorized_by_epoch"] is False
assert epoch["execution_authority_required_from_brain"] is True
assert epoch["run_attempts_authorized_by_epoch"]==0
assert epoch["incremental_spend_usd_max"]==0

assert manifest["frozen_dataset"]["slot_count"]==210
assert manifest["acceptance"]["required_successes"]==124
assert manifest["acceptance"]["irreversible_failure_count"]==87
rows=[x for x in manifest["task_metadata"] if x["name"]==TASK]
assert len(rows)==1 and rows[0]["digest"]==DIGEST
schedule=[x for x in manifest["slot_schedule"] if x["slot_id"]==SLOT]
assert len(schedule)==1 and schedule[0]["schedule_order"]==10 and schedule[0]["task_digest"]==DIGEST

print(json.dumps({
 "status":"PASS",
 "rank10_slot_untouched":True,
 "exact_authority_blob":EXPECTED["TB_SCIENCE_RANK10_ONE_SLOT_EXECUTION_AUTHORITY_20261007_V1.json"],
 "exact_epoch_blob":EPOCH_SHA,
 "transport_precondition_independently_bound":True,
 "exact_repaired_transitive_runtime_file_count":14,
 "benchmark_task_exposure":0,
 "incremental_spend_usd":0,
 "acceptance_credit_delta":0,
 "terminal_credit_delta":0
},sort_keys=True))
