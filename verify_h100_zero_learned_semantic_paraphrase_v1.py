from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/H100_ZERO_LEARNED_SEMANTIC_PARAPHRASE_PREEXPOSURE_V1.json":"490ae449877af813d8e8d1f071afb46a5190b02a",
 "canonical/runtime/h100_zero_learned_semantic_paraphrase_v1.py":"db4e836b4104a9b311c2c08ab2d8675bfc0d0760",
 "canonical/tests/test_h100_zero_learned_semantic_paraphrase_v1.py":"9976fd8a160582fc0ce3e1c79bfa496f35b593bf",
 "canonical/governance/H100_ZERO_LEARNED_SEMANTIC_PARAPHRASE_CANDIDATE_V1.json":"34adb64e9c775af6ac5a1507cc15dd8c111dddb5",
}

def blob_sha(data:bytes)->str:
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def load_module():
    p=ROOT/"canonical/runtime/h100_zero_learned_semantic_paraphrase_v1.py"
    s=importlib.util.spec_from_file_location("h100_semantic",p)
    if s is None or s.loader is None:
        raise RuntimeError("IMPORT_SPEC_FAILED")
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

def main():
    for rel,expected in EXPECTED.items():
        actual=blob_sha((ROOT/rel).read_bytes())
        if actual!=expected:
            raise SystemExit(f"BLOB_MISMATCH:{rel}:{actual}!={expected}")
    pre=json.loads((ROOT/"canonical/governance/H100_ZERO_LEARNED_SEMANTIC_PARAPHRASE_PREEXPOSURE_V1.json").read_text())
    cand=json.loads((ROOT/"canonical/governance/H100_ZERO_LEARNED_SEMANTIC_PARAPHRASE_CANDIDATE_V1.json").read_text())
    if pre["status"]!="FROZEN_BEFORE_SEMANTIC_PARAPHRASE_OUTCOMES__PUBLIC_SYNTHETIC_NONTERMINAL__ZERO_CREDIT":
        raise SystemExit("PREEXPOSURE_STATUS_INVALID")
    if len(pre["tasks"])!=10:
        raise SystemExit("PREEXPOSURE_DENOMINATOR_INVALID")
    m=load_module()
    identified=0
    abstained=0
    for task in pre["tasks"]:
        out=m.induce_semantic_roles(task["text"])
        if out["status"]!=task["expected_status"]:
            raise SystemExit("STATUS_MISMATCH:"+task["task_id"])
        if out["inputs"]!=task["expected_inputs"] or out["target"]!=task["expected_target"]:
            raise SystemExit("ROLE_MISMATCH:"+task["task_id"])
        if out["persistent_learned_bytes"]!=0:
            raise SystemExit("LEARNED_BYTES_NONZERO:"+task["task_id"])
        if out["external_frontier_model_calls"]!=0 or out["external_learned_capability_calls"]!=0:
            raise SystemExit("EXTERNAL_LEARNED_PROVIDER_USED:"+task["task_id"])
        if out["status"]=="ROLES_IDENTIFIED":
            identified+=1
        else:
            abstained+=1
    if identified!=8 or abstained!=2:
        raise SystemExit("OUTCOME_COUNTS_INVALID")
    if cand["preexposure"]["git_blob_sha"]!=EXPECTED["canonical/governance/H100_ZERO_LEARNED_SEMANTIC_PARAPHRASE_PREEXPOSURE_V1.json"]:
        raise SystemExit("CANDIDATE_PREEXPOSURE_BINDING_INVALID")
    if cand["accounting"]["persistent_learned_bytes"]!=0:
        raise SystemExit("CANDIDATE_LEARNED_BYTES_NONZERO")
    print(json.dumps({
      "status":"PASS",
      "exact_subject_blobs":True,
      "identified_tasks":identified,
      "mandatory_abstentions":abstained,
      "persistent_learned_bytes":0,
      "external_frontier_model_calls":0,
      "external_learned_capability_calls":0,
      "hard_nonclaim":"FINITE_ONTOLOGY_PASS_IS_NOT_OPEN_WORLD_SEMANTICS"
    },sort_keys=True))

if __name__=="__main__":
    main()
