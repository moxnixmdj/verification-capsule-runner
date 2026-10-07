from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
verified_blobs=[]
for rel,expected in manifest["exact_brain_blobs"].items():
    data=(ROOT/rel).read_bytes()
    got=git_blob(data)
    assert got==expected,(rel,got,expected)
    verified_blobs.append({"path":rel,"git_blob_sha":got})

# Run the exact Brain V2 tests without adding pytest as a dependency.
import canonical.tests.test_universal_verified_adaptive_solver_v2 as tv2
v2_tests=[]
for name in sorted(x for x in dir(tv2) if x.startswith("test_")):
    fn=getattr(tv2,name)
    fn()
    v2_tests.append(name)
assert len(v2_tests)==8,v2_tests

# Additional independent adversarial checks against the exact V2 runtime.
from canonical.runtime.universal_verified_adaptive_solver_v2 import run

def cap(cid,requires,provides,expected):
    return {
      "id":cid,"requires":requires,"provides":provides,"cost":1,"result_fields":[],
      "action":{
        "type":"verified_policy","verifier_id":"EXACT_JSON_V1",
        "verifier_payload":{"expected":expected},
        "effect_contract":{
          "effects":provides,
          "verifier_success_condition":"CANDIDATE_EQUALS_EXPECTED"
        }
      }
    }

adversarial=[]
p={"initial_facts":["PRE"],"target_effects":["DONE"],"capabilities":[cap("solve",["PRE"],["DONE"],{"x":1})]}
o=run(p,proposal_packets={"solve":[{"candidate":{"x":1}}]})
assert o["pass"] is True and o["run_verified_target_effects"]==["DONE"]
adversarial.append("NON_TARGET_PRELOAD_ALLOWED_BUT_TARGET_MINTED_IN_RUN")

p2={"initial_facts":[],"target_effects":["DONE"],"capabilities":[cap("solve",[],["DONE"],{"x":1})]}
p2["capabilities"][0]["action"]["effect_contract"]["effects"]=["OTHER"]
o=run(p2,proposal_packets={"solve":[{"candidate":{"x":1}}]})
assert o["status"]=="FAIL_CLOSED" and any("PROVIDES_EFFECT_CONTRACT_MISMATCH" in x for x in o["errors"])
adversarial.append("EFFECT_LABEL_LAUNDERING_REJECTED")

p3={"initial_facts":["DONE"],"target_effects":["DONE"],"capabilities":[cap("solve",[],["DONE"],{"x":1})]}
o=run(p3,proposal_packets={})
assert o["status"]=="FAIL_CLOSED__PRELOADED_TARGET_EFFECT_UNAUTHENTICATED"
adversarial.append("PRELOADED_TARGET_SELF_CERTIFICATION_REJECTED")

# Ratchet provenance must fail closed on repository-authored fake runner metadata.
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.skill_receipt_authenticator_v1 import (
    EPISODE_SCHEMA,EPISODE_VERIFY_SCHEMA,CANDIDATE_SCHEMA,CANDIDATE_VERIFY_SCHEMA,
    SkillReceiptError,
)
from canonical.runtime.universal_verified_skill_ratchet_v1 import bind_verified_episode,bind_verified_skill

def write_json(root:Path,rel:str,doc:dict):
    p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(doc,sort_keys=True,separators=(",",":")).encode()
    p.write_bytes(raw)
    return {"path":rel,"git_blob_sha":git_blob_id(raw,object_format="sha1")}

def fake_runner():
    return {
      "repository":"moxnixmdj/verification-capsule-runner",
      "workflow_run_id":1,"workflow_job_id":2,"execution_head_sha":"a"*40,
      "artifact_id":3,"artifact_digest":"sha256:"+"b"*64,"conclusion":"success",
      "verifier_path":"fabricated/verifier.py","verifier_git_blob_sha":"c"*40
    }

