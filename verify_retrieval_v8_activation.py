#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
F={
 "a":("canonical/governance/GLOBAL_RETRIEVAL_V8_EMPIRICAL_EXTENSION_ACTIVATION_V1.json","5597833707ac5e2a28a2ba3ede9b83f5ce175ae5"),
 "h":("canonical/verification/RETRIEVAL_V8_REAL_HIDDEN_WITNESS_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","3d37f0cff61d5603bdec0358762e854be3adde3a"),
 "e":("canonical/verification/RETRIEVAL_V8_EMPIRICAL_CONTROLLER_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","5e9a16be3cf51a42f530377524c6cb08c81d4347"),
}
def blob(p):
 x=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 p,s=F[k]; q=R/p; assert blob(q)==s,(k,blob(q),s); return json.loads(q.read_text())
a=load("a");h=load("h");e=load("e")
assert h["independent_runner"]["conclusion"]=="success"
assert e["independent_runner"]["conclusion"]=="success"
assert h["measured"]["monotonic_pooled_top5_recall"]==1.0
assert h["measured"]["monotonic_pooled_top5_misses"]==0
assert a["real_hidden_witness_regression"]["verification_git_blob_sha"]==F["h"][1]
assert a["empirical_live_routing"]["verification_git_blob_sha"]==F["e"][1]
assert a["empirical_live_routing"]["fixed_correlation_multiplier_used"] is False
assert a["empirical_live_routing"]["fixed_source_independence_multiplier_used"] is False
assert a["empirical_live_routing"]["finite_arena_used_as_live_provider_oracle"] is False
assert a["empirical_live_routing"]["live_calibration_maturity"].startswith("EARLY")
rules=set(a["mandatory_policy"])
assert "AUTHORIZED_GLOBAL_RETRIEVAL_PLAN_COMPILATION_MUST_USE_GLOBAL_RETRIEVAL_ENTRYPOINT_V2" in rules
assert "FINITE_REAL_HIDDEN_WITNESS_ARENA_IS_REGRESSION_EVIDENCE_NOT_A_LIVE_PROVIDER_ORACLE" in rules
assert "OPEN_WORLD_MISS_REMAINS_UNKNOWN" in rules
assert a["current_global_retrieval_authority"] if "current_global_retrieval_authority" in a else True
assert a["incremental_spend_usd"]==0
assert a["execution_authority"] is False and a["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V8_EMPIRICAL_EXTENSION_ACTIVATION_VERIFIED")
