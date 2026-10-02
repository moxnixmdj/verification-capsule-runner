from __future__ import annotations
import hashlib,json
from pathlib import Path

from canonical.runtime.recovery_t0_t2_acceptance_ceiling_lifter_v1 import (
    STRICT_EARLIEST_CHECK,
    _semantic_relation_errors,
    evaluate,
)

ROOT=Path(__file__).resolve().parent
EXPECTED={
"canonical/runtime/recovery_t0_t2_acceptance_ceiling_lifter_v1.py":"632c0662925c2eb3c11da452d78a6d96d2eac66d",
"canonical/tests/test_recovery_t0_t2_acceptance_ceiling_lifter_v1.py":"501ad66e50c250a9183cccaf72dfab8aaf7fcc23",
"canonical/governance/RECOVERY_DUAL_SEMANTIC_FIREWALL_V2.json":"2a707920ce1a1b19daa0d13d9a36d328ac24319f",
"canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json":"f4fe68c78ccdf5392b5e24519ae9a57e620221a7",
"canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json":"5159f145fad8b07fe2164716aedf653a0b34a6e0",
"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":"eb4bca0fe6a015d49d2854998fbe046c979c7ea9",
"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":"ee187f611a0e82b2de495ee377682f39bc31dd31",
"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
"canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json":"8703c6aa08227467a619a7ae90d0d61f8e54da39",
"canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json":"bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
}
def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(rel:str):
    return json.loads((ROOT/rel).read_text())
for rel,expected in EXPECTED.items():
    got=blob(ROOT/rel)
    assert got==expected,(rel,got,expected)

relation=load("canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json")
semantic=_semantic_relation_errors(relation)
required={
 "RELATION_STRICT_EARLIEST_TARGET_HAS_NO_STRICT_SOURCE_PROOF",
 "RELATION_EARLIEST_TARGET_WEAKENED_TO_EARLIEST_OR_CRITICAL",
 "CAUSAL_LOCALIZATION_CEILING_DERIVED_FROM_WEAKER_DISJUNCTION",
}
assert required.issubset(set(semantic)),semantic

out=evaluate(
 protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
 registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
 predicates=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
 binding=load("canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"),
 terminal=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
 relation=relation,
)
assert out["pass"] is False,out
assert out["candidate_witness"] is None,out
assert "P1_EXECUTED_TERMINAL_SCOPE_MISMATCH_QUARANTINE_ACTIVE" in out["errors"],out
assert required.issubset(set(out["errors"])),out
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0,out
assert out["promotion_authority"] is False,out

# Independent truth-table countermodel.
critical=True
earliest=False
assert (critical or earliest) is True
assert earliest is False

# Semantic errors disappear only when a strict source is substituted.
strict=json.loads(json.dumps(relation))
strict["target_dimension_to_source_checks"]["earliest causal failure localization"]=[
 STRICT_EARLIEST_CHECK,
 "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
]
strict["acceptance_to_objective_floor_ceiling"]["causal_localization"]["source_check"]=STRICT_EARLIEST_CHECK
assert _semantic_relation_errors(strict)==[],_semantic_relation_errors(strict)

print(json.dumps({
 "status":"INDEPENDENT_RECOVERY_DUAL_SEMANTIC_FIREWALL_PASS",
 "exact_blob_count":len(EXPECTED),
 "current_quarantine_detected":True,
 "strict_earliest_nonimplication_verified":True,
 "semantic_error_count":len(required),
 "credit_delta":0
},indent=2,sort_keys=True))
