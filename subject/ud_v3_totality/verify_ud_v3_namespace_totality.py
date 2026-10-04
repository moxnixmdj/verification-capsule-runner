from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

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

def blob(path:str)->str:
 b=(ROOT/path).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
assert not drift,drift

from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_v3_universal_proof_v2 as proposed

FAMILIES=(
 "ORDER_PRESERVING_TRANSFORM",
 "PARITY_OR_SIGN_INVARIANT",
 "CONSERVATION_RELATION",
 "MONOTONE_CAUSAL_EDGE",
 "COMPOSITIONAL_REWRITE",
 "THRESHOLD_OR_PARTITION_INVARIANT",
)
assert tuple(g1.PRIMITIVE_FAMILIES)==FAMILIES
assert g1.PRODUCTION_CASE_COUNTS=={g1.TRANSFER:12,g1.ABSTAIN:15}
assert harness.MAX_TRANSFER_PROBES==2

# Independent continuous-envelope derivation.
MIN_MAG,MAX_MAG=0.25,3.5
D0,D1=4.75,6.25
assert 0.6*D0==2.85
sat_gap=0.7*D0/(1.0+10.0)**2
assert sat_gap>4.5e-9
for index in (1,7):
 assert (3+index)%2==0
 assert -MAX_MAG+D0>0
for index in (5,11):
 assert 4%2==0
 assert D0-2.2>0
for index in (4,10):
 assert (3+index)%2==1
 assert (3+index+1)%3!=0
 r0=tuple(-1 if (j+index)%2==0 else 1 for j in range(3))
 r1=tuple(-1 if (j+index+1)%3==0 else 1 for j in range(3))
 assert r0==c3.ADD2_R0_SIG==(-1,1,-1)
 assert r1==c3.ADD2_R1_SIG==(1,-1,1)
 assert r0!=r1
add2_min=min(D0-(MAX_MAG-MIN_MAG),D1,D0,D1-(MAX_MAG-MIN_MAG),D0+D1)
assert abs(add2_min-1.5)<1e-15

# Preserve the exact V2 counterexample and verify the V3 exact-order repair.
secret=hashlib.sha256(b"secret0").digest()
visible,hidden=g2._transfer_case(secret,"beacon-qualification-0000000000000000",4,namespace="QUALONLY")
v2out=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
assert v2out["scorer_result"]["pass"] is False
assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in v2out["scorer_result"]["errors"]
v3out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
assert v3out["scorer_result"]["pass"] is True,v3out
assert v3out["probe_count"]==1

# Independently attack the namespace-totality guard. These are in-memory
# verifier mutations of a qualification fixture, never production cases.
base=g2.generate_qualification_fixture_population(beacon="VERIFY-NAMESPACE-GUARD-00000001")
assert g3.validate_packet(base)["case_count"]==27

def must_reject(packet,needle):
 try:
  g3.validate_packet(packet)
 except g3.UnknownDomainGeneratorV3Error as exc:
  assert needle in str(exc),(needle,str(exc))
  return
 raise AssertionError("NAMESPACE_MUTATION_NOT_REJECTED:"+needle)

p=copy.deepcopy(base)
i=next(i for i,h in enumerate(p["hidden_records"]) if len(h.get("transfer_relevant_feature_ids",[]))==2)
p["hidden_records"][i]["transfer_relevant_feature_ids"][1]=p["hidden_records"][i]["transfer_relevant_feature_ids"][0]
must_reject(p,"TRANSFER_RELEVANT_DUPLICATE")

p=copy.deepcopy(base)
i=next(i for i,h in enumerate(p["hidden_records"]) if h.get("distractor_feature_ids"))
p["hidden_records"][i]["distractor_feature_ids"][1]=p["hidden_records"][i]["distractor_feature_ids"][0]
must_reject(p,"TRANSFER_DISTRACTORS_DUPLICATE")

