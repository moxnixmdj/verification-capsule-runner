from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as generator
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate

ROOT=Path(__file__).resolve().parent
EXPECTED={
"canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
"canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
"canonical/tests/test_unknown_domain_direct_candidate_v2.py":"a56e7fcaa985a1cf1a573166843816c42fa943df",
"canonical/governance/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_PREEXPOSURE_V1.json":"77018decd79e13168d14e2e5ed6ee319fa79d83c",
"canonical/governance/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_QUALIFICATION_V1.json":"a3574e1b8b2c33c0265c018dbb4872410e41de24",
"canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json":"52090daf78d12020af48c1b6ffaea056d9029e1b",
"canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
"canonical/governance/UNKNOWN_DOMAIN_DIRECT_GENERATOR_FREEZE_V2.json":"6bf6042a7a36c12d6d5ebfc5d16ea23ed2befbb6",
"canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
"canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_HARNESS_FREEZE_V1.json":"3e3a87962c13ad4c76621508763fab74df25cb44",
"canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd"}
BEACONS=["FRESH-V2-D-2718281828459045","FRESH-V2-E-1618033988749894","FRESH-V2-F-1414213562373095"]
def blob(data):
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def run_one(beacon):
 p=generator.generate_qualification_fixture_population(beacon=beacon)
 assert p["production"] is False and p["case_count"]==27,p
 results=[]; probes=[]
 for visible,hidden in zip(p["visible_cases"],p["hidden_records"]):
  out=harness.execute_case(candidate_step=candidate.step,case_visible=visible,hidden_record=hidden)
  results.append(out["scorer_result"]); probes.append((out["leaf_id"],out["probe_count"]))
 agg=scorer.aggregate(results)
 assert agg["all_27_cases_pass"] is True,agg
 assert all(n<=2 for leaf,n in probes if leaf==scorer.TRANSFER),probes
 return agg,probes
if __name__=="__main__":
 for rel,expected in EXPECTED.items():
  got=blob((ROOT/rel).read_bytes()); assert got==expected,(rel,got,expected)
 subprocess.check_call(["python","-m","unittest","canonical.tests.test_unknown_domain_direct_candidate_v2","-v"])
 rows=[run_one(x) for x in BEACONS]
 print(json.dumps({"status":"INDEPENDENT_V2_QUALIFICATION_PASS","fresh_populations":3,"fresh_cases":81,
 "all_pass":all(a["all_27_cases_pass"] for a,_ in rows),"max_transfer_probes":max(n for _,p in rows for leaf,n in p if leaf==scorer.TRANSFER),
 "persistent_learned_bytes":0,"production_cases_generated":0},indent=2,sort_keys=True))
