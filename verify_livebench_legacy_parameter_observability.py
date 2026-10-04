#!/usr/bin/env python3
from __future__ import annotations

import hashlib, importlib, json, sys, urllib.request
from pathlib import Path

COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
BASE=f"https://raw.githubusercontent.com/LiveBench/LiveBench/{COMMIT}/livebench/if_runner/instruction_following_eval"
PINS={
 "instructions.py":"4997bab885a676d92545fd91a9a20b48d234a2b2",
 "instructions_util.py":"1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
 "instructions_registry.py":"903ed738398648c7cfac61d5ffa478c22f1f0891",
}

def fetch(name):
    req=urllib.request.Request(f"{BASE}/{name}",headers={"User-Agent":"brain-verifier"})
    return urllib.request.urlopen(req,timeout=60).read()

def blob_sha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def main():
    root=Path("vendor_legacy")
    pkg=root/"instruction_following_eval"
    pkg.mkdir(parents=True,exist_ok=True)
    (pkg/"__init__.py").write_text("")
    for name,sha in PINS.items():
        data=fetch(name)
        assert blob_sha(data)==sha,(name,blob_sha(data),sha)
        (pkg/name).write_bytes(data)
    sys.path.insert(0,str(root.resolve()))
    ins=importlib.import_module("instruction_following_eval.instructions")
    reg=importlib.import_module("instruction_following_eval.instructions_registry")

    assert len(reg.INSTRUCTION_DICT)==25, len(reg.INSTRUCTION_DICT)

    cases={
      "keywords:existence":({"keywords":["nebula","zircon"]},["nebula","zircon"]),
      "keywords:frequency":({"keyword":"quasar","frequency":3,"relation":"at least"},["quasar","3","at least"]),
      "keywords:forbidden_words":({"forbidden_words":["cobalt","mango"]},["cobalt","mango"]),
      "keywords:letter_frequency":({"letter":"q","let_frequency":7,"let_relation":"less than"},["q","7","less than"]),
      "language:response_language":({"language":"fi"},["Finnish"]),
      "length_constraints:number_sentences":({"num_sentences":7,"relation":"at least"},["7","at least"]),
      "length_constraints:number_paragraphs":({"num_paragraphs":4},["4"]),
      "length_constraints:number_words":({"num_words":137,"relation":"less than"},["137","less than"]),
      "length_constraints:nth_paragraph_first_word":({"num_paragraphs":4,"nth_paragraph":3,"first_word":"zephyr"},["4","3","zephyr"]),
      "detectable_content:number_placeholders":({"num_placeholders":3},["3"]),
      "detectable_content:postscript":({"postscript_marker":"P.S."},["P.S."]),
      "detectable_format:number_bullet_lists":({"num_bullets":4},["4"]),
      "detectable_format:constrained_response":({},["My answer is yes.","My answer is no.","My answer is maybe."]),
      "detectable_format:number_highlighted_sections":({"num_highlights":3},["3"]),
      "detectable_format:multiple_sections":({"section_spliter":"SECTION","num_sections":4},["SECTION","4"]),
      "detectable_format:json_format":({},["JSON"]),
      "detectable_format:title":({},["<<poem of joy>>"]),
      "combination:two_responses":({},["******"]),
      "combination:repeat_prompt":({"prompt_to_repeat":"VISIBLE_BASE_REQUEST_SENTINEL"},[]),
      "startend:end_checker":({"end_phrase":"Any other questions?"},["Any other questions?"]),
      "change_case:capital_word_frequency":({"capital_frequency":7,"capital_relation":"at least"},["7","at least"]),
      "change_case:english_capital":({},["all capital letters"]),
      "change_case:english_lowercase":({},["all lowercase letters"]),
      "punctuation:no_comma":({},["commas"]),
      "startend:quotation":({},["double quotation marks"]),
    }
    assert set(cases)==set(reg.INSTRUCTION_DICT), (set(cases)^set(reg.INSTRUCTION_DICT))

    rows=[]
    hidden=[]
    for iid,cls in reg.INSTRUCTION_DICT.items():
        kwargs,visible_tokens=cases[iid]
        obj=cls(iid)
        desc=obj.build_description(**kwargs)
        args=obj.get_instruction_args()
        if args is None: args={}
        for token in visible_tokens:
            assert str(token).lower() in desc.lower(),(iid,token,desc)
        hidden_keys=[]
        for key,value in args.items():
            if value is None: continue
            if key=="language":
                # Public source maps ISO code to a visible language name.
                assert ins._LANGUAGES[value].lower() in desc.lower()
                continue
            if key=="prompt_to_repeat":
                assert str(value) not in desc
                hidden_keys.append(key)
                continue
            if isinstance(value,(list,tuple,set)):
                for v in value:
                    assert str(v).lower() in desc.lower(),(iid,key,v,desc)
            else:
                assert str(value).lower() in desc.lower(),(iid,key,value,desc)
        if hidden_keys:
            hidden.append({"instruction_id":iid,"keys":hidden_keys})
        rows.append({"instruction_id":iid,"description":desc,"arg_keys":sorted(args),"hidden_arg_keys":hidden_keys})

    assert hidden==[{"instruction_id":"combination:repeat_prompt","keys":["prompt_to_repeat"]}],hidden

    # The one non-rendered value is definitionally the request preceding the
    # repeat instruction. Demonstrate prompt-only recovery from the exact fixed
    # public description without inspecting dataset kwargs.
    iid="combination:repeat_prompt"
    cls=reg.INSTRUCTION_DICT[iid]
    base="VISIBLE_BASE_REQUEST_SENTINEL"
    obj=cls(iid)
    desc=obj.build_description(prompt_to_repeat=base)
    full=base+"\n"+desc
    pos=full.find(desc)
    assert pos>0
    recovered=full[:pos].strip()
    assert recovered==base

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY_PARAMETER_OBSERVABILITY_VERIFICATION_V1",
      "status":"PASS__25_OF_25_LEGACY_CHECKER_FAMILIES_HAVE_PROMPT_OBSERVABLE_SCORING_PARAMETERS_OR_PROMPT_PREFIX_RECOVERY",
      "pinned_livebench_commit":COMMIT,
      "pinned_blobs":PINS,
      "registered_checker_families":len(reg.INSTRUCTION_DICT),
      "families_audited":len(rows),
      "ordinary_families_with_all_nonnull_scoring_args_rendered":24,
      "nonrendered_arg_families":hidden,
      "repeat_prompt_recovery":"VISIBLE_PREFIX_BEFORE_EXACT_PUBLIC_REPEAT_DESCRIPTION",
      "terminal_dataset_rows_read":0,
      "terminal_prompt_content_read":False,
      "terminal_kwargs_read":False,
      "model_dependency_count":0,
      "incremental_spend_usd":0,
      "acceptance_credit_delta":0,
      "hard_nonclaim":"This proves source-level parameter observability, not that a witness compiler yet satisfies every compatible multi-checker composition."
    }
    Path("livebench_legacy_parameter_observability_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__":
    main()
