from __future__ import annotations
import hashlib, importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "QUALITATIVE_PAIRWISE_PROMPT_NONENTAILMENT_CUT_20261007_V1.json":"bd1018b320418aeaa8aa6a06cd8df85521bad2b8",
 "qualitative_pairwise_prompt_nonentailment_v1.py":"2d309030afa3dc189579a8d989dfb52614063adf",
 "GDPVAL_AA_V21_PUBLIC_COMPARATOR_CUT_20261007_V1.json":"9bc454e57d544624a766bc808b56ef8fe673206e",
 "ABOVE_EXPONENTIAL_NO_FREE_LUNCH_FRONTIER_20261007_V1.json":"50ad273cc6c897a1d0809ed5d22c7b76be66124b",
 "P2_VISIBLE_GATE_SELF_PROOF_FALSIFIER_20261007_V1.json":"23bc8bc11a1e55222f4071320741f40213742b9c",
}
def blob(p):
 data=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
for name,want in EXPECTED.items():
 got=blob(ROOT/name)
 assert got==want,(name,got,want)

gov=json.loads((ROOT/"QUALITATIVE_PAIRWISE_PROMPT_NONENTAILMENT_CUT_20261007_V1.json").read_text())
cut=json.loads((ROOT/"GDPVAL_AA_V21_PUBLIC_COMPARATOR_CUT_20261007_V1.json").read_text())
nfl=json.loads((ROOT/"ABOVE_EXPONENTIAL_NO_FREE_LUNCH_FRONTIER_20261007_V1.json").read_text())
p2=json.loads((ROOT/"P2_VISIBLE_GATE_SELF_PROOF_FALSIFIER_20261007_V1.json").read_text())
assert gov["accounting"]["terminal_credit_delta"]==0
assert cut["proof_effect"]["exact_target_relation_recovered"] is False
assert cut["proof_effect"]["U_empty"] is False
assert "VISIBLE_P2_GATE_IMPROVEMENT_ALONE_PROVES_COMPLETE_HIDDEN_QUALITY_ORDER" in nfl["falsified_shortcuts"]
assert p2["countermodel"]["hidden_load_bearing_dimension_can_reverse_order"] is True

mod_path=ROOT/"qualitative_pairwise_prompt_nonentailment_v1.py"
spec=importlib.util.spec_from_file_location("candidate",mod_path)
candidate=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(candidate)

base={
 "shared_contract":{
   "prompt_blob_sha":"1"*40,
   "input_digest":"2"*64,
   "judge_identities":["J1","J2","J3"],
   "aggregation_digest":"3"*64,
   "output_schema":"PAIRWISE_A_OR_B",
 },
 "worlds":[
   {"same_public_contract":True,"judge_semantics_bound":False,"preference":"A"},
   {"same_public_contract":True,"judge_semantics_bound":False,"preference":"B"},
 ],
}
out=candidate.evaluate(base)
assert out["pass"] is True
assert out["unique_preference_entailed"] is False
assert out["exact_prompt_bytes_alone_sufficient"] is False
assert out["terminal_credit_delta"]==0

bad=json.loads(json.dumps(base)); bad["worlds"][1]["preference"]="A"
try: candidate.evaluate(bad)
except candidate.PairwiseNonentailmentError as e: assert "DOES_NOT_FLIP" in str(e)
else: raise AssertionError("same-preference counterfeit accepted")

bad=json.loads(json.dumps(base)); bad["worlds"][0]["judge_semantics_bound"]=True
try: candidate.evaluate(bad)
except candidate.PairwiseNonentailmentError as e: assert "MUST_LEAVE_JUDGE_SEMANTICS_UNBOUND" in str(e)
else: raise AssertionError("bound-semantics world accepted by this countermodel")

bad=json.loads(json.dumps(base)); bad["worlds"][1]["same_public_contract"]=False
try: candidate.evaluate(bad)
except candidate.PairwiseNonentailmentError as e: assert "PUBLIC_CONTRACT_MISMATCH" in str(e)
else: raise AssertionError("different-contract world accepted")

print(json.dumps({
 "status":"PASS",
 "exact_candidate_blobs":EXPECTED,
 "logical_countermodel_pass":True,
 "source_boundary_consistency_pass":True,
 "terminal_credit_delta":0
},sort_keys=True))
