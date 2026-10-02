from __future__ import annotations
import copy, hashlib, importlib.util, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))

def git_blob_sha(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,expected in manifest["exact_brain_blobs"].items():
    actual=git_blob_sha(ROOT/rel)
    assert actual==expected,(rel,actual,expected)

sys.path.insert(0,str(ROOT))
subprocess.run([
    sys.executable,"-m","unittest",
    "canonical.tests.test_trajectory_failure_typed_ir_v5","-v"
],cwd=ROOT,check=True)

from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as proof

cases=proof.suite_cases()
assert len(cases)==192
scope_cases=[
    c for c in cases
    if "SCOPE" in {k for ks in c["_oracle"]["mechanisms"].values() for k in ks}
]
assert len(scope_cases)>0
scope_failures=[]
for case in scope_cases:
    out=candidate.solve(proof.public_task(case))
    verdict=proof.score_case(case,out)
    if verdict.get("pass") is not True:
        scope_failures.append((case["seed"],verdict))
assert not scope_failures,scope_failures

# Falsification: the alleged intervention-rescue evaluator never executes the
# public trajectory or terminal state. Preserve the hidden token model, destroy
# the task dynamics, and the same repair tokens still receive RESCUED.
counterexamples=[]
for pattern in ("SINGLE","DELAYED","INTERACTION"):
    case=proof.generate_case(77000+len(counterexamples),pattern=pattern,domain="CODE",kind="SCOPE")
    repairs=proof._repair_targets(case["_oracle"])
    base=proof.evaluate_intervention(case,repairs)
    assert base["rescued"] is True
    broken=copy.deepcopy(case)
    broken["task"]["trajectory"]=[]
    broken["task"]["terminal_failed_resources"]=["nonexistent:terminal"]
    mutated=proof.evaluate_intervention(broken,repairs)
    assert mutated["rescued"] is True, mutated
    no_task=copy.deepcopy(case)
    del no_task["task"]
    taskless=proof.evaluate_intervention(no_task,repairs)
    assert taskless["rescued"] is True, taskless
    counterexamples.append({
        "pattern":pattern,
        "repair_count":len(repairs),
        "rescued_after_trajectory_deleted":mutated["rescued"],
        "rescued_without_task":taskless["rescued"],
    })

# Source-level guard: evaluate_intervention is a hidden-token membership check.
import inspect
src=inspect.getsource(proof.evaluate_intervention)
assert 'case["_intervention_model"]' in src
assert '"task"' not in src and "trajectory" not in src and "terminal_failed_resources" not in src

print(json.dumps({
    "status":"PASS__SCOPE_FIRST_CLASS_SUPPORTED__HETEROGENEOUS_RESCUE_CLAIM_FALSIFIED",
    "exact_blob_count":len(manifest["exact_brain_blobs"]),
    "suite_case_count":len(cases),
    "scope_case_count":len(scope_cases),
    "scope_classification_failures":0,
    "rescue_counterexamples":counterexamples,
    "adjudication":{
        "P1_EXPLICIT_SCOPE_FAILURE_CLASS":"SUPPORTED_BY_EXACT_V5_INDEPENDENT_EXECUTION",
        "P1_HETEROGENEOUS_INTERVENTION_RESCUE":"NOT_DISCHARGED__V5_RESCUE_EVALUATOR_IS_ORACLE_DERIVED_TOKEN_MEMBERSHIP_NOT_POST_INTERVENTION_TERMINAL_EXECUTION"
    },
    "capability_credit_delta":0,
    "family_credit_delta":0,
    "execution_authority":False,
    "promotion_authority":False
},indent=2,sort_keys=True))
