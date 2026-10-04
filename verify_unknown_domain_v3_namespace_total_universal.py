from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
from fractions import Fraction
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as proof1
from canonical.runtime import unknown_domain_direct_v3_universal_proof_v2 as proof2

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":"6582f60d67d4bee7851cfa42ec1d677c643d8c2e",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/runtime/unknown_domain_direct_v3_universal_proof_v1.py":"ee5f3832fdbad5ae645b0626e9f39ebeaee2b1da",
 "canonical/runtime/unknown_domain_direct_v3_universal_proof_v2.py":"549f2887eb85492cc9f1e46bad41d8d51f4fb48e",
}

def git_blob(p:Path)->str:
 b=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

got={p:git_blob(ROOT/p) for p in EXPECTED}
assert got==EXPECTED,(got,EXPECTED)

# Exact structural composition: V3 generation does not rewrite a successful V2
# packet. It passes identical generator arguments into V2 and then validates.
src=inspect.getsource(g3._generate)
tree=ast.parse(src)
fn=tree.body[0]
assert isinstance(fn,ast.FunctionDef) and fn.name=="_generate"
assert len(fn.body)==1 and isinstance(fn.body[0],ast.Return)
outer=fn.body[0].value
assert isinstance(outer,ast.Call) and isinstance(outer.func,ast.Name) and outer.func.id=="validate_packet"
assert len(outer.args)==1 and isinstance(outer.args[0],ast.Call)
inner=outer.args[0]
assert isinstance(inner.func,ast.Attribute)
assert isinstance(inner.func.value,ast.Name) and inner.func.value.id=="v2" and inner.func.attr=="_generate"
kw={k.arg:k.value for k in inner.keywords}
for name in ("beacon","evaluator_secret","namespace"):
 assert name in kw and isinstance(kw[name],ast.Name) and kw[name].id==name
assert "return dict(packet)" in inspect.getsource(g3.validate_packet)

# Candidate V3 must remain zero-learned and must not import evaluator internals.
c3src=inspect.getsource(c3)
for token in (
 "unknown_domain_direct_hidden_generator",
 "unknown_domain_direct_hidden_scorer",
 "unknown_domain_direct_execution_harness",
 "openai","anthropic","transformers","torch",
):
 assert token not in c3src,token

# Preserve the real V2 falsifier, then require exact repair by V3.
secret=hashlib.sha256(b"secret0").digest()
beacon="beacon-qualification-0000000000000000"
visible,hidden=g2._transfer_case(secret,beacon,4,namespace="QUALONLY")
old=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
assert old["scorer_result"]["pass"] is False
assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in old["scorer_result"]["errors"]
assert set(old["candidate_terminal_action"]["support_feature_ids"])==set(hidden["transfer_relevant_feature_ids"])
assert 0 < abs(old["candidate_terminal_action"]["terminal_consequence"]-hidden["gold_terminal_consequence"]) < 1e-12
new=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
assert new["scorer_result"]["pass"] is True,new["scorer_result"]
assert new["candidate_terminal_action"]["terminal_consequence"]==hidden["gold_terminal_consequence"]
assert new["probe_count"]==1

# Re-derive load-bearing analytic margins independently.
assert Fraction(3,5)*Fraction(19,4)==Fraction(57,20)
assert Fraction(19,4)==Fraction(19,4)
assert Fraction(7,10)*Fraction(19,4)/Fraction(121,1) > Fraction(45,10)*Fraction(1,10**9)
assert -Fraction(7,2)+Fraction(19,4)==Fraction(5,4)
assert Fraction(19,4)-Fraction(11,5)==Fraction(51,20)
add2=(
 Fraction(19,4)-(Fraction(7,2)-Fraction(1,4)),
 Fraction(25,4),
 Fraction(19,4),
 Fraction(25,4)-(Fraction(7,2)-Fraction(1,4)),
 Fraction(19,4)+Fraction(25,4),
)
assert min(add2)==Fraction(3,2)
for index in (4,10):
 r0=tuple(-1 if (j+index)%2==0 else 1 for j in range(3))
 r1=tuple(-1 if (j+index+1)%3==0 else 1 for j in range(3))
 assert r0==c3.ADD2_R0_SIG==(-1,1,-1)
 assert r1==c3.ADD2_R1_SIG==(1,-1,1)

p1=proof1.prove(ROOT)
assert p1["status"]=="PASS__UNIVERSAL_OVER_EXACT_FROZEN_V2_GENERATOR_DOMAIN_WITH_V3_EXACTNESS_REPAIR"
assert p1["v2_counterexample_status"].startswith("PROVED_BY_REGRESSION_TEST")
p2=proof2.prove(ROOT)
assert p2["status"]=="PASS__UNIVERSAL_OVER_EVERY_STRUCTURALLY_VALID_POPULATION_EMITTED_BY_NAMESPACE_TOTAL_GENERATOR_V3"
assert p2["namespace_proof"]["probabilistic_collision_freeness_assumed"] is False
assert p2["fresh_reality_required_for_this_exact_emitted_population_claim"] is False

# Adversarially inject each harmful namespace-collapse class and require fail-closed.
base=g2.generate_qualification_fixture_population(beacon="INDEPENDENT-NAMESPACE-MUTATION-0001")

