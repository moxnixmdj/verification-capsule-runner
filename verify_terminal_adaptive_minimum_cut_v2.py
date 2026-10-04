import importlib
import json
import pathlib
import subprocess

FILES = {
    "solver":"canonical/runtime/minimum_terminal_cut_solver_v2.py",
    "solver_test":"canonical/tests/test_minimum_terminal_cut_solver_v2.py",
    "super":"canonical/runtime/terminal_adaptive_supertransaction_v2.py",
    "super_test":"canonical/tests/test_terminal_adaptive_supertransaction_v2.py",
    "candidate":"canonical/governance/TERMINAL_ADAPTIVE_MINIMUM_CUT_V2.json",
    "root":"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json",
    "r2":"canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json",
    "r2a":"canonical/governance/ROOT2_FRONTIER_V6_ACTIVATION_V1.json",
    "r2v":"canonical/verification/ROOT2_FRONTIER_V6_FINANCE_COMPRESSION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
    "r3":"canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V2.json",
    "retrieval":"canonical/governance/GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1.json",
    "tb4":"canonical/verification/TB4_ATTAINABILITY_CUT_VERDICT_20261002_V1.json",
    "fguard":"canonical/governance/FINANCE_AGENT_V2_ZERO_SPEND_RUNTIME_GUARD_V1.json",
    "fguardv":"canonical/verification/FINANCE_AGENT_V2_ZERO_SPEND_RUNTIME_GUARD_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
    "osworld":"canonical/governance/OSWORLD_OPUS55_METHODOLOGY_PUBLIC_CORROBORATION_20261004_V1.json",
}
EXPECTED = {
    "solver":"da2ae55103f9b8f8bbe10e6316d152027e31854c",
    "solver_test":"065af38ed6cb6be6680a18dcede3ca65cb5374d1",
    "super":"77a00cc6f71c3ceb0e668217299ce04a5d5b63b6",
    "super_test":"574c4be558049e8085c419274d4bb4abded871a0",
    "candidate":"5408498d5c29f7a213ff54e793939881ae681115",
    "root":"78f70dc63654b7d4be0917fce9405088177a48b5",
    "r2":"fcbdb818b63b4986b026db29c400a47373a26fdb",
    "r2a":"9a0ef849b74faa26c07d94035c8455eee8777cdd",
    "r2v":"b4cac01e5c1fe32a300607fe89854b4081376c3f",
    "r3":"4d8ce78ebe312100bbfc524062199961c0c6479d",
    "retrieval":"55b1d411561f720fcd9d66c127cecd63ef0b5f5e",
    "tb4":"a7b0c692251b92819007c581b9fe84b75960cab7",
    "fguard":"278a3317564138088fd8af83a8734a84fe09b158",
    "fguardv":"342740561634a86d0c55876ee126e8122b21af0f",
    "osworld":"259a6fa8f7daf744e6e06902d43925419cdd4d9b",
}

def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],text=True).strip()

def load(key):
    return json.loads(pathlib.Path(FILES[key]).read_text())

for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k],(k,got,EXPECTED[k])

root=load("root"); r2=load("r2"); r2a=load("r2a"); r2v=load("r2v")
r3=load("r3"); retrieval=load("retrieval"); tb4=load("tb4")
fguard=load("fguard"); fguardv=load("fguardv"); candidate=load("candidate")

assert root["current_acceptance"]=={
    "accepted_families":5,"open_families":14,"proved_atomic":12,
    "unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False
}
part=root["current_residual_root_partition"]
assert (part["root1_positive_gap_count"],part["root2_only_count"],part["root3_only_count"],
        part["root2_and_root3_count"],part["unresolved_total"])==(0,16,7,3,26)

ctrl=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert ctrl["current_frontier_path"]==FILES["r2"]
assert ctrl["current_frontier_git_blob_sha"]==EXPECTED["r2"]
assert ctrl["effective_scheduling_authority"] is True
assert ctrl["fresh_reality_authority"] is False
assert r2a["authority"]["scheduling_authority"] is True
assert r2a["authority"]["fresh_reality_authority"] is False
assert r2v["verifier"]["conclusion"]=="success"

r3s=root["root3_current_execution_state"]
assert (r3s["live_root3_predicates"],r3s["matched_scope_targets"],r3s["currently_runnable_event_count"])==(10,7,0)

assert retrieval["v19_verified_route_portfolio"]["mandatory_for_authorized_global_retrieval_plan_compilation"] is True
assert retrieval["search_engine_architecture"]["single_engine"]=="REJECTED_AS_STRUCTURALLY_INSUFFICIENT"
assert retrieval["search_engine_architecture"]["full_web_index_rebuild"]=="REJECTED_AS_DOMINATED_UNDER_ZERO_SPEND_AND_MINIMUM_WALL_CLOCK"

t=tb4["result"]
assert t["attainability_state"]=="IMPOSSIBLE" and t["upper_bound_successes"]==180 and t["required_successes"]==220
ex={x["route"]:x for x in r2["exhausted_or_deleted"]}
for x in ("TB4_CIRCLECI_FREE_XLARGE_GEN2","CURSORBENCH_OWNER_ACCESS_SEARCH","AUTOMATIONBENCH_PUBLIC600_EQUIVALENCE_SEARCH","GENERIC_ROOT3_SEARCH"):
    assert x in ex

assert fguard["current_evidence"]["scored_task_executions"]==1350
v=fguardv["verified"]
for k in ("unknown_or_paid_account_state_fails_closed","quota_payment_overage_or_cost_event_fails_closed",
          "unobserved_or_unguarded_calls_fail_closed","complete_zero_trip_zero_cost_run_can_pass_gate","quota_sufficiency_not_preclaimed"):
    assert v[k] is True
assert "BRAIN_SCORE_GE_81_8_PARTIAL" in load("osworld")["still_open"]

assert candidate["current_state"]["unresolved_atomic"]==26
assert candidate["implementation"]["supertransaction"]["causal_phase_upper_bound"]==2
assert candidate["finality"]["separate_manual_phase"] is False
assert candidate["proposed_authority_if_verified"]["scheduling_authority"] is True
assert candidate["proposed_authority_if_verified"]["execution_authority_broadening"] is False
assert candidate["fresh_reality_authority"] is False
assert candidate["accounting"]["acceptance_credit_delta"]==0

for name in (
    "canonical.tests.test_minimum_terminal_cut_solver_v2",
    "canonical.tests.test_terminal_adaptive_supertransaction_v2",
):
    m=importlib.import_module(name)
    tests=[getattr(m,n) for n in sorted(dir(m)) if n.startswith("test_") and callable(getattr(m,n))]
    assert tests
    for fn in tests:
        fn()
        print("PASS",name,fn.__name__)

from canonical.runtime.terminal_adaptive_supertransaction_v2 import evaluate
out=evaluate()
assert out["pass"] is True,out
assert out["root2_authority"]["frontier"]=="V6"
assert out["causal_phase_upper_bound"]==2
assert out["automatic_finality"]["separate_manual_phase_required"] is False
assert len(out["zero_probability_deleted_routes"])==4
assert out["fresh_reality_authority"] is False

print("PASS__ADAPTIVE_MINCUT_V2__ROOT2_V6_CURRENT__26_RESIDUAL__TWO_PHASE_MAX__ZERO_CREDIT")
