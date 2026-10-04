#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUBJECT=ROOT/"subject/unknown_domain_v4_total_successor_20261005"
sys.path.insert(0,str(SUBJECT))

EXPECTED={
"canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
"canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
"canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
"canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
"canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
"canonical/runtime/unknown_domain_direct_hidden_generator_v4.py":"e52858b9fef2d795f72b45cd3ae82ad04344aa91",
"canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
"canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}
def blob(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,sha in EXPECTED.items(): assert blob(SUBJECT/rel)==sha,(rel,blob(SUBJECT/rel),sha)

from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer

# Frozen family algebra: wrong-support margins dominate V1 _close tolerance.
min_shift=4.75
true_abs_max=3.5
affine_gap=.6*min_shift
affine_tol=1e-9*max(1.0,2.0+2.6*(true_abs_max+6.5))
complement_gap=min_shift
complement_tol=1e-9*max(1.0,abs(8.0-(-true_abs_max)),abs(2.0-(true_abs_max+6.5)))
sat_gap=.7*min_shift/121.0
sat_tol=1e-9*4.5
assert affine_gap>affine_tol and complement_gap>complement_tol and sat_gap>sat_tol
assert -true_abs_max+min_shift>0.0
assert min_shift-2.2>0.0
assert min([4.75-(3.5-.25),6.25,4.75,6.25-(3.5-.25),11.0])==1.5
assert c3.ADD2_R0_SIG==(-1,1,-1)
assert c3.ADD2_R1_SIG==(1,-1,1)

def run_packet(packet):
 results=[]; probes=[]
 for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
  ex=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
  if ex["scorer_result"]["pass"] is not True:
   raise AssertionError(json.dumps({"visible":visible,"hidden":hidden,"execution":ex},sort_keys=True))
  results.append(ex["scorer_result"]); probes.append(ex["probe_count"])
 agg=scorer.aggregate(results); assert agg["all_27_cases_pass"] is True
 return probes

# Exact old V2 counterexample still repaired by current candidate V3.
secret=hashlib.sha256(b"secret0").digest()
visible,hidden=g2._transfer_case(secret,"beacon-qualification-0000000000000000",4,namespace="REVOCATION")
ex=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
assert ex["scorer_result"]["pass"] is True
assert ex["candidate_terminal_action"]["terminal_consequence"]==hidden["gold_terminal_consequence"]

# Strong totality falsifier: collapse every truncated token to one literal.
orig=g1._token
try:
 g1._token=lambda *args,**kwargs:"COLLISION"
 packet=g4._generate(beacon="FORCED-COLLISION-000000000000",evaluator_secret=b"x"*32,namespace="COLLIDE")
 assert len({x["case_id"] for x in packet["visible_cases"]})==27
 forced_probes=run_packet(packet)
finally:
 g1._token=orig

# Rank/label constructor itself stays injective under arbitrary suffix collision.
orig=g1._token
try:
 g1._token=lambda *args,**kwargs:"SAME"
 labels=g4._ranked_labels(b"x"*32,"B"*20,scope="proof",keys=[f"k{i}" for i in range(100)],prefix="X-")
 assert len(labels)==len(set(labels.values()))==100
finally:
 g1._token=orig

POPULATIONS=2048
cases=0; probe_hist={}; fam_hist={}
for k in range(POPULATIONS):
 secret=hashlib.sha256(f"v4-independent-secret-{k}".encode()).digest()
 beacon="V4-INDEPENDENT-"+hashlib.sha256(f"beacon-{k}".encode()).hexdigest()[:24]
 packet=g4._generate(beacon=beacon,evaluator_secret=secret,namespace=f"IV4{k}")
 results=[]
 for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"],strict=True):
  ex=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
  if ex["scorer_result"]["pass"] is not True:
   raise AssertionError(json.dumps({"population":k,"visible":visible,"hidden":hidden,"execution":ex},sort_keys=True))
  results.append(ex["scorer_result"]); cases+=1
  q=str(ex["probe_count"]); probe_hist[q]=probe_hist.get(q,0)+1
  if hidden["leaf_id"]==g1.TRANSFER:
   fam=str(hidden["primitive_family"]); fam_hist[fam]=fam_hist.get(fam,0)+1
 assert scorer.aggregate(results)["all_27_cases_pass"] is True

receipt={
 "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V4_TOTAL_SUCCESSOR_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__EXACT_V2_FLOAT_FALSIFIER_REPAIRED__ALL_TOKEN_COLLISION_SURVIVES_END_TO_END__ALGEBRAIC_MARGINS_BOUND__LARGE_FALSIFICATION_PASS",
 "exact_subject_blobs":EXPECTED,
 "algebraic_margins":{
  "affine_min_gap":affine_gap,"affine_max_close_tol":affine_tol,
  "complement_min_gap":complement_gap,"complement_max_close_tol":complement_tol,
  "sat_mono_min_gap":sat_gap,"sat_mono_max_close_tol":sat_tol,
  "sign_shifted_min":-true_abs_max+min_shift,"step_second_probe_margin":min_shift-2.2,
  "add2_wrong_support_min_gap":1.5,
  "add2_role_signatures":[list(c3.ADD2_R0_SIG),list(c3.ADD2_R1_SIG)]
 },
 "v2_exact_float_counterexample_repaired":True,
 "forced_all_token_collision_population_passed":True,
 "forced_all_token_collision_probe_histogram":{str(x):forced_probes.count(x) for x in sorted(set(forced_probes))},
 "ranked_label_100_way_forced_collision_unique":True,
 "synthetic_falsification":{"populations":POPULATIONS,"cases":cases,"probe_histogram":probe_hist,"transfer_family_histogram":fam_hist,"all_exact_hidden_scorer_pass":True},
 "hard_nonclaims":[
  "FINITE_FALSIFICATION_ALONE_IS_NOT_THE_UNIVERSAL_THEOREM",
  "ALGEBRAIC_ARGUMENT_IS_BOUND_ONLY_TO_THE_EXACT_FROZEN_V2_NUMERIC_FAMILY_AND_V4_IDENTIFIER_SUCCESSOR",
  "NO_OPEN_WORLD_GENERALIZATION",
  "NO_PRODUCTION_OR_TERMINAL_CASES_CONSUMED",
  "NO_ACCEPTANCE_CREDIT_GRANTED_BY_THIS_VERIFIER_ALONE"
 ],
 "accounting":{"incremental_spend_usd":0,"production_cases_consumed":0,"terminal_cases_consumed":0,"acceptance_credit_delta":0}
}
Path("unknown_domain_v4_total_successor_independent_verification_v1.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