def must_fail(packet,needle):
 try:
  g3.validate_packet(packet)
 except g3.UnknownDomainGeneratorV3Error as exc:
  assert needle in str(exc),(needle,str(exc))
 else:
  raise AssertionError("MUTATED_PACKET_WAS_EMITTED:"+needle)

x=copy.deepcopy(base)
i=next(i for i,h in enumerate(x["hidden_records"]) if len(h.get("transfer_relevant_feature_ids",[]))==2)
x["hidden_records"][i]["transfer_relevant_feature_ids"][1]=x["hidden_records"][i]["transfer_relevant_feature_ids"][0]
must_fail(x,"TRANSFER_RELEVANT_DUPLICATE")

x=copy.deepcopy(base)
i=next(i for i,h in enumerate(x["hidden_records"]) if h.get("distractor_feature_ids"))
x["hidden_records"][i]["distractor_feature_ids"][1]=x["hidden_records"][i]["distractor_feature_ids"][0]
must_fail(x,"TRANSFER_DISTRACTORS_DUPLICATE")

x=copy.deepcopy(base)
i=next(i for i,v in enumerate(x["visible_cases"]) if v.get("domain_b",{}).get("allowed_probes"))
ps=x["visible_cases"][i]["domain_b"]["allowed_probes"]
ps[1]["probe_id"]=ps[0]["probe_id"]
must_fail(x,"TRANSFER_PROBE_IDS_DUPLICATE")

x=copy.deepcopy(base)
i=next(i for i,h in enumerate(x["hidden_records"]) if h.get("identifiability_status")=="NONIDENTIFIABLE")
hs=x["visible_cases"][i]["hypotheses"]
hs[1]["terminal_consequence"]=hs[0]["terminal_consequence"]
must_fail(x,"NONIDENTIFIABLE_CONSEQUENCE_COLLISION")

x=copy.deepcopy(base)
i=next(i for i,h in enumerate(x["hidden_records"]) if h.get("identifiability_status")=="UNDERSPECIFIED")
ps=x["visible_cases"][i]["allowed_probes"]
ps[1]["probe_id"]=ps[0]["probe_id"]
must_fail(x,"ABSTENTION_PROBE_IDS_DUPLICATE")

x=copy.deepcopy(base)
x["visible_cases"][1]["case_id"]=x["visible_cases"][0]["case_id"]
x["hidden_records"][1]["case_id"]=x["hidden_records"][0]["case_id"]
must_fail(x,"VISIBLE_CASE_IDS_DUPLICATE")

# Fresh verifier-only populations. This is falsification support, not an inference
# from sampling and never calls generate_production_population.
populations=256
cases=0
max_probes=0
for i in range(populations):
 b=f"INDEPENDENT-V3-VERIFY-{i:04d}-20261005"
 s=hashlib.sha256(f"v3-independent-secret-{i}".encode()).digest()
 packet=g3._generate(beacon=b,evaluator_secret=s,namespace="VERIFYV3")
 assert packet["case_count"]==27
 rows=[]
 for vis,hid in zip(packet["visible_cases"],packet["hidden_records"]):
  out=harness.execute_case(candidate_step=c3.step,case_visible=vis,hidden_record=hid)
  assert out["scorer_result"]["pass"] is True,{"population":i,"case":vis["case_id"],"errors":out["scorer_result"]["errors"]}
  max_probes=max(max_probes,out["probe_count"])
  rows.append(out["scorer_result"])
  cases+=1
 agg=scorer.aggregate(rows)
 assert agg["all_27_cases_pass"] is True
assert cases==6912
assert max_probes<=2

receipt={
 "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V3_NAMESPACE_TOTAL_UNIVERSAL_PUBLIC_VERIFICATION_V1",
 "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_BYTES__V2_FLOAT_FALSIFIER_PRESERVED__V3_EXACTNESS_REPAIR__NAMESPACE_FAIL_CLOSED__6912_FRESH_SYNTHETIC_FALSIFICATION_CASES__ZERO_CREDIT",
 "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
 "exact_subject_blobs":EXPECTED,
 "v2_exact_float_counterexample_reproduced":True,
 "v3_exact_float_counterexample_repaired":True,
 "generator_composition":"EXACT_AST_BINDING__V3_GENERATE_EQUALS_VALIDATE_OF_V2_GENERATE",
 "namespace_collision_classes_injected_and_rejected":6,
 "universal_theorem_status":p2["status"],
 "fresh_synthetic_falsification":{"populations":populations,"cases":cases,"all_pass":True,"max_transfer_probes":max_probes,"production_authority_used":False},
 "production_cases_generated":0,
 "terminal_cases_consumed":0,
 "incremental_spend_usd":0,
 "acceptance_credit_delta":0,
 "hard_nonclaims":[
  "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION",
  "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_VERIFIER",
  "NO_INFERENCE_OF_UNIVERSALITY_FROM_THE_6912_CASE_SAMPLE",
  "SEPARATE_SCOPE_EQUIVALENCE_AND_ACCEPTANCE_REDUCTION_REQUIRED",
 ],
}
print(json.dumps(receipt,sort_keys=True))
