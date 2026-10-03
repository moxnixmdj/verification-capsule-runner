from __future__ import annotations
import copy, hashlib, json
from pathlib import Path
from canonical.runtime.opus55_acceptance_residual_compiler_v3 import evaluate

ROOT=Path(__file__).resolve().parent
EXPECTED=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())

def blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for rel, expected in EXPECTED["files"].items():
    actual=blob_sha(ROOT/rel)
    assert actual==expected, (rel, expected, actual)

def load(rel):
    return json.loads((ROOT/rel).read_text())

reg=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
evid=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
comp=load("canonical/reasoning/2026-10-02_EXACT_OPUS55_ZERO_COST_COMPARATOR_ROUTE_RECONCILIATION_V1.json")
ready=load("canonical/governance/OPUS55_PUBLIC_BAR_SCORE_READINESS_MATRIX_V1.json")

out=evaluate(reg,evid,comp,ready)
assert out["errors"]==[], out
assert out["proved_predicate_count"]==12, out
assert out["open_predicate_count"]+out["blocked_predicate_count"]==26, out
assert out["receipt_saturation_complete"] is False, out
assert [a["action_id"] for a in out["authorized_actions"]]==["ACTION::SATURATE_EXISTING_RECEIPTS"], out
assert out["terminal_promotion_allowed"] is False, out
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0, out

row=next(x for x in evid["claims"] if x["predicate_id"]=="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
assert row["state"]=="PROVED"
assert row["proof_kind"]=="ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS"
sc=row["scope_completeness"]
assert sc["basis"]=="UNIVERSAL_FORMAL_SCOPE_PROOF"
assert sc["formal_completeness"] is True
assert sc["all_admissible_target_inputs_proved"] is True

mut=copy.deepcopy(evid)
mrow=next(x for x in mut["claims"] if x["predicate_id"]=="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
mrow["scope_completeness"]["all_admissible_target_inputs_proved"]=False
bad=evaluate(reg,mut,comp,ready)
assert (
    "NONINDEPENDENT_EVIDENCE:TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" in bad["errors"]
    or "UNIVERSAL_SCOPE_COMPLETENESS_NOT_ESTABLISHED:TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" in bad["errors"]
), bad

print(json.dumps({
 "status":"PASS",
 "proved_predicates":out["proved_predicate_count"],
 "unresolved_predicates":out["open_predicate_count"]+out["blocked_predicate_count"],
 "receipt_saturation_complete":out["receipt_saturation_complete"],
 "authorized_actions":[a["action_id"] for a in out["authorized_actions"]],
 "mutation_fail_closed":True,
 "terminal_promotion_allowed":out["terminal_promotion_allowed"]
},sort_keys=True))
