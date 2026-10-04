#!/usr/bin/env python3
import json, pathlib, subprocess

ROOT=pathlib.Path(__file__).resolve().parent
R=ROOT/"subject/livebench_runtime_closure_v17/RECEIPT.json"
F=ROOT/"subject/livebench_runtime_closure_v17/FRONTIER.json"
EXPECTED={
 str(R.relative_to(ROOT)):"44111f7f56b4f9300a83d5060f52f857724d858a",
 str(F.relative_to(ROOT)):"247d3b663fd5bfbe98c0c1a7cbb3ea64654cf8b3",
}
def blob(p):
    return subprocess.check_output(["git","rev-parse","HEAD:"+str(p.relative_to(ROOT))],text=True).strip()
for p,e in [(R,EXPECTED[str(R.relative_to(ROOT))]),(F,EXPECTED[str(F.relative_to(ROOT))])]:
    g=blob(p)
    assert g==e,(p,g,e)

r=json.loads(R.read_text())
f=json.loads(F.read_text())
assert r["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert r["observed"]["status"]=="PASS__EXACT_BLOBS_SYNTHETIC_FULL_ADAPTER_PATH__PUBLIC_GITHUB_RUNNER"
assert r["observed"]["model_dependency_count"]==0
assert r["observed"]["terminal_cases_consumed"]==0
assert r["observed"]["fresh_reality_consumed"] is False
assert r["observed"]["incremental_spend_usd"]==0
assert r["exact_runtime_closure"]["goal_compiler"]["git_blob_sha"]=="4b61fe911471854ec15c7900816f61e9e55f602e"
assert r["exact_runtime_closure"]["capability_planner"]["git_blob_sha"]=="64ff65cb184f50d3336326f33cccfcc0a53301a8"
assert r["exact_runtime_closure"]["capability_proposal_generators"]["git_blob_sha"]=="71f2bbfda66a65d8d75e035b9ae073671ebd56e2"
assert all(v==0 for v in r["accounting"].values())

assert f["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V17"
assert "ZERO_CREDIT" in f["status"] and "NO_FRESH_REALITY" in f["status"]
assert f["supersedes_for_scheduling_if_verified"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V16.json"
d=[x for x in f.get("projection_deltas",[]) if x.get("deletion")=="LIVEBENCH_EXACT_TRANSITIVE_FROZEN_RUNTIME_DEPENDENCY_CLOSURE"]
assert len(d)==1
run=[str(x) for x in f.get("runnable_zero_reality",[])]
assert not any(x.startswith("LIVEBENCH_IF_MATERIALIZE_OR_FORMALLY_PROVE_EXACT_TRANSITIVE_FROZEN_RUNTIME_DEPENDENCY_CLOSURE") for x in run)
assert any("WRITE_ONLY_OR_CRYPTOGRAPHIC_ESCROW" in x for x in run)
a=f.get("accounting",{})
for k in ("incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
    assert a.get(k)==0,(k,a.get(k))
print("PASS: exact LiveBench runtime closure receipt and Root2 V17 scheduling deletion verified; zero credit preserved")
