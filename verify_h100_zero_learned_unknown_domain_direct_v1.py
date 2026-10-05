from __future__ import annotations
import hashlib, json, inspect
from pathlib import Path

from canonical.runtime.h100_zero_learned_unknown_domain_direct_candidate_v1 import step
from canonical.runtime.unknown_domain_direct_execution_harness_v1 import execute_case
from canonical.runtime.unknown_domain_direct_hidden_generator_v1 import generate_test_fixture_population
from canonical.runtime.unknown_domain_direct_hidden_scorer_v1 import aggregate, TRANSFER, ABSTAIN

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/h100_zero_learned_unknown_domain_direct_candidate_v1.py":"b9d289b29784b434aac9b61eb39450035927ff1e",
 "canonical/governance/H100_ZERO_LEARNED_UNKNOWN_DOMAIN_DIRECT_PREEXPOSURE_V1.json":"fb6e128c2bfeebec75beffbd147425f4a98988e0",
 "canonical/tests/test_h100_zero_learned_unknown_domain_direct_candidate_v1.py":"8186550b44402aa93d16105810120936a6d99867",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_GENERATOR_FREEZE_V1.json":"26108d0d06f7a308c3eaf4b9821ff0c4551dcda3",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json":"52090daf78d12020af48c1b6ffaea056d9029e1b",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_HARNESS_FREEZE_V1.json":"3e3a87962c13ad4c76621508763fab74df25cb44",
}

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for p,sha in EXPECTED.items():
    got=blob((ROOT/p).read_bytes())
    assert got==sha,(p,got,sha)

pre=json.loads((ROOT/"canonical/governance/H100_ZERO_LEARNED_UNKNOWN_DOMAIN_DIRECT_PREEXPOSURE_V1.json").read_text())
assert pre["status"].startswith("FROZEN_BEFORE_TEST_FIXTURE_OUTCOME")
assert pre["test_population"]["production"] is False
assert pre["accounting"]["generated_production_case_count"]==0
assert pre["candidate"]["persistent_learned_bytes"]==0
assert pre["candidate"]["external_frontier_model_calls"]==0
assert pre["candidate"]["external_learned_capability_calls"]==0

population=generate_test_fixture_population()
assert population["production"] is False
hidden={x["case_id"]:x for x in population["hidden_records"]}
executions=[]
results=[]
for visible in population["visible_cases"]:
    out=execute_case(candidate_step=step,case_visible=visible,hidden_record=hidden[visible["case_id"]])
    executions.append(out)
    results.append(out["scorer_result"])

agg=aggregate(results)
transfer=[x for x in executions if x["leaf_id"]==TRANSFER]
abstain=[x for x in executions if x["leaf_id"]==ABSTAIN]
assert len(transfer)==12 and len(abstain)==15
assert all(x["probe_count"]==1 for x in transfer)
assert agg["all_27_cases_pass"] is True
assert agg["transfer_leaf_pass"] is True
assert agg["abstention_leaf_pass"] is True
assert agg["status"]=="TWO_FROZEN_LEAVES_PASS"

src=inspect.getsource(__import__(
 "canonical.runtime.h100_zero_learned_unknown_domain_direct_candidate_v1",
 fromlist=["*"]
))
for token in ["transformers","torch","tensorflow","openai","anthropic",
              "unknown_domain_direct_hidden_scorer_v1",
              "unknown_domain_direct_hidden_generator_v1"]:
    assert token not in src,token

receipt={
 "schema":"PROJECT_BRAIN_H100_ZERO_LEARNED_UNKNOWN_DOMAIN_DIRECT_PUBLIC_RUNNER_RESULT_V1",
 "status":"PASS",
 "exact_blob_count":len(EXPECTED),
 "fixture":{"production":False,"case_count":27,"transfer_cases":12,"abstention_cases":15},
 "aggregate":agg,
 "transfer_probe_counts":sorted({x["probe_count"] for x in transfer}),
 "resource_boundary":{"persistent_learned_bytes":0,"external_frontier_model_calls":0,"external_learned_capability_calls":0},
 "conclusion":"FROZEN_ZERO_LEARNED_CANDIDATE_SOLVES_ALL_27_TEST_ONLY_DIRECT_UNKNOWN_DOMAIN_CASES_WITH_EXACT_TRANSFER_AND_CALIBRATED_ABSTENTION; EACH_TRANSFER_CASE_USES_ONE_PROBE.",
 "hard_nonclaims":["NO_PRODUCTION_CASE_GENERATION","NO_UNKNOWN_DOMAIN_ACCEPTANCE_CREDIT","NO_H100_TERMINAL_CREDIT","NO_OPEN_WORLD_GENERALIZATION_CLAIM"],
}
Path("h100_zero_learned_unknown_domain_direct_receipt_v1.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
