#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "capsules/tb_science_rank20_20261010_v1/RANK20_CLAIM_V3_BEHAVIOR_SNAPSHOT.json"
EFFECTIVE = "execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V2.json"
BASE_SHA = "9012d4bf1c84e157cdfa27ec04fd1a5afd7c78c7"
EFFECTIVE_SHA = "dc20b4ef740eaeb6741c834d9c74634653c69193"
CLAIM_BINDING = ("capsules/tb_science_rank20_20261010_v1/RANK20_LOGICAL_ATTEMPT_CLAIM_BINDING_V3.json","59fa5616f1754f90ded1c3b30cb53c98b4348cee")
HELPER = ("execution_guard/rank20_claim_bound_identity_v1.py","d5e5207a41a5cf0983a0078b1d996bffc9e7a01c")

def blob(rel: str) -> str:
    raw=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(rel: str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def main() -> int:
    assert blob(BASE)==BASE_SHA
    assert blob(EFFECTIVE)==EFFECTIVE_SHA
    base=load(BASE); effective=load(EFFECTIVE)
    for key in ("schema","date","scope","slot_id","task_digest","workflow_path","behavior"):
        assert effective[key]==base[key], key
    old=base["runtime_bindings"]; new=effective["runtime_bindings"]
    added=set(new)-set(old)
    assert added=={"logical_attempt_claim_binding","logical_attempt_binding_helper"}, added
    assert not (set(old)-set(new))
    for key,row in old.items():
        assert new[key]==row, key
    assert (new["logical_attempt_claim_binding"]["path"],new["logical_attempt_claim_binding"]["git_blob_sha"])==CLAIM_BINDING
    assert (new["logical_attempt_binding_helper"]["path"],new["logical_attempt_binding_helper"]["git_blob_sha"])==HELPER
    assert blob(CLAIM_BINDING[0])==CLAIM_BINDING[1]
    assert blob(HELPER[0])==HELPER[1]
    # No executable/runtime semantics changed: only proof-plane bindings and status text were added.
    assert effective["behavior"]==base["behavior"]
    print("PASS__RANK20_CLAIM_V3_BEHAVIOR_PROOF_ONLY_REFINEMENT__NO_REAUTHORIZATION")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
