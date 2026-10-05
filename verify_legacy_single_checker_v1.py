#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"legacy_single_checker_v1.py"
LB=pathlib.Path("/tmp/LiveBench")
sys.path.insert(0,str(LB/"livebench"/"if_runner"))

spec=importlib.util.spec_from_file_location("candidate",SUB)
candidate=importlib.util.module_from_spec(spec); spec.loader.exec_module(candidate)

from instruction_following_eval import instructions_registry

cases = {
 "keywords:existence":{"keywords":["cedar","river"]},
 "keywords:frequency":{"keyword":"cedar","frequency":3,"relation":"at least"},
 "keywords:forbidden_words":{"forbidden_words":["cedar","river"]},
 "keywords:letter_frequency":{"letter":"q","let_frequency":3,"let_relation":"at least"},
 "length_constraints:number_sentences":{"num_sentences":3,"relation":"at least"},
 "length_constraints:number_paragraphs":{"num_paragraphs":3},
 "length_constraints:number_words":{"num_words":6,"relation":"at least"},
 "length_constraints:nth_paragraph_first_word":{"num_paragraphs":3,"nth_paragraph":2,"first_word":"cedar"},
 "detectable_content:number_placeholders":{"num_placeholders":3},
 "detectable_content:postscript":{"postscript_marker":"P.S."},
 "detectable_format:number_bullet_lists":{"num_bullets":3},
 "detectable_format:constrained_response":{},
 "detectable_format:number_highlighted_sections":{"num_highlights":3},
 "detectable_format:multiple_sections":{"num_sections":3,"section_spliter":"Section"},
 "detectable_format:json_format":{},
 "detectable_format:title":{},
 "combination:two_responses":{},
 "combination:repeat_prompt":{"prompt_to_repeat":"Explain cedar trees."},
 "startend:end_checker":{"end_phrase":"Any other questions?"},
 "change_case:capital_word_frequency":{"capital_frequency":3,"capital_relation":"at least"},
 "change_case:english_capital":{},
 "change_case:english_lowercase":{},
 "punctuation:no_comma":{},
 "startend:quotation":{},
}
assert set(cases) == set(instructions_registry.INSTRUCTION_DICT) - {"language:response_language"}

results={}
for iid,slots in cases.items():
    checker=instructions_registry.INSTRUCTION_DICT[iid](iid)
    checker.build_description(**slots)
    exact_args=checker.get_instruction_args() or {}
    out=candidate.synthesize(iid,exact_args)
    passed=bool(checker.check_following(out["response"]))
    results[iid]={"pass":passed,"response":out["response"]}
    assert passed,(iid,exact_args,out)

language_results={}
for code in sorted(candidate._LANGUAGE_SAMPLE):
    iid="language:response_language"
    checker=instructions_registry.INSTRUCTION_DICT[iid](iid)
    checker.build_description(language=code)
    out=candidate.synthesize(iid,checker.get_instruction_args())
    passed=bool(checker.check_following(out["response"]))
    language_results[code]=passed
    assert passed,(code,out["response"])

# Exercise the strict comparison branches too.
edge_cases=[
 ("keywords:frequency",{"keyword":"cedar","frequency":3,"relation":"less than"}),
 ("keywords:letter_frequency",{"letter":"q","let_frequency":3,"let_relation":"less than"}),
 ("length_constraints:number_sentences",{"num_sentences":3,"relation":"less than"}),
 ("length_constraints:number_words",{"num_words":6,"relation":"less than"}),
 ("change_case:capital_word_frequency",{"capital_frequency":3,"capital_relation":"less than"}),
]
for iid,slots in edge_cases:
    checker=instructions_registry.INSTRUCTION_DICT[iid](iid)
    checker.build_description(**slots)
    out=candidate.synthesize(iid,checker.get_instruction_args())
    assert checker.check_following(out["response"]),(iid,slots,out)

receipt={
 "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY_SINGLE_CHECKER_PUBLIC_VERIFICATION_V1",
 "status":"PASS",
 "brain_candidate_blob":"6dd4302488b374a45593a83025839cdc5483c789",
 "livebench_commit":"8f8e5c381a16e3f24257776edd53471fe86f8091",
 "instructions_blob":"4997bab885a676d92545fd91a9a20b48d234a2b2",
 "registry_blob":"903ed738398648c7cfac61d5ffa478c22f1f0891",
 "instructions_util_blob":"1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
 "registered_checker_families_verified":len(cases)+1,
 "non_language_families_passed":sum(int(x["pass"]) for x in results.values()),
 "language_codes_verified":len(language_results),
 "language_codes_passed":sum(int(x) for x in language_results.values()),
 "strict_relation_edge_cases_passed":len(edge_cases),
 "terminal_cases_used":0,
 "acceptance_credit":False,
 "multi_checker_composition_proved":False,
}
(ROOT/"legacy_single_checker_v1_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
