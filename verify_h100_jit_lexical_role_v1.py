from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/H100_JIT_LEXICAL_RAW_KNOWLEDGE_V1.json":"611d6d1ed968c5b56b72d1949e16fcb4474b2056",
 "canonical/governance/H100_JIT_LEXICAL_ROLE_PREEXPOSURE_V1.json":"78a3b94bce549b67a6dda3d316dea96c25aca7e4",
 "canonical/runtime/h100_jit_lexical_role_v1.py":"d751354ae8ef8dfbe720f4837d4ac6c0849f7a9a",
 "canonical/tests/test_h100_jit_lexical_role_v1.py":"353afbdbe247451327f5e3811ff08e1885604788",
}
FORBIDDEN_RUNTIME_CUES=("cue_a","cue_b","cue_c","cue_d","cue_e","cue_f","cue_ambiguous","cue_unknown")

def blob_sha(data:bytes)->str:
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def load_runtime():
    p=ROOT/"canonical/runtime/h100_jit_lexical_role_v1.py"
    s=importlib.util.spec_from_file_location("h100_jit_lexical",p)
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

    runtime_text=(ROOT/"canonical/runtime/h100_jit_lexical_role_v1.py").read_text().lower()
    for cue in FORBIDDEN_RUNTIME_CUES:
        if cue in runtime_text:
            raise SystemExit("TASK_CUE_HARDCODED_IN_RUNTIME:"+cue)

    pre=json.loads((ROOT/"canonical/governance/H100_JIT_LEXICAL_ROLE_PREEXPOSURE_V1.json").read_text())
    knowledge=json.loads((ROOT/"canonical/governance/H100_JIT_LEXICAL_RAW_KNOWLEDGE_V1.json").read_text())
    if len(pre["tasks"])!=5:
        raise SystemExit("PREEXPOSURE_DENOMINATOR_INVALID")

    m=load_runtime()
    identified=0
    abstained=0
    for task in pre["tasks"]:
        out=m.induce_roles(task["clauses"],knowledge)
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
    if identified!=3 or abstained!=2:
        raise SystemExit("OUTCOME_COUNTS_INVALID")

    challenger={
      "anchors":{"input":"input","target":"output"},
      "edges":[
        ["fresh_semantic_left","left_bridge"],["left_bridge","input"],
        ["fresh_semantic_right","right_bridge"],["right_bridge","output"],
      ],
    }
    out=m.induce_roles([
      {"cue":"fresh_semantic_right","fields":["answer"]},
      {"cue":"fresh_semantic_left","fields":["u","v"]},
    ],challenger)
    if out["status"]!="ROLES_IDENTIFIED" or out["inputs"]!=["u","v"] or out["target"]!="answer":
        raise SystemExit("INDEPENDENT_FRESH_TOKEN_CHALLENGE_FAILED")

    print(json.dumps({
      "status":"PASS",
      "exact_subject_blobs":True,
      "preexposed_identified":identified,
      "preexposed_abstentions":abstained,
      "fresh_token_challenge":"PASS",
      "persistent_learned_bytes":0,
      "external_frontier_model_calls":0,
      "external_learned_capability_calls":0,
      "hard_nonclaim":"RAW_LEXICAL_GRAPH_RESOLUTION_DOES_NOT_PROVE_OPEN_WORLD_GRAPH_ACQUISITION"
    },sort_keys=True))

if __name__=="__main__":
    main()
