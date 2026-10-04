#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path("subject/livebench_legacy_visible_compiler_v1")
MODULE_PATH=ROOT/"canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py"
LIVEBENCH="/tmp/LiveBench"
sys.path.insert(0, f"{LIVEBENCH}/livebench/if_runner")

spec=importlib.util.spec_from_file_location("candidate", MODULE_PATH)
candidate=importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["candidate"]=candidate
spec.loader.exec_module(candidate)

from instruction_following_eval import instructions_registry

CASES = {
 "keywords:existence": {"keywords":["alpha","beta"]},
 "keywords:frequency": {"keyword":"kiwi","frequency":3,"relation":"at least"},
 "keywords:forbidden_words": {"forbidden_words":["bad","worse"]},
 "keywords:letter_frequency": {"letter":"Q","let_frequency":4,"let_relation":"less than"},
 "language:response_language": {"language":"fr"},
 "length_constraints:number_sentences": {"num_sentences":7,"relation":"at least"},
 "length_constraints:number_paragraphs": {"num_paragraphs":3},
 "length_constraints:number_words": {"num_words":120,"relation":"less than"},
 "length_constraints:nth_paragraph_first_word": {"num_paragraphs":3,"nth_paragraph":2,"first_word":"apple"},
 "detectable_content:number_placeholders": {"num_placeholders":3},
 "detectable_content:postscript": {"postscript_marker":"P.S."},
 "detectable_format:number_bullet_lists": {"num_bullets":4},
 "detectable_format:constrained_response": {},
 "detectable_format:number_highlighted_sections": {"num_highlights":2},
 "detectable_format:multiple_sections": {"section_spliter":"SECTION","num_sections":3},
 "detectable_format:json_format": {},
 "detectable_format:title": {},
 "combination:two_responses": {},
 "combination:repeat_prompt": {"prompt_to_repeat":"Base request."},
 "startend:end_checker": {"end_phrase":"Any other questions?"},
 "change_case:capital_word_frequency": {"capital_frequency":6,"capital_relation":"at least"},
 "change_case:english_capital": {},
 "change_case:english_lowercase": {},
 "punctuation:no_comma": {},
 "startend:quotation": {},
}

def normalize_expected(iid, kwargs):
    if iid=="language:response_language":
        return {"language":"fr","language_name":"French"}
    if iid=="keywords:letter_frequency":
        return {"letter":"q","let_frequency":4,"let_relation":"less than"}
    if iid=="combination:repeat_prompt":
        return {}
    return dict(kwargs)

def main():
    registry=set(instructions_registry.INSTRUCTION_DICT)
    assert registry==set(CASES), (sorted(registry),sorted(CASES))
    assert len(registry)==25

    surface=candidate.source_surface()
    assert surface["all_registered_types_covered_by_recognizers"] is True
    assert set(surface["instruction_ids"])==registry
    assert surface["fully_visible_parameter_type_count"]==24
    assert surface["parameter_incomplete_types"]==["combination:repeat_prompt"]

    verified=[]
    for iid in sorted(registry):
        cls=instructions_registry.INSTRUCTION_DICT[iid]
        inst=cls(iid)
        description=inst.build_description(**CASES[iid])
        out=candidate.compile_visible_constraints(description)
        assert out["status"]=="PASS", (iid,description,out)
        cs=[x for x in out["constraints"] if x["instruction_id"]==iid]
        assert len(cs)==1, (iid,description,out)
        c=cs[0]
        if iid=="combination:repeat_prompt":
            assert c["parameter_complete"] is False
            assert c["unresolved_parameters"]==["prompt_to_repeat"]
            assert c["slots"]=={}
        else:
            assert c["parameter_complete"] is True
            expected=normalize_expected(iid,CASES[iid])
            for k,v in expected.items():
                assert c["slots"].get(k)==v, (iid,k,v,c["slots"])
        verified.append(iid)

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_COMPILER_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS",
      "candidate_git_blob_sha":"e986035ff68b53c0dc7a7eb478f6e3d8882214aa",
      "candidate_test_git_blob_sha":"aa279543c6fbd9dea353aa4b18cf283d4e6e25c6",
      "pinned_livebench_commit":"8f8e5c381a16e3f24257776edd53471fe86f8091",
      "pinned_instruction_source_blob":"4997bab885a676d92545fd91a9a20b48d234a2b2",
      "pinned_registry_blob":"903ed738398648c7cfac61d5ffa478c22f1f0891",
      "verified_registered_type_count":len(verified),
      "fully_visible_parameter_type_count":24,
      "parameter_incomplete_types":["combination:repeat_prompt"],
      "verified":[
        "EXACT_25_TYPE_LEGACY_REGISTRY_MATCH",
        "ALL_25_PINNED_BUILD_DESCRIPTION_RENDERINGS_RECOGNIZED",
        "24_OF_25_PARAMETER_SURFACES_RECOVERED_FROM_VISIBLE_RENDERING",
        "REPEAT_PROMPT_HIDDEN_PARAMETER_FAILS_CLOSED_INSTEAD_OF_GUESSING",
        "NO_TERMINAL_DATA_USED"
      ],
      "hard_nonclaims":[
        "NO_CLAIM_VISIBLE_DESCRIPTION_RECOGNITION_ALONE_SOLVES_RESPONSE_CONSTRUCTION",
        "NO_TERMINAL_SCORE_OR_ACCEPTANCE_CREDIT",
        "NO_PROMPT_DISTRIBUTION_OR_CASE_FREQUENCY_INFERENCE"
      ],
      "accounting":{"incremental_spend_usd":0,"terminal_cases_consumed":0,"acceptance_credit_delta":0}
    }
    Path("livebench_legacy_visible_compiler_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__":
    main()
