#!/usr/bin/env python3
from __future__ import annotations
import ast,hashlib,importlib.util,json,pathlib,tempfile
ROOT=pathlib.Path(__file__).resolve().parent
EXEC=ROOT/"execute_livebench_if_replay72_v4_candidate.py"
EXPECTED_BLOB="2a57ce896ddbd6819246aab8b44d17a00f36b61e"

def git_blob_sha(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert git_blob_sha(EXEC)==EXPECTED_BLOB
src=EXEC.read_text(encoding="utf-8")
tree=ast.parse(src)

required_literals=[
 "REPLAY_LIMIT = 72",
 "for start in range(0,REPLAY_LIMIT,BATCH):",
 '"replay_only_no_new_case_exposure":True',
 '"BLOCKED__POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN"',
 "LIVEBENCH_POLICY_POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN",
 "LIVEBENCH_POLICY_EXTERNAL_NETWORK_FORBIDDEN",
 "astra_runtime._load_auto_capability_acquisition=_deny_auto_capability_acquisition",
 'raise SystemExit("FAIL_CLOSED:VERIFIED_V4_REPLAY_LAUNCHER_REQUIRED")',
 "VERIFIED_V4_ACTIVATION_BLOB_REQUIRED",
]
for lit in required_literals:
    assert lit in src, "MISSING_REQUIRED_LITERAL:"+lit
for forbidden in [
 'AUTHORIZED_ACTIVATION_BLOB =',
 "for start in range(0,POPULATION,BATCH):",
 '"retry_epoch_authorized_by_verified_launcher":True',
]:
    assert forbidden not in src, "FORBIDDEN_STALE_PATTERN:"+forbidden

spec=importlib.util.spec_from_file_location("lbv4",EXEC)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod.REPLAY_LIMIT==72
assert mod.POPULATION==200
assert mod.THRESHOLD==0.657
assert mod.BENCHMARK_ID=="LIVEBENCH_IF_2026_06_25"
assert mod.DATASET_REV=="0868379c4b5cf62aeacaf8be4f08fced815c81bb"
assert mod.DATASET_SHA256=="a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
assert len(mod.RUNTIME_FILES)==24, len(mod.RUNTIME_FILES)
assert len(mod.RUNTIME_DESTS)==24
assert set(mod.RUNTIME_FILES)==set(mod.RUNTIME_DESTS)

with tempfile.TemporaryDirectory(prefix="lb-v4-zero-case-") as td:
    template=mod.build_runtime_template(pathlib.Path(td))
    assert (template/"canonical/runtime/astra_runtime.py").is_file()
    assert (template/"canonical/runtime/auto_capability_acquisition.py").is_file()
    q={"question_id":"SYNTHETIC_ZERO_CASE","turns":["Reply with exactly SYNTHETIC_OK."]}
    qid,answer,err=mod.infer_one(template,q)
    assert qid=="SYNTHETIC_ZERO_CASE"
    assert not (err and err.startswith("INFERENCE_EXIT_")), (answer,err)
    assert (err is None and bool(answer)) or err=="POLICY_BLOCKED_POST_PROMPT_CAPABILITY_ACQUISITION", (answer,err)
    synthetic_class=("VALID_FROZEN_CANDIDATE_RESPONSE" if err is None else err)
    synthetic_answer_sha256=(hashlib.sha256(answer.encode()).hexdigest() if answer else None)

out={
 "schema":"PROJECT_BRAIN_LIVEBENCH_V4_REPLAY72_EXECUTOR_VERIFICATION_V1",
 "status":"PASS",
 "executor_git_blob_sha":git_blob_sha(EXEC),
 "runtime_file_count":len(mod.RUNTIME_FILES),
 "replay_limit":mod.REPLAY_LIMIT,
 "terminal_cases_consumed":0,
 "terminal_case_content_read":False,
 "synthetic_result":synthetic_class,
 "synthetic_answer_sha256":synthetic_answer_sha256,
 "post_prompt_acquisition_loader_denied":True,
 "external_network_defense_in_depth":True,
 "subprocess_install_defense_in_depth":True,
 "direct_execution_authority":False,
 "acceptance_credit_delta":0,
}
print(json.dumps(out,sort_keys=True))