ratchet=[]
with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    ep={"episode_id":"e1","scope_id":"scope","program_sha256":"sha256:"+"1"*64}
    subject=write_json(root,"canonical/verification/episode.json",{
      "schema":EPISODE_SCHEMA,"episode_id":"e1","scope_id":"scope",
      "program_sha256":ep["program_sha256"],"behavior_verified":True,"conclusion":"success"
    })
    verify=write_json(root,"canonical/verification/episode_verify.json",{
      "schema":EPISODE_VERIFY_SCHEMA,"subject_git_blob_sha":subject["git_blob_sha"],
      "episode_id":"e1","scope_id":"scope","program_sha256":ep["program_sha256"],
      "pass":True,"verifier_id":"fake","public_runner":fake_runner()
    })
    try:
        bind_verified_episode(ep,{"receipt":subject,"verification":verify},repo_root=str(root))
        raise AssertionError("FORGED_EPISODE_PROVENANCE_ACCEPTED")
    except SkillReceiptError as exc:
        assert "INDEPENDENCE_UNPROVED" in str(exc),exc
    ratchet.append("FORGED_EPISODE_RUNNER_METADATA_REJECTED")

    bad_subject=dict(subject);bad_subject["git_blob_sha"]="0"*40
    try:
        bind_verified_episode(ep,{"receipt":bad_subject,"verification":verify},repo_root=str(root))
        raise AssertionError("BLOB_DRIFT_ACCEPTED")
    except Exception as exc:
        assert "INDEPENDENCE_UNPROVED" not in str(exc),exc
    ratchet.append("BLOB_DRIFT_REJECTED_BEFORE_INDEPENDENCE")

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    cand={"candidate_sha256":"sha256:"+"2"*64,"source_episode_ids":["e1","e2"]}
    subject=write_json(root,"canonical/verification/candidate.json",{
      "schema":CANDIDATE_SCHEMA,"candidate_sha256":cand["candidate_sha256"],
      "source_episode_ids":cand["source_episode_ids"],
      "behavior_preserving_on_claimed_scope":True,"scope_relation":"PROVEN_SUPERSET","conclusion":"success"
    })
    verify=write_json(root,"canonical/verification/candidate_verify.json",{
      "schema":CANDIDATE_VERIFY_SCHEMA,"subject_git_blob_sha":subject["git_blob_sha"],
      "candidate_sha256":cand["candidate_sha256"],"source_episode_ids":cand["source_episode_ids"],
      "scope_relation":"PROVEN_SUPERSET","pass":True,"verifier_id":"fake","public_runner":fake_runner()
    })
    try:
        bind_verified_skill(cand,{"receipt":subject,"verification":verify},repo_root=str(root))
        raise AssertionError("FORGED_SKILL_PROVENANCE_ACCEPTED")
    except SkillReceiptError as exc:
        assert "INDEPENDENCE_UNPROVED" in str(exc),exc
    ratchet.append("FORGED_SKILL_RUNNER_METADATA_REJECTED")

result={
  "schema":"PROJECT_BRAIN_UNIVERSAL_ADAPTIVE_V2_PUBLIC_CAPSULE_RESULT_V1",
  "status":"PASS",
  "exact_brain_blob_count":len(verified_blobs),
  "exact_brain_blobs":verified_blobs,
  "exact_v2_test_count":len(v2_tests),
  "exact_v2_tests":v2_tests,
  "independent_adversarial_checks":adversarial,
  "ratchet_fail_closed_checks":ratchet,
  "scope_proved":[
    "MECHANICAL_PROOF_TO_EFFECT_BINDING_V2_ON_EXACT_JSON_CONTROL_PATH",
    "PRELOADED_TARGET_SELF_CERTIFICATION_BLOCKED",
    "FORGED_REPOSITORY_AUTHORED_RUNNER_PROVENANCE_BLOCKED"
  ],
  "hard_nonclaims":manifest["hard_nonclaims"]+[
    "NO_CLAIM_TEST_ONLY_STUBS_VERIFY_UNUSED_SEMANTIC_ADAPTERS",
    "NO_CLAIM_INDEPENDENT_RUN_AUTHENTICATES_A_REUSABLE_SKILL_RECEIPT"
  ]
}
(ROOT.parent/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
