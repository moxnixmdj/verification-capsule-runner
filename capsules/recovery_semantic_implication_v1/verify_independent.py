from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path

from canonical.runtime.recovery_semantic_implication_audit_v1 import (
    CAUSAL_TARGET_ATOM,
    EARLIEST_TARGET_ATOM,
    evaluate,
)

ROOT = Path(__file__).resolve().parent

def blob(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def load(rel: str):
    return json.loads((ROOT / rel).read_text())

target_path = ROOT / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"
p1_path = ROOT / "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
wave_path = ROOT / "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
binding_path = ROOT / "canonical/governance/OPUS55_RECOVERY_SEMANTIC_IMPLICATION_BINDING_V1.json"

target = load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json")
p1 = load("canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json")
wave = load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json")
binding = load("canonical/governance/OPUS55_RECOVERY_SEMANTIC_IMPLICATION_BINDING_V1.json")

assert blob(target_path) == binding["authority"]["target_normalization"]["git_blob_sha"]
assert blob(p1_path) == binding["authority"]["p1_binding"]["git_blob_sha"]
assert blob(wave_path) == binding["authority"]["terminal_wave"]["git_blob_sha"]

out = evaluate(target_normalization=target, p1_binding=p1, terminal_wave=wave)
assert out["pass"] is True, out
assert out["closed_predicates"] == []
assert out["predicate_credit_delta"] == 0
assert out["promotion_authority"] is False
assert [x["atom"] for x in out["candidate_positive_atom_bindings"]] == [CAUSAL_TARGET_ATOM]
assert out["nonimplication_certificates"][0]["atom"] == EARLIEST_TARGET_ATOM
cm = out["nonimplication_certificates"][0]["countermodel"]
assert cm["p1_disjunction_satisfied"] is True
assert cm["target_atom_satisfied"] is False
assert [x["state"] for x in out["metric_bounds"]] == ["OPEN", "OPEN", "OPEN"]

bad = copy.deepcopy(p1)
bad["evaluator"]["required_checks"].remove(
    "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT"
)
assert evaluate(target_normalization=target, p1_binding=bad, terminal_wave=wave)["pass"] is False

bad_wave = copy.deepcopy(wave)
for row in bad_wave["reduction_input"]["wave"]["parent_portfolio_receipts"]["T2"]:
    if row.get("behavior_id") == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
        row["binding_blob"] = "bad"
assert evaluate(target_normalization=target, p1_binding=p1, terminal_wave=bad_wave)["pass"] is False

print(json.dumps({
    "status": "INDEPENDENT_RECOVERY_SEMANTIC_IMPLICATION_PASS",
    "positive_atom_binding_count": 1,
    "nonimplication_certificate_count": 1,
    "open_metric_bound_count": 3,
    "closed_predicate_count": 0,
    "predicate_credit_delta": 0,
    "family_credit_delta": 0,
}, indent=2, sort_keys=True))
