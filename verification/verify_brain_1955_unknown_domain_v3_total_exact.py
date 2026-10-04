#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as proposed

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"22559a9daa6f6c22c1d373565989a95e9c3b9f7f",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":"03a40a88801d1a7871e2b239ca00fee415ffb000",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/runtime/unknown_domain_direct_v3_universal_proof_v1.py":"d2303d16e810b5da5632ecbe63078f65eb6a14f7",
}

def blob(path:Path)->str:
 b=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

got={p:blob(ROOT/p) for p in EXPECTED}
assert got==EXPECTED,{"expected":EXPECTED,"got":got}

# Independent structural totality: uniqueness is enumerate(rank), not digest uniqueness.
orig_rank=g3._rank_digest
try:
 g3._rank_digest=lambda secret,beacon,scope,label:b"\x00"*32
 for n in range(1,28):
  labels=tuple(f"L{i}" for i in range(n))
  m=g3._opaque_bijection(
   b"X"*32,"FORCED-TIE-BEACON-00000000",
   scope=f"VERIFY-{n}",labels=labels,prefix="Q-"
  )
  assert set(m)==set(labels)
  assert len(set(m.values()))==n

 # Strong evaluator-level falsifier: all ranking digests tie in every identifier
 # scope, yet the complete 27-case packet must still exist and pass unchanged scorer.
 tie_packet=g3._generate(
  beacon="FORCED-TOTAL-RANK-TIE-BEACON-0001",
  evaluator_secret=b"Z"*32,
  namespace="TIEVERIFY",
 )
 assert tie_packet["case_count"]==27
 assert len({x["case_id"] for x in tie_packet["visible_cases"]})==27
 tie_results=[]
 for visible,hidden in zip(tie_packet["visible_cases"],tie_packet["hidden_records"]):
  out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
  assert out["scorer_result"]["pass"],(visible["case_id"],out["scorer_result"])
  tie_results.append(out["scorer_result"])
 assert scorer.aggregate(tie_results)["all_27_cases_pass"] is True
finally:
 g3._rank_digest=orig_rank

# Reproduce the exact V2 binary64 role-order falsifier and require V3 repair.
secret=hashlib.sha256(b"secret0").digest()
beacon="beacon-qualification-0000000000000000"
visible,hidden=g2._transfer_case(secret,beacon,4,namespace="REVOCATION")
old=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
assert old["scorer_result"]["pass"] is False
assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in old["scorer_result"]["errors"]
new=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
assert new["scorer_result"]["pass"] is True,new["scorer_result"]
assert new["candidate_terminal_action"]["terminal_consequence"]==hidden["gold_terminal_consequence"]
assert set(new["candidate_terminal_action"]["support_feature_ids"])==set(hidden["transfer_relevant_feature_ids"])
assert new["probe_count"]<hidden["full_rediscovery_probe_floor"]

# Bind exact ADD2 operation order after orientation.
gen_src="".join(inspect.getsource(g1._eval).split())
cand_src="".join(inspect.getsource(c1._program_eval).split())
assert 'returnfloat(p["bias"])+float(role_values["r0"])+float(role_values["r1"])' in gen_src
assert 'return_finite(params["bias"],"bias")+_finite(role_values["r0"],"r0")+_finite(role_values["r1"],"r1")' in cand_src

# Independent strict-margin checks for wrong support elimination.
min_shift=4.75
assert 0.6*min_shift>1.0
assert min_shift>1.0
assert 0.7*min_shift/121.0>4.5e-9
assert -3.5+min_shift>0.0
assert min_shift-2.2>0.0
add2_gap=min(
 4.75-(3.5-0.25),
 6.25,
 4.75,
 6.25-(3.5-0.25),
 4.75+6.25,
)
assert add2_gap==1.5
assert harness.MAX_TRANSFER_PROBES==2

# Deterministic nonproduction falsification sweep over varied secret/beacon pairs.
populations=128
cases=0
for i in range(populations):
 packet=g3._generate(
  beacon=f"INDEPENDENT-V3-TOTAL-EXACT-{i:04d}-BEACON",
  evaluator_secret=hashlib.sha256(f"verify-secret-{i}".encode()).digest(),
  namespace=f"IV{i}",
 )
 results=[]
 for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
  out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
  assert out["scorer_result"]["pass"],{
   "population":i,
   "case_id":visible["case_id"],
   "errors":out["scorer_result"].get("errors"),
  }
  results.append(out["scorer_result"])
  cases+=1
 assert scorer.aggregate(results)["all_27_cases_pass"] is True
assert cases==3456

# Only after independent checks, compare the proposed proof kernel.
theorem=proposed.prove(ROOT)
assert theorem["status"]=="PASS__UNIVERSAL_PROOF_CANDIDATE_OVER_EXACT_V3_EMITTED_DOMAIN"
assert theorem["identifier_totality_proof"]["identifier_totality"] is True
assert theorem["identifier_totality_proof"]["uniqueness_depends_on_hash_collision_resistance"] is False
assert theorem["add2_exact_orientation_proof"]["candidate_generator_add2_eval_exactly_aligned"] is True
assert theorem["support_rejection_proof"]["all_six_families_wrong_support_rejected"] is True
assert theorem["scope"]["terminal_or_production_cases_generated"]==0
assert theorem["accounting"]["acceptance_credit_delta"]==0

receipt={
 "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V3_TOTAL_EXACT_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__EXACT_BYTE_BOUND__FORCED_TOTAL_DIGEST_TIE__V2_FLOAT_FALSIFIER_REPAIRED__3456_CASE_SWEEP__ZERO_CREDIT",
 "brain_pr":1955,
 "exact_subject_blobs":EXPECTED,
 "forced_all_ranking_digest_tie":{"population_cases":27,"all_pass":True},
 "v2_exact_float_falsifier":{
  "old_pass":False,
  "v3_pass":True,
  "v3_probe_count":new["probe_count"],
  "exact_gold":hidden["gold_terminal_consequence"],
 },
 "nonproduction_falsification":{"populations":populations,"cases":cases,"all_pass":True},
 "production_or_terminal_cases_generated":0,
 "incremental_spend_usd":0,
 "acceptance_credit_delta":0,
 "hard_nonclaims":[
  "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION",
  "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_VERIFIER",
  "SEPARATE_ROOT3_SCOPE_AND_ACCEPTANCE_REDUCTION_REQUIRED",
 ],
}
Path("unknown_domain_v3_total_exact_brain1955_receipt.json").write_text(
 json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(receipt,sort_keys=True))
