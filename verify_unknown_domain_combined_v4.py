from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
"canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
"canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
"canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
"canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
"canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
"canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":"8b855851b8a0fec3a0811c5033cc4ea6d2436954",
"canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
"canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
"canonical/runtime/unknown_domain_direct_combined_v4_universal_proof_v1.py":"fb5cec3efff41597cb5e64e4de982c697b73ac84",
}

def blob(path:str)->str:
 b=(ROOT/path).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
assert not drift,drift

from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_combined_v4_universal_proof_v1 as proof

# 1) Exact theorem must self-bind and preserve the frozen evaluator.
p=proof.prove()
assert p["status"]=="PASS__UNIVERSAL_COLLISION_TOTAL_AND_EXACT_FLOAT_SAFE_OVER_EXACT_V3_GENERATOR_DOMAIN"
assert p["exact_subject_blobs"]=={k:v for k,v in EXPECTED.items() if "combined_v4_universal_proof" not in k}
assert p["repairs"]["scorer_or_harness_relaxed"] is False
assert p["scope"]["terminal_or_production_cases_generated"]==0

# 2) Reproduce the old exact-float failure and prove candidate V3 repairs it
# against the unchanged scorer/harness.
secret=hashlib.sha256(b"secret0").digest()
visible,hidden=g2._transfer_case(secret,"beacon-qualification-0000000000000000",4,namespace="QUALONLY")
old=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
new=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
assert old["scorer_result"]["pass"] is False
assert old["scorer_result"]["errors"]==["DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG"]
assert set(old["candidate_terminal_action"]["support_feature_ids"])==set(hidden["transfer_relevant_feature_ids"])
assert new["scorer_result"]["pass"] is True,new
assert new["candidate_terminal_action"]["terminal_consequence"]==hidden["gold_terminal_consequence"]

# 3) Force maximally colliding/repeated permutation draws. Identifier correctness
# must survive because uniqueness comes from slot permutation, not hash uniqueness.
orig_draw=g3._draw
forced_draw_populations=0
try:
 for forced in (0,1,(1<<256)-1):
  g3._draw=lambda *args, _forced=forced, **kwargs: _forced
  packet=g3._generate(
   beacon=f"FORCED-DRAW-{forced}-BEACON-0000000000000000",
   evaluator_secret=hashlib.sha256(f"forced-{forced}".encode()).digest(),
   namespace=f"FORCED{forced%1000:03d}",
  )
  assert packet["case_count"]==27
  assert len({x["case_id"] for x in packet["visible_cases"]})==27
  results=[]
  for vis,hid in zip(packet["visible_cases"],packet["hidden_records"]):
   run=harness.execute_case(candidate_step=c3.step,case_visible=vis,hidden_record=hid)
   assert run["scorer_result"]["pass"] is True,(forced,vis["case_id"],hid,run)
   results.append(run["scorer_result"])
  assert scorer.aggregate(results)["all_27_cases_pass"] is True
  forced_draw_populations+=1
finally:
 g3._draw=orig_draw

# 4) Independent deterministic falsification sweep over many secrets/beacons.
# These are verifier fixtures only. generate_production_population is never called.
populations=512
cases=0
transfer_cases=0
max_probes=0
family_counts={}
class_counts={"IDENTIFIABLE":0,"NONIDENTIFIABLE":0,"UNDERSPECIFIED":0}
for i in range(populations):
 seed=hashlib.sha256(f"COMBINED-V4-INDEPENDENT-FALSIFIER-{i}".encode()).digest()
 beacon="COMBINED-V4-"+hashlib.sha256(b"beacon"+seed).hexdigest()
 packet=g3._generate(beacon=beacon,evaluator_secret=seed,namespace=f"IV4{i:04d}")
 assert packet["case_count"]==27
 results=[]
 for vis,hid in zip(packet["visible_cases"],packet["hidden_records"]):
  run=harness.execute_case(candidate_step=c3.step,case_visible=vis,hidden_record=hid)
  assert run["scorer_result"]["pass"] is True,(i,vis["case_id"],hid,run)
  results.append(run["scorer_result"])
  cases+=1
  if hid["leaf_id"]==g2.v1.TRANSFER:
   transfer_cases+=1
   max_probes=max(max_probes,run["probe_count"])
   fam=hid["primitive_family"]
   family_counts[fam]=family_counts.get(fam,0)+1
  else:
   cls=hid["identifiability_status"]
   class_counts[cls]+=1
 agg=scorer.aggregate(results)
 assert agg["all_27_cases_pass"] is True,(i,agg)

assert cases==populations*27
assert transfer_cases==populations*12
assert max_probes<=2
assert sorted(family_counts.values())==[populations*2]*6
assert class_counts=={k:populations*5 for k in class_counts}

print(json.dumps({
 "status":"INDEPENDENT_COMBINED_V4_VERIFICATION_PASS",
 "exact_subject_blobs":EXPECTED,
 "structural_universal_proof":"PASS",
 "old_v2_exact_float_counterexample_reproduced":True,
 "candidate_v3_repairs_old_counterexample_under_unchanged_scorer_v1":True,
 "forced_repeated_draw_populations":forced_draw_populations,
 "identifier_totality_under_forced_repeated_draws":"PASS",
 "falsifier_populations":populations,
 "falsifier_cases":cases,
 "falsifier_transfer_cases":transfer_cases,
 "max_transfer_probes_observed":max_probes,
 "production_cases_generated":0,
 "terminal_cases_consumed":0,
 "acceptance_credit_delta":0,
 "family_credit_delta":0
},sort_keys=True))
