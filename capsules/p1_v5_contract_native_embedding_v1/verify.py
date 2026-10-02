from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/p1_v5_contract_native_population_embedding_v1.py":"a8c5af1d5e5efd06489ea8ea2db2549ac3e37ae2",
 "canonical/tests/test_p1_v5_contract_native_population_embedding_v1.py":"cb75bef70c6da86337ecce8faa63436911b1459a",
 "canonical/governance/P1_V5_CONTRACT_NATIVE_POPULATION_EMBEDDING_ACTIVATION_V1.json":"e427f0451d54b7f2718124ab58ccc6697aecdc10",
 "canonical/runtime/contract_native_proof_suites.py":"0210790c7dd705ef328e1b55d529a30c5c6c3337",
 "canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py":"2a8613ddac7402c7e6d2f349f9d3c32d3fb95e1d",
 "canonical/runtime/trajectory_failure_typed_ir_proof_v5.py":"3fc600a8176dac250219e3d98b92cf93d8fceef5",
 "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json":"8703c6aa08227467a619a7ae90d0d61f8e54da39",
 "canonical/governance/TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json":"a1630299d29ea9c07e55b4314c07ddb3228c3287",
 "canonical/governance/P1_TYPED_INTERVENTION_ENVELOPE_V5_ACTIVATION_V1.json":"e01df1a703266e055ab965ec7c37c491051b221b",
}

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,want in EXPECTED.items():
    got=blob(ROOT/rel)
    assert got==want,(rel,got,want)

subprocess.run(
    [sys.executable,"-m","unittest","canonical.tests.test_p1_v5_contract_native_population_embedding_v1","-v"],
    cwd=ROOT,
    check=True,
)

sys.path.insert(0,str(ROOT))
from canonical.runtime import p1_v5_contract_native_population_embedding_v1 as emb

out=emb.evaluate()
assert out["status"]=="PASS__FROZEN_CONTRACT_NATIVE_P1_POPULATION_EMBEDS_IN_V5__THREE_SUPERSET_RELATION_CANDIDATES",out
assert out["population_superset_proven"] is True
assert out["legacy_semantic_shape_count"]==30
assert out["embedded_domain_shape_count"]==180
assert out["canonical_domain_count"]==6
assert out["repair_order_invariance_checks"]==30
assert out["candidate_information_relation"]=="CANDIDATE_HAS_STRICTLY_LESS_INFORMATION_PROVEN"
assert out["removed_candidate_visible_field"]=="repair_candidates"
assert out["removed_field_load_bearing"] is False
assert out["oracle_relation"]=="CANDIDATE_STRONGER_PROVEN"
assert out["failures"]==[]
assert len(out["surface_relations"])==3
assert {x["relation"] for x in out["surface_relations"]}=={"SUPERSET"}
assert {x["claim_id"] for x in out["surface_relations"]}=={
 "P1-V5-FRONTIERCODE-CONTRACT-NATIVE-EMBEDDING-V1",
 "P1-V5-CURSORBENCH-CONTRACT-NATIVE-EMBEDDING-V1",
 "P1-V5-RECOVERY-CONTRACT-NATIVE-EMBEDDING-V1",
}
assert out["terminal_results_replayed"]==0
assert out["new_reality_units_consumed"]==0
assert out["capability_credit_delta"]==0
assert out["family_credit_delta"]==0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

print(json.dumps({
 "status":"PASS",
 "exact_brain_blob_count":len(EXPECTED),
 "legacy_semantic_shape_count":out["legacy_semantic_shape_count"],
 "embedded_domain_shape_count":out["embedded_domain_shape_count"],
 "repair_order_invariance_checks":out["repair_order_invariance_checks"],
 "wrong_legacy_repair_rejection_checks":out["wrong_legacy_repair_rejection_checks"],
 "surface_relations":out["surface_relations"],
 "candidate_information_relation":out["candidate_information_relation"],
 "oracle_relation":out["oracle_relation"],
 "terminal_results_replayed":0,
 "new_reality_units_consumed":0,
 "credit_delta":0,
},indent=2,sort_keys=True))
