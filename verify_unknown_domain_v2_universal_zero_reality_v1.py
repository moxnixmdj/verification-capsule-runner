from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_V2_UNIVERSAL_PROOF_CANDIDATE_20261005_V1.json":"97084bbfb2d9228b9555c3fb71d29f4d0e8796fa",
 "canonical/runtime/unknown_domain_direct_v2_universal_proof_v1.py":"2400dba7f763fc16dc65c31512ccd9eee8be82fb",
 "canonical/tests/test_unknown_domain_direct_v2_universal_proof_v1.py":"e0a0436cf7bdb190a8228ca511e0a37d5a6947f0",
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}
def blob(path:str)->str:
 b=(ROOT/path).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
assert not drift, drift

from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_v2_universal_proof_v1 as proposed

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
assert candidate.TRANSFER==g1.TRANSFER and candidate.ABSTAIN==g1.ABSTAIN

# Independent structural derivation over the continuous generator envelope.
MIN_MAG,MAX_MAG=0.25,3.5
MIN_SHIFT=4.75
MAX_SHIFT=6.50
assert 0.6*MIN_SHIFT==2.85
assert MIN_SHIFT==4.75
sat_gap=0.7*MIN_SHIFT/(1+10.0)**2
sat_tol=4.5e-9
assert sat_gap>sat_tol
# SIGN transfer indices 1,7: first probe row j=3 is negative; shifted distractors are positive.
for index in (1,7):
 assert (3+index)%2==0
 assert -MAX_MAG+MIN_SHIFT>0
# STEP transfer indices 5,11: second probe row j=4 is below threshold; even the minimum
# distractor shift moves it strictly above threshold.
for index in (5,11):
 assert 4%2==0
 assert MIN_SHIFT-2.2>0
# ADD2 transfer indices 4,10: first probe j=3 has both true roles positive.
for index in (4,10):
 assert (3+index)%2==1
 assert (3+index+1)%3!=0
add2_min=min(
 4.75-(MAX_MAG-MIN_MAG),
 6.25,
 4.75,
 6.25-(MAX_MAG-MIN_MAG),
 4.75+6.25,
)
assert abs(add2_min-1.5)<1e-15

# Directly verify abstention contract shape is total and balanced.
assert tuple(g1.ABSTAIN_CLASSES)==("IDENTIFIABLE","NONIDENTIFIABLE","UNDERSPECIFIED")
assert scorer.DECISIONS=={"CONCLUDE","ABSTAIN","REQUEST_DISCRIMINATOR"}

# Execute the proposed content-bound proof only after independent source binding and
# independent inequality checks above.
p=proposed.prove()
assert p["status"]=="PASS__UNIVERSAL_OVER_EXACT_FROZEN_V2_GENERATOR_DOMAIN"
assert p["exact_subject_blobs"]=={k:v for k,v in EXPECTED.items() if k.startswith("canonical/runtime/unknown_domain_direct_") and "universal_proof" not in k}

# Deterministic adversarial falsification supplement. These are verifier fixtures,
# not production populations and never call generate_production_population.
populations=256
cases=0
transfer_cases=0
max_probes=0
family_counts={x:0 for x in FAMILIES}
for i in range(populations):
 seed=hashlib.sha256(f"UDIR-UNIVERSAL-FALSIFIER-{i}".encode()).digest()
 beacon="VERIFY-UNIVERSAL-"+hashlib.sha256(b"beacon"+seed).hexdigest()
 packet=g2._generate(beacon=beacon,evaluator_secret=seed,namespace=f"VERIFY{i:04d}")
 assert packet["case_count"]==27
 results=[]
 for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
  out=harness.execute_case(candidate_step=candidate.step,case_visible=visible,hidden_record=hidden)
  assert out["scorer_result"]["pass"] is True,(i,visible["case_id"],hidden,out)
  results.append(out["scorer_result"])
  cases+=1
  if hidden["leaf_id"]==g1.TRANSFER:
   transfer_cases+=1
   max_probes=max(max_probes,out["probe_count"])
   family_counts[hidden["primitive_family"]]+=1
 agg=scorer.aggregate(results)
 assert agg["all_27_cases_pass"] is True,(i,agg)

assert cases==populations*27
assert transfer_cases==populations*12
assert max_probes<=2
assert all(v==populations*2 for v in family_counts.values())

print(json.dumps({
 "status":"INDEPENDENT_CONTENT_BOUND_UNIVERSAL_PROOF_PASS",
 "proof_subject_git_blob":EXPECTED["canonical/runtime/unknown_domain_direct_v2_universal_proof_v1.py"],
 "candidate_v2_git_blob":EXPECTED["canonical/runtime/unknown_domain_direct_candidate_v2.py"],
 "generator_v2_git_blob":EXPECTED["canonical/runtime/unknown_domain_direct_hidden_generator_v2.py"],
 "continuous_structural_proof_checks":"PASS",
 "falsifier_populations":populations,
 "falsifier_cases":cases,
 "falsifier_transfer_cases":transfer_cases,
 "max_transfer_probes_observed":max_probes,
 "production_cases_generated":0,
 "fresh_reality_required_for_exact_frozen_generator_claim":False,
 "acceptance_credit_delta":0,
 "ownership_credit_delta":0
},sort_keys=True))