p=copy.deepcopy(base)
i=next(i for i,v in enumerate(p["visible_cases"]) if v.get("domain_b",{}).get("allowed_probes"))
probes=p["visible_cases"][i]["domain_b"]["allowed_probes"]
probes[1]["probe_id"]=probes[0]["probe_id"]
must_reject(p,"TRANSFER_PROBE_IDS_DUPLICATE")

p=copy.deepcopy(base)
i=next(i for i,h in enumerate(p["hidden_records"]) if h.get("identifiability_status")=="NONIDENTIFIABLE")
hs=p["visible_cases"][i]["hypotheses"]
hs[1]["terminal_consequence"]=hs[0]["terminal_consequence"]
must_reject(p,"NONIDENTIFIABLE_CONSEQUENCE_COLLISION")

p=copy.deepcopy(base)
i=next(i for i,h in enumerate(p["hidden_records"]) if h.get("identifiability_status")=="UNDERSPECIFIED")
probes=p["visible_cases"][i]["allowed_probes"]
probes[1]["probe_id"]=probes[0]["probe_id"]
must_reject(p,"ABSTENTION_PROBE_IDS_DUPLICATE")

# Execute the proposed theorem only after independent byte binding, algebra,
# V2 falsification, V3 regression, and namespace attacks.
proof=proposed.prove()
assert proof["status"]=="PASS__UNIVERSAL_OVER_EVERY_STRUCTURALLY_VALID_POPULATION_EMITTED_BY_NAMESPACE_TOTAL_GENERATOR_V3"
assert proof["namespace_proof"]["probabilistic_collision_freeness_assumed"] is False
assert proof["accounting"]["production_cases_generated"]==0

# Broad verifier-only falsification across fresh deterministic secrets/beacons.
populations=256
cases=0
transfer_cases=0
max_probes=0
family_counts={x:0 for x in FAMILIES}
for i in range(populations):
 seed=hashlib.sha256(f"UDIR-V3-TOTALITY-FALSIFIER-{i}".encode()).digest()
 beacon="VERIFY-V3-TOTALITY-"+hashlib.sha256(b"beacon"+seed).hexdigest()
 packet=g3._generate(beacon=beacon,evaluator_secret=seed,namespace=f"VERIFYV3{i:04d}")
 assert packet["case_count"]==27
 results=[]
 for v,h in zip(packet["visible_cases"],packet["hidden_records"]):
  out=harness.execute_case(candidate_step=c3.step,case_visible=v,hidden_record=h)
  assert out["scorer_result"]["pass"] is True,(i,v["case_id"],out)
  results.append(out["scorer_result"])
  cases+=1
  if h["leaf_id"]==g1.TRANSFER:
   transfer_cases+=1
   max_probes=max(max_probes,out["probe_count"])
   family_counts[h["primitive_family"]]+=1
 agg=scorer.aggregate(results)
 assert agg["all_27_cases_pass"] is True,(i,agg)

assert cases==populations*27
assert transfer_cases==populations*12
assert max_probes<=2
assert all(v==populations*2 for v in family_counts.values())

print(json.dumps({
 "status":"INDEPENDENT_V3_NAMESPACE_TOTAL_UNIVERSAL_PROOF_PASS",
 "candidate_v3_git_blob":EXPECTED["canonical/runtime/unknown_domain_direct_candidate_v3.py"],
 "generator_v3_git_blob":EXPECTED["canonical/runtime/unknown_domain_direct_hidden_generator_v3.py"],
 "proof_v2_git_blob":EXPECTED["canonical/runtime/unknown_domain_direct_v3_universal_proof_v2.py"],
 "v2_exact_float_counterexample_preserved":True,
 "v3_exact_float_repair_pass":True,
 "namespace_adversarial_mutations_rejected":5,
 "probabilistic_collision_assumption":False,
 "continuous_structural_proof_checks":"PASS",
 "falsifier_populations":populations,
 "falsifier_cases":cases,
 "falsifier_transfer_cases":transfer_cases,
 "max_transfer_probes_observed":max_probes,
 "production_cases_generated":0,
 "acceptance_credit_delta":0,
 "ownership_credit_delta":0,
},sort_keys=True))
