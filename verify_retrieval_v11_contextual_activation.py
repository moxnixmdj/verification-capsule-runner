#!/usr/bin/env python3
import hashlib,json,pathlib,importlib.util
R=pathlib.Path(__file__).resolve().parent
F={
 "a":("subjects/v11/activation.json","b9c31ec7f02b7d8ba623d5d8d8cdafa1008a03c1"),
 "p":("subjects/v11/base_pointer.json","cb58ff10b7c3ac99da8cbee7b8aa0b76006f8dfe"),
 "core":("subjects/v11/core_receipt.json","77fc818f6b6ea9bb35dffd449d529fb9a507b8ce"),
 "live":("subjects/v11/live_receipt.json","2c47dc835efd0142248b08cefc8438370fcbf1f3"),
 "state":("subjects/v11/state_receipt.json","6025779caa5fc839c7bbc9e13c7f009c09e20721"),
 "ledger":("subjects/v11/ledger_v3.py","5008c5d804a511014a803522b713259b6bb16f7d"),
 "controller":("subjects/v11/controller_v3.py","266122c4e893fbcb34784bc01eb859b390dc2cf4"),
 "entry":("subjects/v11/entrypoint_v4.py","b1fd8b92f1aa931b283f242bde7612a3d29b5501"),
 "events":("subjects/v11/live_events_v3.jsonl","1d9c1bdf6b7722c07a081eefa00f40b6ee968fc5"),
}
def blob(p):
 x=p.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 p,s=F[k];q=R/p;assert blob(q)==s,(k,blob(q),s);return json.loads(q.read_text())
a=load("a");p=load("p");core=load("core");live=load("live");state=load("state")
assert p["status"].endswith("GENERATED_STRESS_V9_BOUND__ZERO_CREDIT")
assert "v8_empirical_extension" in p and "v9_generated_stress_extension" in p
assert a["schema"]=="PROJECT_BRAIN_GLOBAL_RETRIEVAL_V11_CONTEXTUAL_LIVE_CALIBRATION_ACTIVATION_V1"
assert a["base_current_authority"]["git_blob_sha"]==F["p"][1]
assert a["v10_runtime"]["live_event_ledger_v3"]["git_blob_sha"]==F["ledger"][1]
assert a["v10_runtime"]["contextual_controller_v3"]["git_blob_sha"]==F["controller"][1]
assert a["v10_runtime"]["authorized_entrypoint_v4"]["git_blob_sha"]==F["entry"][1]
assert a["v10_runtime"]["live_event_state_v3"]["git_blob_sha"]==F["events"][1]
assert a["independent_verification"]["entity_context_core"]["git_blob_sha"]==F["core"][1]
assert a["independent_verification"]["live_provider_epoch"]["git_blob_sha"]==F["live"][1]
assert a["independent_verification"]["exact_brain_live_state"]["git_blob_sha"]==F["state"][1]
assert core["independent_runner"]["conclusion"]=="success"
assert live["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert state["independent_runner"]["conclusion"]=="success"
m=a["measured_live_state"]
assert m["event_count"]==31 and m["episode_count"]==13 and m["task_class_count"]==7
assert m["new_live_event_count"]==30 and m["new_live_successful_event_count"]==28
assert m["new_live_retryable_failure_count"]==2 and m["verified_sufficient_event_count"]==7
assert m["statistical_maturity_claim"] is False
r=a["measured_contextual_routing"]
assert r["CODE_REPOSITORY"]=="GITHUB_FIRST"
assert r["MODEL_HUB"]=="HUGGINGFACE_FIRST"
assert r["SCHOLARLY_WORK"].startswith("CROSSREF_FIRST")
e=a["entity_resolution_policy"]
assert e["heuristic_cross_source_merging"] is False
assert e["title_only_scholarly_sufficiency"] is False
pol=set(a["mandatory_policy"])
for rule in (
 "AUTHORIZED_GLOBAL_RETRIEVAL_PLAN_COMPILATION_MUST_USE_GLOBAL_RETRIEVAL_ENTRYPOINT_V4",
 "LIVE_ROUTING_MUST_USE_ENTITY_RESOLVED_TASK_CLASS_CONDITIONED_EVENT_STATE_V3",
 "TASK_CLASS_MEASURED_SOURCE_STATS_OVERRIDE_GLOBAL_SOURCE_AVERAGES",
 "GLOBAL_SOURCE_STATS_ARE_ONLY_FALLBACK_FOR_UNMEASURED_TASK_CLASS_SOURCE_PAIRS",
 "FIXED_SOURCE_CORRELATION_OR_INDEPENDENCE_MULTIPLIERS_REMAIN_FORBIDDEN",
 "FINITE_V8_AND_V9_ARENAS_REMAIN_REGRESSION_EVIDENCE_NOT_LIVE_PROVIDER_ORACLES",
 "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
): assert rule in pol,rule
assert a["incremental_spend_usd"]==0
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):assert a[k]==0
assert a["execution_authority"] is False and a["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V11_CONTEXTUAL_LIVE_CALIBRATION_ACTIVATION_VERIFIED")
