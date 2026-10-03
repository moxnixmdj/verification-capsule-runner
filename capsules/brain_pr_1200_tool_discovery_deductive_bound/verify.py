from __future__ import annotations
import hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
def blob_sha(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def load(name):
    return json.loads((ROOT/"brain"/name).read_text(encoding="utf-8"))
EXPECTED={
 "DEDUCTIVE_BOUND.json":"d66804163da3310ceb5f44bdf759fbf77368e42b",
 "OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 "TOOL_DISCOVERY_TOOLATHLON_MATCHED_SCOPE_BRIDGE_V1.json":"a5445019120433ca445468306b7364b938e80a9a",
 "CURRENT_TERMINAL_AUTHORITY_V1.json":"1f72486f1b4eeb22ea052cd0c2201890a6ef3d0f",
 "TOOLATHLON_BRAIN_OWNED_SELECTION_ADAPTER_V1.json":"e3f1b6cb6bccd7bf8bc14e2042826389f90f9bb2",
}
for name,sha in EXPECTED.items():
    got=blob_sha(ROOT/"brain"/name)
    assert got==sha,(name,got,sha)

r=load("DEDUCTIVE_BOUND.json")
p=load("OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
b=load("TOOL_DISCOVERY_TOOLATHLON_MATCHED_SCOPE_BRIDGE_V1.json")
a=load("CURRENT_TERMINAL_AUTHORITY_V1.json")
g=load("TOOLATHLON_BRAIN_OWNED_SELECTION_ADAPTER_V1.json")

proto=next(x for x in p["protocols"] if x["family"]=="TOOL_DISCOVERY_SELECTION_AND_LEARNING")
assert proto["status"]=="DEFINED_RESULT_OPEN"
assert "terminal_success" in proto["primary_metrics"]
assert "valid_route_top1" in proto["primary_metrics"]
assert proto["proof_mode"]=="MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER"

effect=b["precondition_effect_if_independently_verified"]
assert "BRAIN_MATCHED_TARGET_RESULT_INDEPENDENT_PASS" in effect["does_not_close"]
assert "NO_BRAIN_TOOLATHLON_RESULT" in b["hard_nonclaims"]
assert b["frozen_target"]["task_count"]==108

assert a["truth"]["opus55_acceptance"]=="3/19_PASS__16/19_OPEN"
assert a["truth"]["achieved"] is False
assert "TOOLATHLON" in a["next"]
assert "ACQUIRE_ONLY_THE_SAFE_PROBE_OR_IRREDUCIBLE_MATCHED_EVIDENCE_SELECTED" in a["next"]

sg=g["source_gate_v2_target_projection"]
assert str(sg["general_substrate_test_pass"]).startswith("PENDING_")
req=set(g["required_before_any_toolathlon_terminal_case"])
assert "GENERAL_SUBSTRATE_MATERIALITY_COUNTERFACTUAL_INDEPENDENT_PASS" in req
assert "REAL_TOOLATHLON_DECOUPLED_HOST_INTEGRATION_BINDS_GATEWAY_TO_THIS_ADAPTER" in req
assert g["execution_authority"] is False
assert g["family_credit_delta"]==0

d=r["deduction"]
assert "PROVED_TERMINAL_SUCCESS_TRIAL_LOWER_BOUND_EQUALS_0_OF_324" in d["conclusion"]
assert "PROVED_TOOLATHLON_TASK_PASS_LOWER_BOUND_EQUALS_0_OF_108" in d["conclusion"]
m=r["opus_reference_candidate_math"]
assert m["integer_successes_consistent_with_published_pass_at_1"]==252
assert m["integer_failures"]==72
assert round(100*252/324,1)==77.8
assert m["fail_lock_condition"]=="FAILURE_COUNT_GTE_73"
assert "NOT_YET_A_MATCHED_ACCEPTANCE_BAR" in m["hard_boundary"]
assert r["new_reality_units_consumed"]==0
assert r["family_credit_delta"]==0
assert r["execution_authority"] is False
print("PASS: Brain PR 1200 Tool Discovery deductive bound is exact-byte grounded and truth-preserving.")
