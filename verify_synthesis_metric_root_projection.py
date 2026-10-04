#!/usr/bin/env python3
import json, pathlib, subprocess

BASE=pathlib.Path("subject/synthesis_metric_root_projection_20261004_sol")
FILES={
    "root":BASE/"ROOT_STATE.json",
    "activation":BASE/"ACTIVATION.json",
    "receipt":BASE/"RECEIPT.json",
    "contract":BASE/"CONTRACT.json",
    "root2":BASE/"ROOT2_V11.json",
    "adaptive":BASE/"ADAPTIVE_V3_FINAL.json",
}
EXPECTED={
    "root":"60b70daf25f47d12d7a9522990769c0200acbfa9",
    "activation":"1ca2de029b02ca8518e59e0d66a973e3e26e251b",
    "receipt":"8a5be1224383dccfbd917729df285eeb96004825",
    "contract":"0886f7592875a5b750cdd401aa783351ab2f0854",
    "root2":"6857750dea3a0af48a5acc545b6f66b619d4335b",
    "adaptive":"cf6d3c92134ee7cb2e75ae7f82e144aa71a8ecba",
}
def blob(p):
    return subprocess.check_output(["git","hash-object",str(p)],text=True).strip()
for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k],(k,got,EXPECTED[k])

o={k:json.loads(p.read_text()) for k,p in FILES.items()}
root=o["root"]; act=o["activation"]; receipt=o["receipt"]; contract=o["contract"]
root2=o["root2"]; adaptive=o["adaptive"]

# Terminal truth must be unchanged.
assert root["current_acceptance"]=={
  "accepted_families":5,"open_families":14,"proved_atomic":12,
  "unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False
}
res=root["current_residual_root_partition"]
assert (res["unresolved_total"],res["root1_positive_gap_count"],res["root2_only_count"],
        res["root3_only_count"],res["root2_and_root3_count"])==(26,0,16,7,3)

# Root2 V11 remains the active domain scheduler.
r2=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r2["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V11.json"
assert r2["current_frontier_git_blob_sha"]==EXPECTED["root2"]
assert r2["effective_scheduling_authority"] is True
assert r2["fresh_reality_authority"] is False
assert root2["exact_state"]["accepted_families"]==5
assert root2["exact_state"]["proved_atomic"]==12
assert root2["exact_state"]["unresolved_atomic"]==26

# Adaptive V3 remains active and higher-level only.
meta=root["scheduler_policy"]["adaptive_meta_scheduler"]
assert meta["final_activation_git_blob_sha"]==EXPECTED["adaptive"]
assert meta["status"].startswith("ACTIVE__INDEPENDENT_CURRENT_MAIN_PROJECTION_PASS__ROOT2_V11")
assert meta["execution_authority"] is False
assert meta["promotion_authority"] is False
assert meta["fresh_reality_authority"] is False
assert adaptive["authority"]["execution"] is False
assert adaptive["authority"]["promotion"] is False
assert adaptive["authority"]["fresh_reality"] is False

# Root3 remains event-driven and zero-runnable.
r3=root["root3_current_execution_state"]
assert r3["live_root3_predicates"]==10
assert r3["event_class_count"]==3
assert r3["currently_runnable_event_count"]==0
assert r3["fresh_reality_authority"] is False

# New synthesis metric projection is exact.
sp=root["scheduler_policy"]["synthesis_matched_quality_metric"]
assert sp["activation_git_blob_sha"]==EXPECTED["activation"]
assert sp["verification_git_blob_sha"]==EXPECTED["receipt"]
assert sp["target_predicate"]=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
assert sp["deleted_residual"]=="SYNTHESIS_MATCHED_QUALITY_CASE_LEVEL_AGGREGATION_UNDERSPECIFIED"
assert sp["remaining"]==[
    "FIVE_CASE_SPECIFIC_QUALITY_DIMENSION_SCORER_BINDINGS",
    "PORTFOLIO_LEVEL_CONSERVATIVE_MATCHED_NONINFERIORITY_REDUCER",
    "EXACT_OPUS_5_5_COMPARATOR_ADMISSIBILITY_OR_STRONGER_PROOF",
    "MATCHED_QUALITY_RESULT",
]
assert sp["execution_authority"] is False
assert sp["promotion_authority"] is False
assert sp["fresh_reality_authority"] is False

# Activation chains to exact contract and independent receipt.
assert act["subject"]["git_blob_sha"]==EXPECTED["contract"]
assert act["verification"]["git_blob_sha"]==EXPECTED["receipt"]
assert act["verification"]["conclusion"]=="success"
assert act["effects"]["delete"]==["SYNTHESIS_MATCHED_QUALITY_CASE_LEVEL_AGGREGATION_UNDERSPECIFIED"]
assert act["authority"]=={
  "scheduling":True,"execution":False,"promotion":False,"fresh_reality":False
}
assert all(v==0 for v in act["accounting"].values())

# Independent receipt really passed exact scorer/contract semantics.
assert receipt["independent_runner"]["pull_request"]==1678
assert receipt["independent_runner"]["merge_commit"]=="cfe8e9102d5615e6d7aa5b69b2ae435d3f640a38"
assert receipt["independent_runner"]["workflow_run_id"]==37176553743
assert receipt["independent_runner"]["workflow_job_id"]==111360244300
assert receipt["independent_runner"]["conclusion"]=="success"
assert all(v==0 for v in receipt["accounting"].values())

# Contract itself preserves remaining work and no authority.
assert contract["statistical_noninferiority"]["state"]=="OPEN"
assert contract["execution_authority"] is False
assert contract["promotion_authority"] is False
assert contract["fresh_reality_authority"] is False
assert all(v==0 for v in contract["accounting"].values())

# Root accounting unchanged.
assert root["accounting"]=={
 "acceptance_credit_delta":0,"family_credit_delta":0,
 "capability_credit_delta":0,"ownership_credit_delta":0,
 "new_reality_units_consumed":0,"incremental_spend_usd":0
}

print("PASS: synthesis matched-quality metric root projection is exact")
print("PASS: aggregation underspecification deleted; four true residuals preserved")
print("PASS: Root2 V11, Adaptive V3 and Root3 zero-runnable gate preserved")
print("PASS: 5/19 families, 12/38 predicates, 26 unresolved unchanged")
print("PASS: zero spend, zero cases, zero credit, no execution or fresh reality")
