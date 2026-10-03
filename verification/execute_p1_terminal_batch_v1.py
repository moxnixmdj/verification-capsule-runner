from __future__ import annotations
import hashlib, json, os
from pathlib import Path
from canonical.runtime import p1_shared_failure_semantics_batch_v1 as batch

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
 "canonical/governance/P1_SHARED_FAILURE_SEMANTICS_ONE_USE_EXECUTION_ACTIVATION_V1.json":"adde681aef00e7c65be60555b93add6dfcd963f0",
 "canonical/governance/P1_SHARED_FAILURE_SEMANTICS_BATCH_FREEZE_V1.json":"6a4b606a759d5479bb5ddbdf29426b1a1808b007",
 "canonical/runtime/p1_shared_failure_semantics_batch_preflight_v1.py":"13c33adda55f58d1eac913e63daa7f6ae1eb6a63",
 "canonical/runtime/p1_shared_failure_semantics_batch_v1.py":"695cfe3f283723a52bafb6299236a2d0378dc79e",
 "canonical/runtime/p1_shared_failure_semantics_normalizer_v1.py":"b6ba06fc6a35fa132eb19389ee256e74a63a4849",
 "canonical/runtime/contract_native_proof_suites.py":"0210790c7dd705ef328e1b55d529a30c5c6c3337",
 "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py":"28940387bd6c11671035ad9201e37bba13fd9bc9",
 "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py":"0f41a36e6ad16722ce05b180e036fb921a2ef886",
 "canonical/tests/test_p1_shared_failure_semantics_batch_v1.py":"7512a920c72d7bdeb2b072788e4c4bc8d2ff2d08",
 "canonical/tests/test_p1_shared_failure_semantics_batch_preflight_v1.py":"2b0b7a8b3fe7017e1be0fa85bed0f10b72802337",
}
def git_blob_sha(path:Path)->str:
 data=path.read_bytes()
 h=hashlib.sha1()
 h.update(f"blob {len(data)}\0".encode())
 h.update(data)
 return h.hexdigest()
for rel,want in EXPECTED.items():
 got=git_blob_sha(ROOT/rel)
 if got!=want: raise SystemExit(f"EXACT_BLOB_MISMATCH:{rel}:{got}:{want}")
attempt=os.environ.get("GITHUB_RUN_ATTEMPT","")
run_id=os.environ.get("GITHUB_RUN_ID","")
if attempt!="1": raise SystemExit("FIRST_ATTEMPT_ONLY")
if not run_id.isdigit(): raise SystemExit("RUN_ID_INVALID")
beacon=f"{run_id}:{attempt}"
result=batch.run_batch(beacon)
canonical=json.dumps(result,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
case_bytes=json.dumps(result.get("case_receipts",[]),sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
summary={
 "schema":"PROJECT_BRAIN_P1_SHARED_FAILURE_SEMANTICS_TERMINAL_BATCH_RESULT_SUMMARY_V1",
 "activation_git_blob_sha":"adde681aef00e7c65be60555b93add6dfcd963f0",
 "github_run_id":int(run_id),
 "github_run_attempt":int(attempt),
 "beacon_sha256":result.get("beacon_sha256"),
 "result_sha256":hashlib.sha256(canonical).hexdigest(),
 "case_receipts_sha256":hashlib.sha256(case_bytes).hexdigest(),
 "cases":result.get("cases"),
 "passes":result.get("passes"),
 "failures":result.get("failures"),
 "pass":result.get("pass"),
 "terminal_v3_replayed":result.get("terminal_v3_replayed"),
 "runtime_fresh_reality_units_consumed":result.get("fresh_reality_units_consumed"),
 "authorized_reality_unit_candidate":result.get("reality_unit_candidate_if_separately_authorized_and_independently_adjudicated"),
 "incremental_spend_usd":result.get("incremental_spend_usd"),
 "by_surface":result.get("by_surface"),
}
Path("p1-terminal-result.json").write_bytes(canonical)
print("P1_TERMINAL_RESULT_SUMMARY="+json.dumps(summary,sort_keys=True,separators=(",",":")))
assert result.get("pass") is True, summary
assert result.get("cases")==192 and result.get("passes")==192 and result.get("failures")==0, summary
assert result.get("terminal_v3_replayed")==0, summary
assert result.get("incremental_spend_usd")==0, summary
assert result.get("reality_unit_candidate_if_separately_authorized_and_independently_adjudicated")==1, summary
for surface,row in (result.get("by_surface") or {}).items():
 assert row.get("cases")==64 and row.get("passes")==64 and row.get("all_pass") is True, (surface,row)
 assert row.get("both_semantics_classes_present_every_case") is True, (surface,row)
print("P1_TERMINAL_BATCH_FIRST_ATTEMPT_PASS")
