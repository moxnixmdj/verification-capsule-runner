from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json":"1d877629399aef04e12ad66b1e365aecb0500cd7",
 "canonical/governance/H100_OEWN_REAL_LEXICAL_PREEXPOSURE_V1.json":"e98dc723dd9ff5cdc75a45e90efc0ba1ccac8412",
 "canonical/runtime/h100_oewn_lexical_acquisition_v1.py":"a692634a25718e7987786c8b533ee23a3e2fe161",
 "canonical/tests/test_h100_oewn_lexical_acquisition_v1.py":"abbc8395692024ab73a6f58f87c035b309c89a3d",
}
FORBIDDEN_SYNSET_IDS=(
 "03578305-n","05836008-n","06777755-n","07279488-n",
 "00916463-n","03292089-n","03866402-n","07279593-n","13780885-n",
 "06344278-n","06756201-n","07307418-n","11430739-n",
)

def blob_sha(data:bytes)->str:
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def load_runtime():
    p=ROOT/"canonical/runtime/h100_oewn_lexical_acquisition_v1.py"
    spec=importlib.util.spec_from_file_location("h100_oewn",p)
    if spec is None or spec.loader is None:
        raise SystemExit("IMPORT_SPEC_FAILED")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    for rel,expected in EXPECTED.items():
        actual=blob_sha((ROOT/rel).read_bytes())
        if actual!=expected:
            raise SystemExit(f"BLOB_MISMATCH:{rel}:{actual}!={expected}")

    runtime_text=(ROOT/"canonical/runtime/h100_oewn_lexical_acquisition_v1.py").read_text().lower()
    for sid in FORBIDDEN_SYNSET_IDS:
        if sid in runtime_text:
            raise SystemExit("SOURCE_SYNSET_HARDCODED_IN_RUNTIME:"+sid)

    knowledge=json.loads((ROOT/"canonical/governance/H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json").read_text())
    pre=json.loads((ROOT/"canonical/governance/H100_OEWN_REAL_LEXICAL_PREEXPOSURE_V1.json").read_text())
    if knowledge["source"]["name"]!="Open English WordNet" or knowledge["source"]["edition"]!="2025":
        raise SystemExit("SOURCE_IDENTITY_INVALID")
    if len(pre["tasks"])!=9:
        raise SystemExit("PREEXPOSURE_DENOMINATOR_INVALID")

    mod=load_runtime()
    passed=0
    abstained=0
    for task in pre["tasks"]:
        out=mod.resolve_lexical_role(task["cue"],task["context"],knowledge)
        if out["status"]!=task["expected_status"] or out["role"]!=task["expected_role"]:
            raise SystemExit("PREEXPOSURE_MISMATCH:"+task["task_id"])
        if out["persistent_learned_bytes"]!=0:
            raise SystemExit("LEARNED_BYTES_NONZERO:"+task["task_id"])
        if out["external_frontier_model_calls"]!=0 or out["external_learned_capability_calls"]!=0:
            raise SystemExit("EXTERNAL_LEARNED_PROVIDER_USED:"+task["task_id"])
        if out["status"]=="ROLE_IDENTIFIED":
            passed+=1
        else:
            abstained+=1

    fresh_input=mod.resolve_lexical_role(
        "comment",
        "users supplied a statement of personal belief and opinion as additional information",
        knowledge,
    )
    if fresh_input["status"]!="ROLE_IDENTIFIED" or fresh_input["role"]!="INPUT" or fresh_input["selected_synsets"]!=["06777755-n"]:
        raise SystemExit("FRESH_REAL_POLYSEMY_INPUT_CHALLENGE_FAILED")

    fresh_reject=mod.resolve_lexical_role(
        "comment",
        "the critic added an explanation and illustration to textual material",
        knowledge,
    )
    if fresh_reject["status"]!="ABSTAIN_LEXICAL_SENSE_UNSUPPORTED" or fresh_reject["role"] is not None:
        raise SystemExit("FRESH_REAL_POLYSEMY_REJECTION_CHALLENGE_FAILED")

    print(json.dumps({
      "status":"PASS",
      "exact_subject_blobs":True,
      "preexposed_role_identified":passed,
      "preexposed_abstentions":abstained,
      "fresh_real_polysemy_input_challenge":"PASS",
      "fresh_real_polysemy_rejection_challenge":"PASS",
      "persistent_learned_bytes":0,
      "external_frontier_model_calls":0,
      "external_learned_capability_calls":0,
      "hard_nonclaim":"BOUNDED_PINNED_OEWN_PASS_IS_NOT_OPEN_WORLD_LEXICAL_COMPLETENESS"
    },sort_keys=True))

if __name__=="__main__":
    main()
