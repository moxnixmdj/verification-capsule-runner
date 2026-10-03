from __future__ import annotations
import hashlib, json, urllib.request

BRAIN="moxnixmdj/brain"
BRAIN_HEAD="7208792002f1096e31b2635f5330f5310e0c0668"
AUTH_PATH="canonical/governance/P1_ONE_USE_FAILURE_SEMANTICS_EXECUTION_AUTHORITY_V1.json"
WF_PATH=".github/workflows/execute-p1-shared-failure-semantics-once.yml"
AUTH_BLOB="ec8bc10097aac030966bf0a7d03f5bb5ff06c2da"
WF_BLOB="8e0c1b3adc1da56da8ed83bfc4459d5fea30caa6"
UA={"User-Agent":"ProjectBrain-P1-Activation-Verifier/1.0","Accept":"application/vnd.github+json"}

def get_bytes(url:str)->bytes:
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=30) as r:
        assert int(getattr(r,"status",200))==200,(url,getattr(r,"status",None))
        return r.read()

def get_json(url:str):
    return json.loads(get_bytes(url).decode("utf-8","replace"))

def git_blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

auth_raw=get_bytes(f"https://raw.githubusercontent.com/{BRAIN}/{BRAIN_HEAD}/{AUTH_PATH}")
wf_raw=get_bytes(f"https://raw.githubusercontent.com/{BRAIN}/{BRAIN_HEAD}/{WF_PATH}")
assert git_blob_sha(auth_raw)==AUTH_BLOB,(git_blob_sha(auth_raw),AUTH_BLOB)
assert git_blob_sha(wf_raw)==WF_BLOB,(git_blob_sha(wf_raw),WF_BLOB)

a=json.loads(auth_raw)
w=wf_raw.decode("utf-8","strict")

assert a["schema"]=="PROJECT_BRAIN_P1_ONE_USE_FAILURE_SEMANTICS_EXECUTION_AUTHORITY_V1"
assert a["authorized_observation"]=="P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH"
assert a["fresh_reality_units_authorized"]==1
assert a["execution_authority"] is True
assert a["promotion_authority"] is False
assert a["first_attempt_only"] is True
assert a["rerun_credit"] is False
assert a["terminal_v3_replay"] is False
assert a["incremental_spend_usd"]==0
assert a["selection"]["cases_per_surface"]==64
assert a["selection"]["surface_count"]==3
assert a["selection"]["total_cases"]==192
assert len(a["selection"]["frozen_surfaces"])==3
assert a["selection"]["post_freeze_uncontrollable_selection"] is True
assert a["execution_contract"]["workflow_path_only_trigger"] is True
assert a["execution_contract"]["first_attempt_only"] is True
assert a["execution_contract"]["no_manual_rerun_credit"] is True
assert a["execution_contract"]["no_retry_credit"] is True
assert a["execution_contract"]["no_case_replacement"] is True
assert a["execution_contract"]["no_post_result_tuning"] is True
assert a["execution_contract"]["terminal_v3_replay"] is False
assert a["execution_contract"]["runtime_self_promotion_forbidden"] is True
assert a["execution_contract"]["independent_post_execution_adjudication_required"] is True
assert a["exact_inputs"]["execution_workflow_blob"]==WF_BLOB

basis=a["authority_basis"]["independent_preexecution_verification"]
assert basis["repository"]=="moxnixmdj/verification-capsule-runner"
assert basis["pull_request"]==1166
assert basis["isolated_workflow_run_id"]==37104366556
assert basis["dispatcher_workflow_run_id"]==37104366512
assert basis["merge_commit"]=="7dd7391ecded6bcea3b45639f71679c1ea54359e"
assert basis["conclusion"]=="success"

pr=get_json("https://api.github.com/repos/moxnixmdj/verification-capsule-runner/pulls/1166")
assert pr["merged_at"] is not None
assert pr["merge_commit_sha"]=="7dd7391ecded6bcea3b45639f71679c1ea54359e"
for rid in (37104366556,37104366512):
    run=get_json(f"https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/{rid}")
    assert run["status"]=="completed",(rid,run["status"])
    assert run["conclusion"]=="success",(rid,run["conclusion"])

required_text=[
    'branches: [main]',
    '".github/workflows/execute-p1-shared-failure-semantics-once.yml"',
    'group: p1-shared-failure-semantics-one-use-v1',
    'cancel-in-progress: false',
    'test "$GITHUB_RUN_ATTEMPT" = "1"',
    'test "$GITHUB_REF" = "refs/heads/main"',
    'fresh_reality_units_authorized"]==1',
    'rerun_credit"] is False',
    'terminal_v3_replay"] is False',
    'P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH',
    'P1_AUTHORIZED_BATCH_RESULT.json',
    'execution_authority_consumed":True',
    '"rerun_credit":False',
    '"promotion_authority":False',
]
missing=[s for s in required_text if s not in w]
assert not missing,("WORKFLOW_REQUIRED_GUARDS_MISSING",missing)
for forbidden in ("workflow_dispatch:","schedule:","pull_request:"):
    assert forbidden not in w,("FORBIDDEN_TRIGGER",forbidden)

for k,v in a["exact_inputs"].items():
    if k.endswith("_blob") and k!="execution_workflow_blob":
        assert v in w,("DEPENDENCY_BLOB_NOT_PINNED_IN_WORKFLOW",k,v)

out={
  "schema":"PROJECT_BRAIN_P1_ONE_USE_ACTIVATION_INDEPENDENT_VERIFICATION_20261003_V1",
  "status":"PASS__EXACT_AUTHORITY_AND_WORKFLOW_BYTES__ONE_USE_GUARDS__PREFLIGHT_RECEIPTS__ZERO_REALITY",
  "brain_head":BRAIN_HEAD,
  "authority_blob":AUTH_BLOB,
  "workflow_blob":WF_BLOB,
  "preexecution_verifier_pr":1166,
  "preexecution_isolated_run":37104366556,
  "preexecution_dispatcher_run":37104366512,
  "authorized_reality_units":1,
  "cases":192,
  "surface_count":3,
  "first_attempt_only":True,
  "rerun_credit":False,
  "terminal_v3_replay":False,
  "terminal_cases_executed":0,
  "fresh_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "execution_authority":False,
  "promotion_authority":False,
  "capability_credit_delta":0,
  "family_credit_delta":0,
  "consequence":"BRAIN_PR_1239_EXACT_HEAD_IS_ELIGIBLE_FOR_MERGE__THE_FIRST_MAIN_PUSH_THAT_INTRODUCES_THE_EXACT_WORKFLOW_CONSUMES_THE_SINGLE_AUTHORIZED_REALITY_UNIT"
}
print(json.dumps(out,sort_keys=True))
