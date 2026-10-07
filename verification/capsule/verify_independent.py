from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def sha(x):
    return hashlib.sha256(canon(x).encode()).hexdigest()

m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
verified=[]
for rel,expected in m["exact_brain_blobs"].items():
    raw=(ROOT/rel).read_bytes()
    got=git_blob(raw)
    assert got==expected,(rel,got,expected)
    verified.append({"path":rel,"git_blob_sha":got})

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    run, task_contract_sha256, BINDING_SCHEMA, BINDING_VERIFY_SCHEMA
)
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS

def write_json(root:Path,rel:str,doc:dict):
    p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
    raw=canon(doc).encode()
    p.write_bytes(raw)
    return {"path":rel,"git_blob_sha":git_blob_id(raw,object_format="sha1")}

problem={
  "task_id":"v3-self-certification-counterexample",
  "initial_facts":[],
  "target_effects":["OPUS55_PARITY_VERIFIED"],
  "capabilities":[{
    "id":"solve",
    "requires":[],
    "provides":["OPUS55_PARITY_VERIFIED"],
    "cost":1,
    "result_fields":[],
    "action":{
      "type":"verified_policy",
      "verifier_id":"EXACT_JSON_V1",
      "verifier_payload":{"expected":{"answer":42}},
      "effect_contract":{
        "effects":["OPUS55_PARITY_VERIFIED"],
        "verifier_success_condition":SUCCESS_CONDITIONS["EXACT_JSON_V1"]
      }
    }
  }]
}
cap=problem["capabilities"][0]
task_sha=task_contract_sha256(problem)
payload_sha=sha(cap["action"]["verifier_payload"])

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    # SAME PROCESS authors both the subject and the purported independent verification.
    receipt_doc={
      "schema":BINDING_SCHEMA,
      "capability_id":"solve",
      "task_contract_sha256":task_sha,
      "requires":[],
      "verifier_id":"EXACT_JSON_V1",
      "verifier_payload_sha256":payload_sha,
      "verifier_success_condition":SUCCESS_CONDITIONS["EXACT_JSON_V1"],
      "provided_effects":["OPUS55_PARITY_VERIFIED"],
      "pass":True,
      "claim":"BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS"
    }
    rr=write_json(root,"canonical/verification/effect-semantics.json",receipt_doc)
    verify_doc={
      "schema":BINDING_VERIFY_SCHEMA,
      "subject_git_blob_sha":rr["git_blob_sha"],
      "capability_id":"solve",
      "task_contract_sha256":task_sha,
      "requires":[],
      "verifier_id":"EXACT_JSON_V1",
      "verifier_payload_sha256":payload_sha,
      "verifier_success_condition":SUCCESS_CONDITIONS["EXACT_JSON_V1"],
      "provided_effects":["OPUS55_PARITY_VERIFIED"],
      "pass":True,
      "independent_verified":True,
      "implication_semantics_verified":True,
      "independent_verifier_id":"I_TYPED_THIS_MYSELF"
    }
    vr=write_json(root,"canonical/verification/effect-semantics-verify.json",verify_doc)
    cap["effect_semantics_binding"]={"receipt":rr,"verification":vr}
    out=run(
      problem,
      proposal_packets={"solve":[{"candidate":{"answer":42}}]},
      repo_root=root,
    )

accepted=(
    out.get("pass") is True
    and out.get("status")=="SOLVED__ALL_TARGET_EFFECTS_INDEPENDENTLY_SEMANTICS_BOUND"
    and out.get("run_verified_target_effects")==["OPUS55_PARITY_VERIFIED"]
)
assert accepted, out
result={
  "schema":"PROJECT_BRAIN_V3_REPOSITORY_SELF_CERTIFICATION_FALSIFICATION_RESULT_V1",
  "status":"COUNTEREXAMPLE_CONFIRMED",
  "v3_accepted_repo_authored_independence_claim":True,
  "external_independent_verifier_used":False,
  "target_effect_minted":"OPUS55_PARITY_VERIFIED",
  "exact_brain_blobs":verified,
  "counterexample":{
    "subject_and_verification_authored_by_same_process":True,
    "verification_field_independent_verified":True,
    "verification_field_independent_verifier_id":"I_TYPED_THIS_MYSELF",
    "v3_result_status":out.get("status")
  },
  "consequence":"V3_REPOSITORY_AUTHORED_EFFECT_SEMANTICS_VERIFICATION_IS_NOT_AN_INDEPENDENTLY_AUTHENTICATED_BOUNDARY",
  "hard_nonclaims":m["hard_nonclaims"]
}
(ROOT.parent/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
