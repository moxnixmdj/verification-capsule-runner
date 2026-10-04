#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import itertools
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
ACTIVE15_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
MANDATORY_LOSS_BLOB = "0f7f22e3ac694d1181e7956ed6552cee376c9d21"
MANDATORY_FOOTPRINT_BLOB = "4e0c036e18265ad89206ab9c47ba8420ecee6069"
ROOT = pathlib.Path(__file__).resolve().parent
ACTIVE15_PATH = ROOT / "subject/livebench_composer_v2_20261005/canonical/runtime/livebench_legacy15_composition_archetypes_v1.py"
SEMANTIC_ROOT = ROOT / "subject/livebench_union25_semantic_cut_20261005/canonical/runtime"
MANDATORY_LOSS_PATH = SEMANTIC_ROOT / "livebench_union25_mandatory_loss_v1.py"
MANDATORY_FOOTPRINT_PATH = SEMANTIC_ROOT / "livebench_union25_mandatory_footprint_v1.py"

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)

def git_blob(path: pathlib.Path) -> str:
    return run(["git","hash-object",str(path)],capture_output=True).stdout.strip()

def load_module(name: str, path: pathlib.Path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def compatible(group, conflicts):
    s=set(group)
    for x in s:
        if (set(conflicts[x]) - {x}) & (s - {x}):
            return False
    return True

def enum_compatible(universe, conflicts, max_size=5, min_size=1):
    out=set()
    for k in range(min_size, min(max_size,len(universe))+1):
        for c in itertools.combinations(universe,k):
            if compatible(c,conflicts):
                out.add(frozenset(c))
    return out

def main():
    assert git_blob(ACTIVE15_PATH) == ACTIVE15_BLOB
    assert git_blob(MANDATORY_LOSS_PATH) == MANDATORY_LOSS_BLOB
    assert git_blob(MANDATORY_FOOTPRINT_PATH) == MANDATORY_FOOTPRINT_BLOB
    mandatory_loss=load_module("union25_mandatory_loss_subject",MANDATORY_LOSS_PATH)
    mandatory_footprint=load_module("union25_mandatory_footprint_subject",MANDATORY_FOOTPRINT_PATH)
    sys.path.insert(0,str(ACTIVE15_PATH.parents[3]))
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as active15

    live=pathlib.Path("/tmp/LiveBench")
    assert run(["git","-C",str(live),"rev-parse","HEAD"],capture_output=True).stdout.strip()==LIVEBENCH_COMMIT
    regpath="livebench/if_runner/instruction_following_eval/instructions_registry.py"
    assert run(["git","-C",str(live),"rev-parse",f"HEAD:{regpath}"],capture_output=True).stdout.strip()==REGISTRY_BLOB
    sys.path.insert(0,str(live/"livebench/if_runner"))
    from instruction_following_eval import instructions_registry as registry
    from instruction_following_eval import instructions_util

    ids=tuple(registry.INSTRUCTION_DICT)
    assert len(ids)==25 and len(set(ids))==25
    conflicts={k:set(v) for k,v in registry.INSTRUCTION_CONFLICTS.items()}
    conflicts=registry.conflict_make(conflicts)
    assert set(conflicts)==set(ids)

    active=tuple(active15.ACTIVE_IDS)
    assert len(active)==15 and set(active)<set(ids)
    extra=tuple(x for x in ids if x not in set(active))
    assert len(extra)==10

    full=enum_compatible(ids,conflicts)
    active_sets=enum_compatible(active,conflicts)
    extra_kernels=enum_compatible(extra,conflicts)

    assert len(full)==14559, len(full)
    assert len(active_sets)==928, len(active_sets)
    assert len(extra_kernels)==156, len(extra_kernels)

    factored=set()
    for e in extra_kernels:
        remaining=5-len(e)
        active_choices={frozenset()}
        for k in range(1,remaining+1):
            for a in itertools.combinations(active,k):
                if compatible(a,conflicts) and compatible(tuple(e)+tuple(a),conflicts):
                    active_choices.add(frozenset(a))
        for a in active_choices:
            factored.add(frozenset(set(e)|set(a)))

    with_extra={s for s in full if s & set(extra)}
    assert factored==with_extra
    assert len(with_extra)==13631
    assert full==active_sets|factored
    assert active_sets.isdisjoint(factored)

    by_extra_count=Counter(sum(x in set(extra) for x in s) for s in with_extra)
    expected={1:4317,2:5892,3:2906,4:495,5:21}
    assert dict(sorted(by_extra_count.items()))==expected

    touch={e:sum(e in s for s in full) for e in extra}
    expected_touch={
      "keywords:frequency":3690,
      "keywords:letter_frequency":3938,
      "language:response_language":809,
      "detectable_content:number_placeholders":3938,
      "detectable_format:constrained_response":1,
      "detectable_format:number_highlighted_sections":2858,
      "change_case:capital_word_frequency":2738,
      "change_case:english_capital":2490,
      "change_case:english_lowercase":2490,
      "punctuation:no_comma":3952,
    }
    assert touch==expected_touch

    kernel_sizes=Counter(len(s) for s in extra_kernels)
    assert dict(sorted(kernel_sizes.items()))=={1:10,2:30,3:50,4:45,5:21}

    # Exact second quotient: three syntactic decorators carry no independent
    # parameter interaction class, while constrained_response is structurally
    # singleton. The remaining load-bearing semantic kernel is only six
    # families and has 19 conflict-compatible nonempty signatures.
    decorators=frozenset({
      "detectable_content:number_placeholders",
      "detectable_format:number_highlighted_sections",
      "punctuation:no_comma",
    })
    constrained="detectable_format:constrained_response"
    hard6=tuple(x for x in extra if x not in decorators and x != constrained)
    assert set(hard6)=={
      "keywords:frequency",
      "keywords:letter_frequency",
      "language:response_language",
      "change_case:capital_word_frequency",
      "change_case:english_capital",
      "change_case:english_lowercase",
    }
    hard_cores=enum_compatible(hard6,conflicts)
    assert len(hard_cores)==19
    assert Counter(len(x) for x in hard_cores)==Counter({1:6,2:9,3:4})
    projected={}
    for kernel in extra_kernels:
        if constrained in kernel:
            key=("CONSTRAINED_SINGLETON",)
        else:
            core=tuple(sorted(set(kernel)&set(hard6)))
            key=core if core else ("DECORATOR_ONLY",)
        projected.setdefault(key,0)
        projected[key]+=1
    assert len(projected)==21
    assert projected[("CONSTRAINED_SINGLETON",)]==1
    assert projected[("DECORATOR_ONLY",)]==7
    nontrivial_projected={k for k in projected if k not in {("CONSTRAINED_SINGLETON",),("DECORATOR_ONLY",)}}
    assert nontrivial_projected=={tuple(sorted(x)) for x in hard_cores}

    # Exact zero-lexical-footprint witnesses for the two positive syntactic
    # decorators. These atoms satisfy the pinned checkers while adding no
    # word tokens, ASCII letters, capital words, commas, or sentence-ending
    # punctuation. Placement relative to structural wrappers remains a
    # separate composition obligation.
    placeholder_atoms={}
    for n in range(1,5):
        atom="[]"*n
        checker=registry.INSTRUCTION_DICT["detectable_content:number_placeholders"](
            "detectable_content:number_placeholders"
        )
        checker.build_description(num_placeholders=n)
        assert checker.check_following(atom)
        assert instructions_util.count_words(atom)==0
        assert not re.search(r"[A-Za-z]",atom)
        assert "," not in atom
        assert not any(tok.isupper() for tok in instructions_util.nltk.word_tokenize(atom))
        placeholder_atoms[n]=atom

    highlight_atoms={}
    for n in range(1,5):
        atom=" ".join(["*#*"]*n)
        checker=registry.INSTRUCTION_DICT["detectable_format:number_highlighted_sections"](
            "detectable_format:number_highlighted_sections"
        )
        checker.build_description(num_highlights=n)
        assert checker.check_following(atom)
        assert instructions_util.count_words(atom)==0
        assert not re.search(r"[A-Za-z]",atom)
        assert "," not in atom
        assert not any(tok.isupper() for tok in instructions_util.nltk.word_tokenize(atom))
        highlight_atoms[n]=atom

    # Exact hidden semantic incompatibilities missed by the structural
    # registry conflict graph.
    semantic_loss_rules=[]

    repeat=registry.INSTRUCTION_DICT["combination:repeat_prompt"]("combination:repeat_prompt")
    repeat.build_description(prompt_to_repeat="alpha, beta")
    comma=registry.INSTRUCTION_DICT["punctuation:no_comma"]("punctuation:no_comma")
    comma.build_description()
    assert repeat.check_following("alpha, beta 0")
    assert not comma.check_following("alpha, beta 0")
    assert "," in repeat._prompt_to_repeat
    semantic_loss_rules.append("REPEAT_PREFIX_COMMA_VS_NO_COMMA")

    section_cls=registry.INSTRUCTION_DICT["detectable_format:multiple_sections"]
    lower_cls=registry.INSTRUCTION_DICT["change_case:english_lowercase"]
    upper_cls=registry.INSTRUCTION_DICT["change_case:english_capital"]
    capfreq_cls=registry.INSTRUCTION_DICT["change_case:capital_word_frequency"]

    for splitter in ("Section","SECTION"):
        section=section_cls("detectable_format:multiple_sections")
        section.build_description(section_spliter=splitter,num_sections=2)
        assert section._section_spliter==splitter
        # A SectionChecker pass with n>=1 requires at least one exact literal
        # splitter match; both frozen splitters contain uppercase cased letters.
        assert any(ch.isupper() for ch in splitter)
        assert not splitter.islower()
    semantic_loss_rules.append("LOWERCASE_ENGLISH_VS_SECTION_HEADING_CASE")

    assert not "Section".isupper() and "SECTION".isupper()
    semantic_loss_rules.append("UPPERCASE_ENGLISH_VS_MIXED_CASE_SECTION_HEADING")

    for n in range(1,6):
        sample="\n".join(f"SECTION {i} 0" for i in range(1,n+1))
        section=section_cls("detectable_format:multiple_sections")
        section.build_description(section_spliter="SECTION",num_sections=n)
        assert section.check_following(sample)
        uppercase_tokens=[tok for tok in instructions_util.nltk.word_tokenize(sample) if tok.isupper()]
        assert len(uppercase_tokens)>=n
        assert uppercase_tokens.count("SECTION")>=n
    semantic_loss_rules.append("CAPITAL_WORD_UPPER_BOUND_VS_UPPERCASE_SECTION_FLOOR")
    assert len(set(semantic_loss_rules))==4

    # Execute the exact canonical Brain semantic-cut subjects against known
    # source-derived boundary cases.
    def contract(iid, **slots):
        return {"instruction_id":iid,"slots":slots}

    out=mandatory_loss.derive(
        [contract("combination:repeat_prompt"),contract("punctuation:no_comma")],
        prompt_to_repeat="alpha, beta",
    )
    assert {x["rule_id"] for x in out["mandatory_loss_rules"]}=={"REPEAT_PREFIX_COMMA_VS_NO_COMMA"}

    out=mandatory_loss.derive([
        contract("detectable_format:multiple_sections",section_spliter="Section",num_sections=2),
        contract("change_case:english_capital"),
    ])
    assert {x["rule_id"] for x in out["mandatory_loss_rules"]}=={"UPPERCASE_ENGLISH_VS_MIXED_CASE_SECTION_HEADING"}

    out=mandatory_loss.derive([
        contract("detectable_format:multiple_sections",section_spliter="SECTION",num_sections=2),
        contract("change_case:english_lowercase"),
    ])
    assert {x["rule_id"] for x in out["mandatory_loss_rules"]}=={"LOWERCASE_ENGLISH_VS_SECTION_HEADING_CASE"}

    fp_cases=[
      (
        [
          contract("keywords:frequency",keyword="help",relation="less than",frequency=1),
          contract("startend:end_checker",end_phrase="Is there anything else I can help with?"),
        ],
        "KEYWORD_FREQUENCY_STRICT_UPPER_BOUND_BELOW_MANDATORY_LITERAL_FLOOR",
      ),
      (
        [
          contract("keywords:letter_frequency",letter="p",let_relation="less than",let_frequency=2),
          contract("detectable_content:postscript",postscript_marker="P.P.S"),
        ],
        "LETTER_FREQUENCY_STRICT_UPPER_BOUND_BELOW_MANDATORY_LITERAL_FLOOR",
      ),
      (
        [
          contract("change_case:capital_word_frequency",capital_relation="less than",capital_frequency=4),
          contract("detectable_format:multiple_sections",section_spliter="SECTION",num_sections=4),
        ],
        "CAPITAL_WORD_STRICT_UPPER_BOUND_BELOW_MANDATORY_SECTION_FLOOR",
      ),
    ]
    footprint_rule_ids=[]
    for contracts,expected_rule in fp_cases:
        losses=mandatory_footprint.proved_upper_bound_losses(contracts)
        assert len(losses)==1 and losses[0]["rule_id"]==expected_rule
        footprint_rule_ids.append(expected_rule)

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_UNION25_DELTA10_STRUCTURAL_FACTORIZATION_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS__REGISTRY25_EXACTLY_FACTORS_AS_ACTIVE15_928_PLUS_DELTA10_156_EXTENSION_KERNELS__13631_EXPANDED_NEW_SETS",
      "pinned_livebench_commit":LIVEBENCH_COMMIT,
      "registry_blob":REGISTRY_BLOB,
      "active15_blob":ACTIVE15_BLOB,
      "registry_family_count":25,
      "active15_family_count":15,
      "delta10_family_count":10,
      "full_compatible_sets_size_1_to_5":len(full),
      "active15_compatible_sets_size_1_to_5":len(active_sets),
      "delta10_internal_compatible_kernels_size_1_to_5":len(extra_kernels),
      "new_union25_sets_touching_delta10":len(with_extra),
      "delta10_kernel_size_histogram":dict(sorted(kernel_sizes.items())),
      "delta10_exact_decorator_and_mandatory_loss_lemmas":{
        "zero_lexical_footprint_placeholder_atoms":placeholder_atoms,
        "zero_lexical_footprint_highlight_atoms":highlight_atoms,
        "new_sound_mandatory_loss_rule_ids":semantic_loss_rules,
        "canonical_mandatory_loss_blob":MANDATORY_LOSS_BLOB,
        "canonical_mandatory_footprint_blob":MANDATORY_FOOTPRINT_BLOB,
        "canonical_mandatory_footprint_boundary_rule_ids":footprint_rule_ids,
        "mandatory_loss_rule_count":len(semantic_loss_rules),
        "complete_union25_loss_map":False
      },
      "delta10_second_quotient":{
        "decorator_families":sorted(decorators),
        "constrained_singleton_family":constrained,
        "hard_family_count":len(hard6),
        "hard_families":list(hard6),
        "hard_compatible_core_signature_count":len(hard_cores),
        "hard_core_size_histogram":dict(sorted(Counter(len(x) for x in hard_cores).items())),
        "projected_class_count_including_decorator_only_and_constrained":len(projected),
        "decorator_only_kernel_count":projected[("DECORATOR_ONLY",)],
        "constrained_kernel_count":projected[("CONSTRAINED_SINGLETON",)],
        "claim_scope":"STRUCTURAL_SEMANTIC_BURDEN_PROJECTION_ONLY__DECORATOR_NEUTRALITY_WITH_ACTIVE15_CONTEXT_REQUIRES_SEPARATE_EXACT_LEMMA"
      },
      "expanded_set_extra_family_count_histogram":dict(sorted(by_extra_count.items())),
      "delta10_touch_counts":touch,
      "delta10_families":list(extra),
      "factorization_identity":"FULL14559 = ACTIVE15_928 DISJOINT_UNION FACTOR(EXTRA_KERNEL156, COMPATIBLE_ACTIVE15_RESIDUES)_13631",
      "terminal_rows_read":0,
      "terminal_kwargs_read":0,
      "terminal_instruction_id_lists_read":0,
      "target_scores_read":0,
      "acceptance_credit_delta":0,
      "hard_nonclaims":[
        "STRUCTURAL_FACTORIZATION_IS_NOT_MULTI_CONTRACT_SEMANTIC_POINTWISE_OPTIMALITY",
        "THE_19_HARD_CORE_SIGNATURES_STILL_REQUIRE_SEMANTIC_INTERACTION_CLOSURE_WITH_COMPATIBLE_ACTIVE15_RESIDUES",
        "THE_DECORATOR_PROJECTION_DOES_NOT_BY_ITSELF_PROVE_PLACEMENT_NEUTRALITY_IN_EVERY_ACTIVE15_CONTEXT",
        "THE_FOUR_NEW_MANDATORY_LOSS_RULES_ARE_A_SOUND_LOWER_BOUND_NOT_A_COMPLETE_UNION25_LOSS_MAP",
        "NO_LIVEBENCH_ACCEPTANCE_CREDIT_FROM_THIS_RECEIPT_ALONE"
      ]
    }
    pathlib.Path("livebench_union25_delta10_factorization_v1.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__":
    main()
