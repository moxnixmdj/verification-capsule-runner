#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

UPSTREAM="/tmp/LiveBench/livebench/if_runner"
sys.path.insert(0, UPSTREAM)

from instruction_following_eval import instructions_registry, instructions_util

SUBJECT=pathlib.Path(__file__).parent / "livebench_legacy25_single_checker_solver_v1.py"
spec=importlib.util.spec_from_file_location("subject_solver", SUBJECT)
solver=importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(solver)

BASE="Explain the topic briefly."

cases = [
 ("keywords:existence", {"keywords":["alpha","beta"]}),
 ("keywords:frequency", {"keyword":"alpha","frequency":3,"relation":"at least"}),
 ("keywords:frequency", {"keyword":"alpha","frequency":2,"relation":"less than"}),
 ("keywords:forbidden_words", {"forbidden_words":["alpha","beta"]}),
 ("keywords:letter_frequency", {"letter":"q","let_frequency":4,"let_relation":"at least"}),
 ("keywords:letter_frequency", {"letter":"q","let_frequency":1,"let_relation":"less than"}),
 ("length_constraints:number_sentences", {"num_sentences":3,"relation":"at least"}),
 ("length_constraints:number_sentences", {"num_sentences":2,"relation":"less than"}),
 ("length_constraints:number_paragraphs", {"num_paragraphs":3}),
 ("length_constraints:number_words", {"num_words":7,"relation":"at least"}),
 ("length_constraints:number_words", {"num_words":3,"relation":"less than"}),
 ("length_constraints:nth_paragraph_first_word", {"num_paragraphs":3,"nth_paragraph":2,"first_word":"alpha"}),
 ("detectable_content:number_placeholders", {"num_placeholders":3}),
 ("detectable_content:postscript", {"postscript_marker":"P.S."}),
 ("detectable_content:postscript", {"postscript_marker":"P.P.S"}),
 ("detectable_format:number_bullet_lists", {"num_bullets":3}),
 ("detectable_format:constrained_response", {}),
 ("detectable_format:number_highlighted_sections", {"num_highlights":3}),
 ("detectable_format:multiple_sections", {"section_spliter":"Section","num_sections":3}),
 ("detectable_format:multiple_sections", {"section_spliter":"SECTION","num_sections":2}),
 ("detectable_format:json_format", {}),
 ("detectable_format:title", {}),
 ("combination:two_responses", {}),
 ("combination:repeat_prompt", {"prompt_to_repeat":BASE}),
 ("startend:end_checker", {"end_phrase":"Any other questions?"}),
 ("startend:end_checker", {"end_phrase":"Is there anything else I can help with?"}),
 ("startend:quotation", {}),
 ("change_case:capital_word_frequency", {"capital_frequency":3,"capital_relation":"at least"}),
 ("change_case:capital_word_frequency", {"capital_frequency":2,"capital_relation":"less than"}),
 ("change_case:english_capital", {}),
 ("change_case:english_lowercase", {}),
 ("punctuation:no_comma", {}),
]

registry_ids=set(instructions_registry.INSTRUCTION_DICT)
assert registry_ids==set(solver.IDS), (sorted(registry_ids-set(solver.IDS)), sorted(set(solver.IDS)-registry_ids))
assert len(registry_ids)==25

results=[]
for iid, kwargs in cases:
    cls=instructions_registry.INSTRUCTION_DICT[iid]
    inst=cls(iid)
    desc=inst.build_description(**kwargs)
    prompt=(BASE+" "+desc).strip()
    got=solver.solve(prompt)
    ok=False
    error=None
    try:
        ok=(got.get("status")=="PASS_CANDIDATE_SINGLE_CHECKER_WITNESS"
            and got.get("checker_id")==iid
            and bool(inst.check_following(got.get("response",""))))
    except Exception as e:
        error=repr(e)
    results.append({
        "instruction_id":iid,
        "kwargs":kwargs,
        "description":desc,
        "solver_status":got.get("status"),
        "recognized":got.get("recognized_checker_ids") or [got.get("checker_id")],
        "response":got.get("response"),
        "checker_pass":ok,
        "error":error,
    })

# Exhaust the language map because this route intentionally relies on the pinned
# checker's documented LangDetectException=>True behavior for no-feature text.
for code in instructions_util.LANGUAGE_CODES:
    iid="language:response_language"
    cls=instructions_registry.INSTRUCTION_DICT[iid]
    inst=cls(iid)
    desc=inst.build_description(language=code)
    prompt=(BASE+" "+desc).strip()
    got=solver.solve(prompt)
    try:
        ok=(got.get("status")=="PASS_CANDIDATE_SINGLE_CHECKER_WITNESS"
            and got.get("checker_id")==iid
            and bool(inst.check_following(got.get("response",""))))
        error=None
    except Exception as e:
        ok=False; error=repr(e)
    results.append({
        "instruction_id":iid,
        "kwargs":{"language":code},
        "description":desc,
        "solver_status":got.get("status"),
        "recognized":got.get("recognized_checker_ids") or [got.get("checker_id")],
        "response":got.get("response"),
        "checker_pass":ok,
        "error":error,
    })

failed=[x for x in results if not x["checker_pass"]]
summary={
 "schema":"LIVEBENCH_LEGACY25_SINGLE_CHECKER_SOLVER_EXACT_UPSTREAM_AUDIT_V1",
 "registry_checker_count":len(registry_ids),
 "test_instances":len(results),
 "passed":len(results)-len(failed),
 "failed":len(failed),
 "all_pass":not failed,
 "failed_rows":failed,
 "subject_blob":"3699a676b91845b40029813b60a2c30e7f325667",
 "upstream_commit":"8f8e5c381a16e3f24257776edd53471fe86f8091",
 "terminal_case_content_read":False,
 "model_dependency_count":0,
}
print(json.dumps(summary,indent=2,ensure_ascii=False,sort_keys=True))
if failed:
    raise SystemExit(1)
