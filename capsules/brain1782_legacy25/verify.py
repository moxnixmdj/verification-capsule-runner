#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT_ROOT=ROOT/"subject"
INVERTER=SUBJECT_ROOT/"canonical/runtime/livebench_legacy_ifeval_prompt_inverter_v1.py"
SOLVER=SUBJECT_ROOT/"canonical/runtime/livebench_legacy_ifeval_single_checker_witness_v1.py"
EXPECTED_INVERTER_BLOB="74904d2a00ed3f0bb2e8ab7787c59c0a8f828f7a"
EXPECTED_SOLVER_BLOB="341b3413493caf8c1cd2e1ab1f18c93d62f4ba87"

def blob(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert blob(INVERTER)==EXPECTED_INVERTER_BLOB, blob(INVERTER)
assert blob(SOLVER)==EXPECTED_SOLVER_BLOB, blob(SOLVER)

sys.path.insert(0,str(SUBJECT_ROOT))
sys.path.insert(0,"/tmp/LiveBench/livebench/if_runner")

from canonical.runtime import livebench_legacy_ifeval_single_checker_witness_v1 as solver
from instruction_following_eval import instructions_registry, instructions_util

BASE="Explain the topic briefly."

cases=[
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
assert len(registry_ids)==25
assert registry_ids=={
 "keywords:existence","keywords:frequency","keywords:forbidden_words","keywords:letter_frequency",
 "language:response_language","length_constraints:number_sentences","length_constraints:number_paragraphs",
 "length_constraints:number_words","length_constraints:nth_paragraph_first_word",
 "detectable_content:number_placeholders","detectable_content:postscript",
 "detectable_format:number_bullet_lists","detectable_format:constrained_response",
 "detectable_format:number_highlighted_sections","detectable_format:multiple_sections",
 "detectable_format:json_format","detectable_format:title","combination:two_responses",
 "combination:repeat_prompt","startend:end_checker","change_case:capital_word_frequency",
 "change_case:english_capital","change_case:english_lowercase","punctuation:no_comma","startend:quotation"
}

results=[]
def check(iid,kwargs):
    cls=instructions_registry.INSTRUCTION_DICT[iid]
    inst=cls(iid)
    desc=inst.build_description(**kwargs)
    prompt=(BASE+" "+desc).strip()
    got=solver.solve(prompt)
    err=None
    try:
        passed=(
            got.get("status")=="PASS_CANDIDATE_SINGLE_CHECKER_WITNESS"
            and got.get("instruction_id")==iid
            and bool(inst.check_following(got.get("response","")))
        )
    except Exception as exc:
        passed=False; err=f"{type(exc).__name__}:{exc}"
    results.append({
        "instruction_id":iid,
        "kwargs":kwargs,
        "description":desc,
        "solver_status":got.get("status"),
        "recognized":got.get("recognized_instruction_ids") or [got.get("instruction_id")],
        "response":got.get("response"),
        "checker_pass":passed,
        "error":err,
    })

for iid,kwargs in cases:
    check(iid,kwargs)

for code in instructions_util.LANGUAGE_CODES:
    check("language:response_language",{"language":code})

failed=[r for r in results if not r["checker_pass"]]
summary={
 "schema":"PROJECT_BRAIN_PR1782_LEGACY25_EXACT_UPSTREAM_VERIFICATION_V1",
 "brain_pr":1782,
 "inverter_blob":EXPECTED_INVERTER_BLOB,
 "solver_blob":EXPECTED_SOLVER_BLOB,
 "upstream_commit":"8f8e5c381a16e3f24257776edd53471fe86f8091",
 "registry_checker_count":len(registry_ids),
 "test_instances":len(results),
 "passed":len(results)-len(failed),
 "failed":len(failed),
 "all_pass":not failed,
 "failed_rows":failed,
 "terminal_case_content_read":False,
 "model_dependency_count":0,
 "incremental_spend_usd":0,
 "acceptance_credit_delta":0,
}
(ROOT/"receipt.json").write_text(json.dumps(summary,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(summary,indent=2,sort_keys=True,ensure_ascii=False))
if failed:
    raise SystemExit(1)
