#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import inspect
import itertools
import json
from fractions import Fraction
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_v4_universal_proof_v1 as proposed

ROOT=Path(__file__).resolve().parents[1]

EXPECTED={
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":"8b855851b8a0fec3a0811c5033cc4ea6d2436954",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/runtime/unknown_domain_direct_v4_universal_proof_v1.py":"72bbed393ac1bcaccb4cf33cd37835662c421f6c",
}


def blob(path:Path)->str:
 b=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


# 1. Content-bind every load-bearing byte.
got={rel:blob(ROOT/rel) for rel in EXPECTED}
assert got==EXPECTED, {"expected":EXPECTED,"got":got}


# 2. Independently prove the permutation construction does not rely on digest
# uniqueness. Exhaust all possible Fisher-Yates choice paths for n<=7. This is
# not statistical: each path represents arbitrary draw residues at each step.
def abstract_perm(n:int, choices:tuple[int,...])->tuple[int,...]:
 out=list(range(n))
 k=0
 for i in range(n-1,0,-1):
  j=choices[k]
  k+=1
  assert 0<=j<=i
  out[i],out[j]=out[j],out[i]
 return tuple(out)

exhaustive_paths=0
for n in range(1,8):
 domains=[range(i+1) for i in range(n-1,0,-1)]
 for choices in itertools.product(*domains):
  p=abstract_perm(n,choices)
  assert len(p)==n
  assert set(p)==set(range(n))
  exhaustive_paths+=1
assert exhaustive_paths==5913, exhaustive_paths

# Actual implementation on every semantic size, adversarial digest/secret values.
for n in (2,3,4,12,15):
 for secret in (b"\x00"*32,b"\xff"*32,b"A"*32,b"B"*32,bytes(range(32))):
  for beacon in ("B"*16,"TOTALITY-EDGE-00000001","TOTALITY-EDGE-99999999"):
   p=g3._perm(secret,beacon,f"independent|n={n}",n)
   assert len(p)==n and set(p)==set(range(n))


# 3. Independently derive strict transfer margins.
D0=Fraction(19,4)
D1=Fraction(25,4)
MIN=Fraction(1,4)
MAX=Fraction(7,2)
assert Fraction(3,5)*D0==Fraction(57,20)
assert D0==Fraction(19,4)
sat_gap=Fraction(7,10)*D0/Fraction(121,1)
assert float(sat_gap)>4.5e-9
assert -MAX+D0==Fraction(5,4)>0
assert D0-Fraction(11,5)==Fraction(51,20)>0
add2_gaps=(
 D0-(MAX-MIN),
 D1,
 D0,
 D1-(MAX-MIN),
 D0+D1,
)
assert min(add2_gaps)==Fraction(3,2)
assert harness.MAX_TRANSFER_PROBES==2


# 4. Independently bind the exact-float repair. ADD2 indices 4/10 have visible
# nonzero role signatures that uniquely distinguish r0 from r1.
for index in (4,10):
 r0=tuple(-1 if (j+index)%2==0 else 1 for j in range(3))
 r1=tuple(-1 if (j+index+1)%3==0 else 1 for j in range(3))
 assert r0==c3.ADD2_R0_SIG==(-1,1,-1)
 assert r1==c3.ADD2_R1_SIG==(1,-1,1)
 assert r0!=r1

# Confirm both gold and candidate execute bias+r0+r1 in the same left-to-right
# Python expression after V3 restores the true role orientation.
gen_src="".join(inspect.getsource(g1._eval).split())
cand_src="".join(inspect.getsource(c1._program_eval).split())
assert 'returnfloat(p["bias"])+float(role_values["r0"])+float(role_values["r1"])' in gen_src
assert 'return_finite(params["bias"],"bias")+_finite(role_values["r0"],"r0")+_finite(role_values["r1"],"r1")' in cand_src


# 5. Find an exact V2 one-ulp failure under the structurally-total generator,
# then require V3 to repair the exact same packet. No production entrypoint used.
counterexample=None
secret=hashlib.sha256(b"INDEPENDENT-V4-FLOAT-SEARCH").digest()
for k in range(1024):
 beacon=f"INDEPENDENT-V4-FLOAT-{k:04d}-BEACON"
 for index in (4,10):
  visible,hidden=g3._transfer_case(secret,beacon,index,namespace="V4VERIFY")
  bad=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
  if not bad["scorer_result"]["pass"] and "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in bad["scorer_result"]["errors"]:
   good=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
   assert good["scorer_result"]["pass"], good["scorer_result"]
   assert good["candidate_terminal_action"]["terminal_consequence"]==hidden["gold_terminal_consequence"]
   counterexample={
    "beacon":beacon,
    "index":index,
    "v2":bad["candidate_terminal_action"]["terminal_consequence"],
    "gold":hidden["gold_terminal_consequence"],
    "v3_probe_count":good["probe_count"],
   }
   break
 if counterexample:
  break
assert counterexample is not None, "EXPECTED_V2_EXACT_FLOAT_COUNTEREXAMPLE_NOT_FOUND"


# 6. Large deterministic nonproduction falsification sweep through the exact
# combined route. This is regression evidence, not the universality argument.
populations=256
cases=0
for i in range(populations):
 packet=g3.generate_qualification_fixture_population(
  beacon=f"INDEPENDENT-V4-TOTAL-EXACT-{i:04d}"
 )
 assert packet["production"] is False
 assert packet["case_count"]==27
 rows=[]
 for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
  out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
  assert out["scorer_result"]["pass"], {
   "population":i,
   "case_id":visible["case_id"],
   "errors":out["scorer_result"].get("errors"),
  }
  rows.append(out["scorer_result"])
  cases+=1
 assert scorer.aggregate(rows)["all_27_cases_pass"] is True
assert cases==6912


# 7. Only after independent derivations/falsification, compare proposed theorem.
theorem=proposed.prove(ROOT)
assert theorem["status"]=="PASS__UNIVERSAL_OVER_ALL_VALID_TOTALIZED_V3_INPUTS_WITH_EXACT_FLOAT_V3_CANDIDATE"
assert theorem["identifier_totality_proof"]["hash_collision_resistance_required"] is False
assert theorem["identifier_totality_proof"]["accepted_secret_or_beacon_rejected_due_identifier_collision"] is False
assert theorem["transfer_proof"]["add2_exact_float_order_repaired"] is True
assert theorem["scope"]["terminal_or_production_cases_generated"]==0
assert theorem["accounting"]["acceptance_credit_delta"]==0

receipt={
 "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V4_TOTAL_EXACT_INDEPENDENT_VERIFICATION_V1",
 "status":"PASS__INDEPENDENT_CONTENT_BOUND_TOTALITY_EXACTNESS_AND_6912_CASE_FALSIFICATION__ZERO_CREDIT",
 "brain_pr":1934,
 "exact_subject_blobs":EXPECTED,
 "fisher_yates_exhaustive_choice_paths_n_le_7":exhaustive_paths,
 "identifier_totality_depends_on_hash_collision_resistance":False,
 "v2_exact_float_counterexample":counterexample,
 "nonproduction_falsification":{"populations":populations,"cases":cases,"all_pass":True},
 "production_or_terminal_cases_generated":0,
 "acceptance_credit_delta":0,
 "hard_nonclaims":[
  "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION",
  "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_VERIFIER",
  "SEPARATE_SCOPE_AND_ACCEPTANCE_REDUCTION_REQUIRED"
 ],
}
Path("unknown_domain_v4_total_exact_receipt.json").write_text(
 json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(receipt,sort_keys=True))
