import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent
B=R/"brain"
M=json.loads((R/"EXPECTED_BRAIN_BLOBS.json").read_text())
def blob(p):
 d=(B/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def load(p): return json.loads((B/p).read_text())
errors=[]
for p,h in M["exact_brain_blobs"].items():
 if blob(p)!=h: errors.append("BLOB_DRIFT:"+p)
root=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
term=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
cut=load("canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V2.json")
adm=load("canonical/governance/ROOT3_SCOPE_CERTIFICATE_ADMISSIBILITY_REFINEMENT_ACTIVATION_V2.json")
r=root.get("root3_current_execution_state") or {}
ra=root.get("root3_scope_certificate_admissibility_refinement") or {}
tcut=(term.get("sources") or {}).get("root3_minimum_action_cut") or {}
tadm=(term.get("sources") or {}).get("root3_scope_certificate_admissibility_refinement") or {}
if r.get("path")!="canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V2.json": errors.append("ROOT_CUT_PATH")
if r.get("git_blob_sha")!="4d8ce78ebe312100bbfc524062199961c0c6479d": errors.append("ROOT_CUT_SHA")
if r.get("live_root3_predicates")!=10 or r.get("matched_scope_targets")!=7 or r.get("event_class_count")!=3: errors.append("ROOT_COUNTS")
if r.get("currently_runnable_event_count")!=0 or r.get("fresh_reality_authority") is not False: errors.append("ROOT_AUTHORITY")
if ra.get("path")!="canonical/governance/ROOT3_SCOPE_CERTIFICATE_ADMISSIBILITY_REFINEMENT_ACTIVATION_V2.json": errors.append("ROOT_ADM_PATH")
if ra.get("git_blob_sha")!="a9bff5074dbb456d673131c60f30efa88a337670": errors.append("ROOT_ADM_SHA")
if tcut.get("path")!=r.get("path") or tcut.get("git_blob_sha")!=r.get("git_blob_sha"): errors.append("TERMINAL_CUT_MISMATCH")
if tadm.get("path")!=ra.get("path") or tadm.get("git_blob_sha")!=ra.get("git_blob_sha"): errors.append("TERMINAL_ADM_MISMATCH")
if cut.get("derivation",{}).get("live_root3_predicates")!=10 or len(cut.get("minimum_event_classes") or [])!=3: errors.append("CUT_CONTENT")
if cut.get("fresh_reality_authority") is not False: errors.append("CUT_FRESH_REALITY")
ce=adm.get("current_effect") or {}
if ce.get("root3_predicates")!=10 or ce.get("matched_scope_targets")!=7 or ce.get("currently_runnable_event_count")!=0: errors.append("ADM_CONTENT")
if adm.get("fresh_reality_authority") is not False: errors.append("ADM_FRESH_REALITY")
out={
 "schema":"PROJECT_BRAIN_ROOT3_ROOT_CAUSE_POINTER_PUBLIC_VERIFICATION_V2",
 "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__ROOT_CAUSE_AND_TERMINAL_AUTHORITY_ALIGNED_ON_ROOT3_V2__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
 "pass":not errors,"errors":errors,
 "verified":{"root3_predicates":10,"matched_scope_targets":7,"event_classes":3,"runnable_events":0,"fresh_reality_authority":False},
 "acceptance_credit_delta":0,"incremental_spend_usd":0
}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["pass"] else 1)
