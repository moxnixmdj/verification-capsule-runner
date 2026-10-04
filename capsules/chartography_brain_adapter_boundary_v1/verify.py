#!/usr/bin/env python3
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

C=ROOT/"candidate.json"
R=ROOT/"registry.json"
T=ROOT/"task.py.txt"
S=ROOT/"scorer.py.txt"
expected={
 "candidate":"af2ba067223c0af48ea349c6569ac333846e5510",
 "registry":"7badee4878700f2cd4176beb8319d2a6a0bdf782",
 "task":"163d910274f06720b601006ef1b6266e7cfd30b6",
 "scorer":"11cffaa92dff3bed126247990d41f1509574040e",
}
actual={"candidate":blob(C),"registry":blob(R),"task":blob(T),"scorer":blob(S)}
assert actual==expected,(actual,expected)

c=json.loads(C.read_text())
r=json.loads(R.read_text())
t=T.read_text()
s=S.read_text()

assert c["target_predicate"]=="CHARTOGRAPHY_TOOLS_GE_89"
assert c["upstream_contract"]["required_model_input"]==["TEXT_QUESTION","IMAGE"]
assert c["upstream_contract"]["solver"]=="inspect_ai.solver.generate"
assert c["classification"]["root1"].startswith("NOT_REOPENED")
assert c["classification"]["root2"]=="OPEN__BRAIN_EVALUATION_ADAPTER_BINDING_MISSING"
assert c["terminal_cases_consumed"]==0 and c["acceptance_credit_delta"]==0
assert "ContentText(text=question)" in t
assert "ContentImage(image=image)" in t
assert "solver=[generate()]" in t.replace(" ","") or "solver=[generate()]" in t
assert "model_graded_qa" in s
assert "GEMINI_3_5_FLASH" in s or "gemini-3.5-flash" in s.lower()

caps=r["capabilities"]
verified=[(cid,v) for cid,v in caps.items() if v.get("status")=="VERIFIED_BOUND_CAPABILITY"]
declared=[]
for cid,v in verified:
    provides=[str(x) for x in (v.get("provides") or [])]
    templ=json.dumps(v.get("action_template") or {},sort_keys=True)
    exact=(
      any(re.search(r"multimodal|visual.*question|image.*question|chart.*answer|vision.*answer",x,re.I) for x in provides)
      or (re.search(r"question",templ,re.I) and re.search(r"image|screenshot",templ,re.I) and re.search(r"answer|response|text",templ,re.I))
    )
    if exact: declared.append(cid)
assert len(verified)==42,len(verified)
assert declared==[],declared
assert c["current_brain_interface"]["verified_bound_capability_count"]==42
assert c["current_brain_interface"]["exact_declared_multimodal_question_image_answer_bindings"]==[]
assert c["current_brain_interface"]["exact_binding_present"] is False

print(json.dumps({
 "schema":"PROJECT_BRAIN_CHARTOGRAPHY_BRAIN_ADAPTER_INTERFACE_BOUNDARY_PUBLIC_RUNNER_RESULT_V1",
 "pass":True,
 "status":"PASS__EXACT_UPSTREAM_MULTIMODAL_CONTRACT__42_VERIFIED_BOUND_CAPABILITIES__ZERO_EXACT_DECLARED_BINDINGS__ROOT1_NOT_REOPENED__ZERO_CREDIT",
 "verified_bound_capability_count":42,
 "exact_declared_bindings":declared
},sort_keys=True))
