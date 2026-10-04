from __future__ import annotations

import ast
import hashlib
import importlib.util
import pathlib

ROOT=pathlib.Path(__file__).resolve().parent
CLASSIFIER=ROOT/"livebench_v8_refined_classifier.py"
DIAG=ROOT/"diagnose_livebench_replay72_v8_refined.py"
V7=ROOT/"diagnose_livebench_replay72_v7_sanitized.py"
EXPECTED_V7="55d4b961f58dc45c1513f9c9282a63773444773d"

def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert blob(V7)==EXPECTED_V7,(blob(V7),EXPECTED_V7)
ast.parse(CLASSIFIER.read_text())
ast.parse(DIAG.read_text())

spec=importlib.util.spec_from_file_location("v8c",CLASSIFIER)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

Root2InferenceBlocked=type("Root2InferenceBlocked",(RuntimeError,),{})
source={
 "BOUND_CAPABILITY_GROUNDING_AVAILABLE_COMPOSITION_BLOCKED",
 "GROUNDED_EXECUTABLE_COMPOSITION_VERIFY_FAILED",
 "GOAL_ARCHITECTURAL_GAP",
 "CAUSAL_COMPOSITION",
 "SOME_STATIC_BLOCKER",
 *m.POLICY_MARKERS,
}

for marker in m.POLICY_MARKERS:
    got=m.classify_exception(Root2InferenceBlocked(marker),source)
    assert got=={"kind":"POLICY_BLOCK","code":marker},got

comp='Blocker:BOUND_CAPABILITY_GROUNDING_AVAILABLE_COMPOSITION_BLOCKED:{"composition_error":"GROUNDED_EXECUTABLE_COMPOSITION_VERIFY_FAILED:UNSAFE_DETAIL","gap":"REDACTED"}'
got=m.classify_exception(Root2InferenceBlocked(comp),source)
assert got=={"kind":"COMPOSITION_SUBBLOCKER","code":"GROUNDED_EXECUTABLE_COMPOSITION_VERIFY_FAILED"},got

arch='Blocker:GOAL_ARCHITECTURAL_GAP:{"gap_class":"CAUSAL_COMPOSITION","subgoal":"DO_NOT_EMIT"}'
got=m.classify_exception(Root2InferenceBlocked(arch),source)
assert got=={"kind":"ARCHITECTURAL_GAP","code":"CAUSAL_COMPOSITION"},got

static='Blocker:SOME_STATIC_BLOCKER:PRIVATE_DETAIL'
got=m.classify_exception(Root2InferenceBlocked(static),source)
assert got=={"kind":"STATIC_BLOCKER","code":"SOME_STATIC_BLOCKER"},got

d=DIAG.read_text()
for required in [
  "REPLAY_LIMIT = 72",
  '"task_id":"REDACTED"',
  '"new_case_exposure":False',
  '"case_ids_emitted":False',
  '"prompt_text_emitted":False',
  '"response_text_emitted":False',
  '"raw_exception_text_emitted":False',
  "mod.install_scorer_deps()",
  "mod.prepare_nltk(base)",
]:
    assert required in d,required
assert "questions[start:start+batch]" in d
assert "range(0,REPLAY_LIMIT,batch)" in d
assert "case_73" not in d.lower()
assert "authorized=False" in d
assert "VERIFIED_V8_ACTIVATION_BLOB_REQUIRED" in d

print("PASS__LIVEBENCH_V8_REFINED_CAUSAL_DIAGNOSTIC__ZERO_NEW_CASES")
