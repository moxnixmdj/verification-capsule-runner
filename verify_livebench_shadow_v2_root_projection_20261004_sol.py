#!/usr/bin/env python3
import hashlib, json, pathlib, sys

BASE=pathlib.Path("subject/livebench_shadow_v2_root_projection_20261004_sol")

def load(name):
    p=BASE/name
    raw=p.read_bytes()
    return json.loads(raw), hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

P,p_sha=load("PROJECTION.json")
R,r_sha=load("ROOT_STATE.json")
T,t_sha=load("THIN_ADAPTER_COMPLETION.json")
E,e_sha=load("PRECOMMIT_VERIFICATION.json")
L,l_sha=load("LEASE_V2_VERIFICATION.json")
X,x_sha=load("PREEXPOSURE_PLAN.json")
C,c_sha=load("CONTROL_PLANE_VERIFICATION.json")
B,b_sha=load("CLAIM_BACKEND.json")

errors=[]
def req(cond,msg):
    if not cond: errors.append(msg)

req(P.get("schema")=="PROJECT_BRAIN_LIVEBENCH_SHADOW_V2_ROOT_PROJECTION_V1","projection schema")
req(P.get("compiled_from_main")=="3406d9bbf29a6706d2f0e84688877414bc481afb","compiled main")
sb=P.get("source_bindings",{})
expected={
 "terminal_root_state":r_sha,
 "thin_adapter_completion":t_sha,
 "execution_precommit_verification":e_sha,
 "shadow_lease_v2_verification":l_sha,
 "shadow_preexposure_plan":x_sha,
 "shadow_control_plane_verification":c_sha,
 "one_use_claim_backend":b_sha,
}
for k,v in expected.items():
    req(sb.get(k,{}).get("git_blob_sha")==v,f"source blob mismatch:{k}")

a=R.get("current_acceptance",{})
req((a.get("accepted_families"),a.get("open_families"),a.get("proved_atomic"),a.get("unresolved_atomic"),a.get("total_families"),a.get("total_atomic"),a.get("terminal"))==(5,14,12,26,19,38,False),"root counts")
pa=P.get("exact_terminal_state_preserved",{})
req((pa.get("accepted_families"),pa.get("open_families"),pa.get("proved_atomic"),pa.get("unresolved_atomic"),pa.get("total_families"),pa.get("total_atomic"),pa.get("terminal"))==(5,14,12,26,19,38,False),"projected counts")

eff=T.get("effect",{})
req(eff.get("thin_adapter_fields_proved")==8 and eff.get("thin_adapter_fields_required")==8 and eff.get("thin_adapter_gate_complete") is True,"thin adapter 8/8")
req(T.get("authority",{}).get("fresh_reality") is False and T.get("authority",{}).get("execution") is False,"thin adapter authority")

req(E.get("independent_runner",{}).get("conclusion")=="success","precommit verifier")
req(E.get("verified",{}).get("terminal_cases_consumed")==0,"precommit zero cases")
for k in ("NO_BRAIN_SCORE","NO_GENERIC_ISOLATION_EXECUTION_RECEIPT","NO_RESOURCE_FIT_CLAIM","NO_SHADOW_COLLECTION_AUTHORITY","NO_FRESH_REALITY_AUTHORITY","NO_ACCEPTANCE_OR_PROMOTION_CREDIT"):
    req(k in E.get("hard_nonclaims",[]),f"precommit nonclaim:{k}")

req(L.get("independent_runner",{}).get("conclusion")=="success","lease v2 verifier")
req(L.get("verified",{}).get("preclaim_grants_case_reveal_authority") is False,"lease preclaim no reveal")
req(L.get("shadow_collection_authority") is False and L.get("fresh_reality_authority") is False,"lease no collection/fresh authority")

req(X.get("case_reveal_has_occurred") is False and X.get("execution_has_started") is False and X.get("evaluation_output_exists") is False,"preexposure future events false")
req(X.get("plan_sha256")=="b66dfe413089d4c91a8970e5d5502672025b9d2215cdbb4db2b4c249aed2c711","plan digest")

req(C.get("independent_runner",{}).get("conclusion")=="success","control-plane verifier")
cv=C.get("verified",{})
req(cv.get("terminal_cases_consumed")==0 and cv.get("case_reveal_authority") is False and cv.get("shadow_collection_authority") is False,"control-plane zero cases/no authority")
sem=C.get("semantic_effect",[])
req("PRESERVE_ACTUAL_LIVEBENCH_ZERO_CASE_RESOURCE_PREFLIGHT_AS_OPEN" in sem,"actual resource preflight open")
req("PRESERVE_SEPARATE_SHADOW_COLLECTION_ACTIVATION_AS_OPEN" in sem,"shadow activation open")
req("PRESERVE_ATOMIC_PRODUCTION_ONE_USE_CLAIM_AS_OPEN" in sem,"production claim open")

req(B.get("shadow_collection_authority") is False and B.get("fresh_reality_authority") is False,"backend no authority")

remaining=P.get("exact_remaining_before_case_reveal",[])
req(remaining==[
 "ACTUAL_LIVEBENCH_ZERO_CASE_POINT_OF_USE_RESOURCE_AND_DEPENDENCY_PREFLIGHT_RECEIPT",
 "SEPARATE_V2_SHADOW_COLLECTION_ACTIVATION_BOUND_TO_VERIFIED_CONTROL_PLANE_AND_ACTUAL_PREFLIGHT",
 "ATOMIC_PRODUCTION_ONE_USE_CLAIM_AFTER_PREFLIGHT_AND_BEFORE_CASE_REVEAL"
],"exact remaining cut")

auth=P.get("current_authority",{})
for k in ("case_reveal","shadow_collection","global_fresh_reality","execution","promotion","acceptance_credit"):
    req(auth.get(k) is False,f"authority inflation:{k}")
acct=P.get("accounting",{})
for k in ("incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
    req(acct.get(k)==0,f"nonzero accounting:{k}")
req(P.get("independent_verification_required") is True,"independent verification gate")

if errors:
    print("FAIL")
    for e in errors: print("-",e)
    sys.exit(1)
print("PASS: LiveBench Shadow V2 root projection is exact, zero-credit, and fail-closed.")
print(json.dumps({"projection_git_blob_sha":p_sha,"source_git_blob_shas":expected},sort_keys=True))
