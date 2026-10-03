#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, shutil, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subjects"
FILES={
"canonical/governance/RETRIEVAL_V6_OPEN_WORLD_HARDENING_ACTIVATION_V1.json":"4398fee2d6d0a8a62ca7209852c961bc1fca1c7c",
"canonical/runtime/evidence_omniretrieval_planner_v2.py":"959d14f11859467d7d1f010f588e0bad99dd667d",
"canonical/runtime/retrieval_monotonic_candidate_ledger_v1.py":"c52a269b599d2b2f9e0e018120a3377165629cc7",
"canonical/runtime/retrieval_bounded_enumerator_v1.py":"99b1f20ddd4b8dcceea19cfc57a1c0c5999f4632",
"canonical/runtime/retrieval_conditional_novelty_scheduler_v1.py":"025559f285952fa79f1db3b04f1f40cf6927b77f",
"canonical/runtime/retrieval_adversarial_universe_v2.py":"d545a453cedfdd0b8318189c4164232b592addb7",
"canonical/runtime/retrieval_open_world_controller_v6.py":"c205b31ab2f850973aa52cbf709f9e770ee8dacc",
"canonical/tests/test_retrieval_v6_open_world_hardening.py":"1048843c58631f11e83a8521e2509c1d30f4f6bc",
}
def blob(raw:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

work=ROOT/"work_v6"
if work.exists(): shutil.rmtree(work)
for rel,sha in FILES.items():
 src=SUB/rel.replace("/","__")
 raw=src.read_bytes()
 assert blob(raw)==sha,(rel,blob(raw),sha)
 dst=work/rel
 dst.parent.mkdir(parents=True,exist_ok=True)
 dst.write_bytes(raw)
for p in (work/"canonical",work/"canonical/runtime",work/"canonical/tests"):
 (p/"__init__.py").write_text("",encoding="utf-8")

act=json.loads((work/"canonical/governance/RETRIEVAL_V6_OPEN_WORLD_HARDENING_ACTIVATION_V1.json").read_text())
assert act["verified_local_candidate_results"]["generated_adversarial_cases"]==291
assert act["verified_local_candidate_results"]["v6_recall_on_declared_finite_fixture_universe"]==1.0
assert act["verified_local_candidate_results"]["lexical_only_recall_on_declared_fixture_universe"]<1.0
assert "ZERO_YIELD_ROUNDS_NEVER_PROVE_COMPLETENESS" in act["mandatory_v6_invariants"]
assert "NO_OPEN_WORLD_RETRIEVAL_COMPLETENESS_CLAIM" in act["hard_nonclaims"]

env=dict(__import__("os").environ)
env["PYTHONPATH"]=str(work)
p=subprocess.run([sys.executable,"-m","unittest","discover","-s",str(work/"canonical/tests"),"-p","test_retrieval_v6_open_world_hardening.py","-v"],env=env,text=True,capture_output=True)
print(p.stdout);print(p.stderr)
assert p.returncode==0,p.returncode

sys.path.insert(0,str(work))
from canonical.runtime.retrieval_adversarial_universe_v2 import run
out=run()
assert out["status"]=="PASS",out
assert out["pairwise_complete"] is True
assert out["generated_case_count"]==291
assert out["v6_finite_fixture_recall"]==1.0
assert out["lexical_only_recall"]<1.0
assert out["outside_scope_correct_state"]=="UNKNOWN"
assert out["open_world_completeness_claim_authorized"] is False
print("RETRIEVAL_V6_OPEN_WORLD_HARDENING_VERIFIED")
print(json.dumps({"tests":"9/9_PASS","generated_cases":out["generated_case_count"],"pairwise_complete":True,"lexical_only_recall":out["lexical_only_recall"],"v6_finite_fixture_recall":1.0,"outside_scope_state":"UNKNOWN","zero_credit":True},sort_keys=True))
