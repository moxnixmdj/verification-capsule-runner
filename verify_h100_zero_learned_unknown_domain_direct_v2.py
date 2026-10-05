from __future__ import annotations
import hashlib,json,inspect
from pathlib import Path
from canonical.runtime.h100_zero_learned_unknown_domain_direct_candidate_v2 import step
from canonical.runtime.unknown_domain_direct_execution_harness_v1 import execute_case
from canonical.runtime.unknown_domain_direct_hidden_generator_v1 import generate_test_fixture_population
from canonical.runtime.unknown_domain_direct_hidden_scorer_v1 import aggregate,TRANSFER,ABSTAIN

ROOT=Path(__file__).resolve().parent
EXPECTED={
"canonical/runtime/h100_zero_learned_unknown_domain_direct_candidate_v1.py":"b9d289b29784b434aac9b61eb39450035927ff1e",
"canonical/runtime/h100_zero_learned_unknown_domain_direct_candidate_v2.py":"2101b7b8fe6b725d82c518d5abaccee381b4d1f9",
"canonical/governance/H100_ZERO_LEARNED_UNKNOWN_DOMAIN_DIRECT_PREEXPOSURE_V2.json":"f98510ace930638974d59e1fc83539b8f71e71f8",
"canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
"canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
"canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
}
def blob(b):return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for p,s in EXPECTED.items():
 g=blob((ROOT/p).read_bytes());assert g==s,(p,g,s)
pre=json.loads((ROOT/"canonical/governance/H100_ZERO_LEARNED_UNKNOWN_DOMAIN_DIRECT_PREEXPOSURE_V2.json").read_text())
assert pre["status"].startswith("FROZEN_BEFORE_V2_TEST_FIXTURE_OUTCOME")
assert pre["accounting"]["generated_production_case_count"]==0
pop=generate_test_fixture_population(); assert pop["production"] is False
hidden={x["case_id"]:x for x in pop["hidden_records"]}
outs=[]; rows=[]
for visible in pop["visible_cases"]:
 o=execute_case(candidate_step=step,case_visible=visible,hidden_record=hidden[visible["case_id"]])
 outs.append(o);rows.append(o["scorer_result"])
agg=aggregate(rows)
transfer=[x for x in outs if x["leaf_id"]==TRANSFER]
abstain=[x for x in outs if x["leaf_id"]==ABSTAIN]
assert len(transfer)==12 and len(abstain)==15
assert max(x["probe_count"] for x in transfer)<=2
assert agg["all_27_cases_pass"] is True
src=inspect.getsource(__import__("canonical.runtime.h100_zero_learned_unknown_domain_direct_candidate_v2",fromlist=["*"]))
for token in ["transformers","tensorflow","openai","anthropic","unknown_domain_direct_hidden_scorer_v1","unknown_domain_direct_hidden_generator_v1"]:
 assert token not in src,token
receipt={"schema":"PROJECT_BRAIN_H100_ZERO_LEARNED_UNKNOWN_DOMAIN_DIRECT_PUBLIC_RUNNER_RESULT_V2","status":"PASS","exact_blob_count":len(EXPECTED),"aggregate":agg,"transfer_probe_counts":{str(n):sum(x["probe_count"]==n for x in transfer) for n in sorted({x["probe_count"] for x in transfer})},"resource_boundary":{"persistent_learned_bytes":0,"external_frontier_model_calls":0,"external_learned_capability_calls":0},"conclusion":"FROZEN_V2_ZERO_LEARNED_CANDIDATE_SOLVES_ALL_27_TESTONLY_DIRECT_UNKNOWN_DOMAIN_CASES_WITH_MAX_TWO_PROBES_PER_TRANSFER","hard_nonclaims":["NO_PRODUCTION_CASE_GENERATION","NO_UNKNOWN_DOMAIN_ACCEPTANCE_CREDIT","NO_OPEN_WORLD_GENERALIZATION_CLAIM","NO_TERMINAL_CREDIT"]}
Path("h100_zero_learned_unknown_domain_direct_receipt_v2.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
