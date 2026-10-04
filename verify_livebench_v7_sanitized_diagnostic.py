#!/usr/bin/env python3
from __future__ import annotations
import hashlib,importlib.util,pathlib,tempfile
ROOT=pathlib.Path(__file__).resolve().parent
BASE=ROOT/"execute_livebench_if_replay72_v4_candidate.py"
DIAG=ROOT/"diagnose_livebench_replay72_v7_sanitized.py"
CLS=ROOT/"livebench_v7_sanitized_classifier.py"
EXPECTED_BASE="2a57ce896ddbd6819246aab8b44d17a00f36b61e"
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
assert blob(BASE)==EXPECTED_BASE
src=DIAG.read_text()
for lit in [
 "REPLAY_LIMIT=72",
 'case_ids_emitted":False',
 'prompt_text_emitted":False',
 'response_text_emitted":False',
 'raw_exception_text_emitted":False',
 "for start in range(0,REPLAY_LIMIT,batch):",
]:
 assert lit in src,lit
for forbidden in [
 "for start in range(0,mod.POPULATION",
 "print(q[",
 "print(answer",
 "print(str(exc)",
]:
 assert forbidden not in src,forbidden
spec=importlib.util.spec_from_file_location("diag",DIAG);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
base=mod.load_base()
assert base.REPLAY_LIMIT==72 and len(base.RUNTIME_FILES)==24
with tempfile.TemporaryDirectory(prefix="lb-v7-zero-") as td:
 template=mod.build_diagnostic_template(pathlib.Path(td),base)
 # Classifier itself is independent of benchmark content.
 cspec=importlib.util.spec_from_file_location("cls",CLS);cm=importlib.util.module_from_spec(cspec);cspec.loader.exec_module(cm)
 codes=cm.source_code_vocabulary([template/"canonical/runtime/astra_runtime.py",template/"canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py"])
 assert "GOAL_ARCHITECTURAL_GAP" in codes
 assert "CAPABILITY_ACQUISITION_REQUIRED" in codes
 class FakeRoot2InferenceBlocked(RuntimeError): pass
 FakeRoot2InferenceBlocked.__name__="Root2InferenceBlocked"
 a=cm.classify_exception(FakeRoot2InferenceBlocked('Blocker:GOAL_ARCHITECTURAL_GAP:{"subgoal":"SECRET_PROMPT_TEXT"}'),codes)
 assert a=={"kind":"STATIC_BLOCKER","code":"GOAL_ARCHITECTURAL_GAP"}
 assert "SECRET_PROMPT_TEXT" not in str(a)
 b=cm.classify_exception(FakeRoot2InferenceBlocked("LiveBenchPostPromptAcquisitionForbidden:LIVEBENCH_POLICY_POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN"),codes)
 assert b["kind"]=="POLICY_BLOCK"
 synth={"question_id":"SYNTHETIC_ZERO_CASE","turns":["Reply with exactly SYNTHETIC_OK."]}
 result=mod.classify_one(template,synth,base.BENCHMARK_ID)
 assert result=="VALID_RESPONSE" or result.startswith(("STATIC_BLOCKER:","STATIC_ADAPTER_BLOCKER:","POLICY_BLOCK:")),result
print('{"status":"INDEPENDENT_PUBLIC_RUNNER_PASS","diagnostic_git_blob_sha":"'+blob(DIAG)+'","classifier_git_blob_sha":"'+blob(CLS)+'","base_executor_git_blob_sha":"'+EXPECTED_BASE+'","replay_case_count":72,"sanitized_static_code_only":true,"no_case_ids_prompts_responses_or_raw_exceptions_emitted":true,"terminal_cases_consumed":0,"acceptance_credit_delta":0}')
