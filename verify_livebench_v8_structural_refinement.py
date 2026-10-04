#!/usr/bin/env python3
from __future__ import annotations
import ast,hashlib,importlib.util,json,pathlib,re,sys

ROOT=pathlib.Path(__file__).resolve().parent
CLASSIFIER=ROOT/"livebench_v8_structural_classifier.py"
DIAGNOSTIC=ROOT/"diagnose_livebench_replay72_v8_structural.py"
BASE=ROOT/"execute_livebench_if_replay72_v4_candidate.py"
EXPECTED_BASE_BLOB="2a57ce896ddbd6819246aab8b44d17a00f36b61e"

def git_blob_sha(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("IMPORT_SPEC")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def require(cond,msg):
    if not cond: raise AssertionError(msg)

require(git_blob_sha(BASE)==EXPECTED_BASE_BLOB,"BASE_EXECUTOR_BLOB")
ct=CLASSIFIER.read_text(encoding="utf-8")
dt=DIAGNOSTIC.read_text(encoding="utf-8")
ast.parse(ct);ast.parse(dt)
require("REPLAY_LIMIT=72" in dt,"REPLAY_LIMIT")
require('"new_case_exposure":False' in dt,"NEW_CASE_FALSE")
require('"case_ids_emitted":False' in dt,"CASE_IDS_FALSE")
require('"prompt_text_emitted":False' in dt,"PROMPT_FALSE")
require('"response_text_emitted":False' in dt,"RESPONSE_FALSE")
require('"raw_exception_text_emitted":False' in dt,"RAW_EXCEPTION_FALSE")
require('"raw_composition_detail_emitted":False' in dt,"RAW_COMPOSITION_FALSE")
i_install=dt.index("mod.install_scorer_deps()")
i_nltk=dt.index("mod.prepare_nltk(base)")
i_download=dt.index("parquet=mod.download_dataset(base)")
require(i_install<i_nltk<i_download,"PRECASE_ENVIRONMENT_ORDER")
for forbidden in ("print(cp.stderr","print(exc)","traceback.print_exc","case_ids.append","question_id"):
    if forbidden=="question_id":
        continue
    require(forbidden not in dt,"FORBIDDEN_OUTPUT_SURFACE:"+forbidden)

m=load(CLASSIFIER,"v8_classifier")
class Root2InferenceBlocked(RuntimeError): pass
source_codes=frozenset({
 "BOUND_CAPABILITY_GROUNDING_AVAILABLE_COMPOSITION_BLOCKED",
 "GOAL_ARCHITECTURAL_GAP",
 "NO_BINDABLE_CANDIDATE_FOR_CLAUSE",
 "PROPOSAL_EFFECT_RESULT_MISSING",
 "UNVERIFIED_INITIAL_FACTS_REQUIRED",
})

secret="SECRET_CASE_DETAIL_DO_NOT_EMIT"
cases=[
 (
  Root2InferenceBlocked("Blocker:BOUND_CAPABILITY_GROUNDING_AVAILABLE_COMPOSITION_BLOCKED:"+json.dumps({
    "composition_error":"GROUNDED_EXECUTABLE_COMPOSITION_FAILED:CompositionError:NO_BINDABLE_CANDIDATE_FOR_CLAUSE:7:"+secret,
    "candidate_capability_ids":[secret],
  })),
  {"kind":"COMPOSITION_PRODUCER","code":"NO_BINDABLE_CANDIDATE_FOR_CLAUSE"}
 ),
 (
  Root2InferenceBlocked("Blocker:BOUND_CAPABILITY_GROUNDING_AVAILABLE_COMPOSITION_BLOCKED:"+json.dumps({
    "composition_error":"GROUNDED_EXECUTABLE_COMPOSITION_VERIFY_FAILED:PROPOSAL_EFFECT_RESULT_MISSING:"+secret
  })),
  {"kind":"COMPOSITION_VERIFIER","code":"PROPOSAL_EFFECT_RESULT_MISSING"}
 ),
 (
  Root2InferenceBlocked("Blocker:GOAL_ARCHITECTURAL_GAP:"+json.dumps({
    "gap_class":"CONTROL_FLOW","subgoal":secret,"compile_error":secret
  })),
  {"kind":"ARCHITECTURAL_GAP","code":"CONTROL_FLOW"}
 ),
 (
  Root2InferenceBlocked("LIVEBENCH_POLICY_POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN"),
  {"kind":"POLICY_BLOCK","code":"POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN"}
 ),
 (
  RuntimeError("LIVEBENCH_POLICY_EXTERNAL_NETWORK_FORBIDDEN:"+secret),
  {"kind":"POLICY_BLOCK","code":"EXTERNAL_NETWORK_FORBIDDEN"}
 ),
 (
  RuntimeError("LIVEBENCH_POLICY_POST_PROMPT_ACQUISITION_FORBIDDEN:"+secret),
  {"kind":"POLICY_BLOCK","code":"POST_PROMPT_PACKAGE_ACQUISITION_FORBIDDEN"}
 ),
]
for exc,expected in cases:
    out=m.classify_exception(exc,source_codes)
    require(out==expected,"CLASSIFICATION:"+repr((out,expected)))
    rendered=json.dumps(out,sort_keys=True)
    require(secret not in rendered,"SECRET_LEAK")
    require(len(rendered)<240,"OUTPUT_NOT_BOUNDED")

print(json.dumps({
 "schema":"PROJECT_BRAIN_LIVEBENCH_V8_STRUCTURAL_REFINEMENT_VERIFIER_V1",
 "status":"PASS",
 "synthetic_adversarial_cases":len(cases),
 "secret_detail_leaks":0,
 "replay_prefix_limit":72,
 "new_case_exposure":False,
 "terminal_cases_consumed":0,
 "acceptance_credit_delta":0
},sort_keys=True))
