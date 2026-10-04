#!/usr/bin/env python3
"""Boundary-equivalence audit for the public-source LiveBench legacy-15 witness.

This does not read terminal rows. It enumerates all 928 conflict-compatible
identity sets and a source-derived boundary/enum basis for every parameter
family whose public default generator is finite. The basis deliberately
includes lexical collisions that can expose impossible or unsupported
cross-constraint interactions.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from itertools import product
import json
import re
from pathlib import Path
import sys

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_joint_witness_v1 as witness
from canonical.runtime import livebench_legacy15_end2end_exact_synthetic_audit_v2 as base

SCHEMA="PROJECT_BRAIN_LIVEBENCH_LEGACY15_PARAMETER_BOUNDARY_AUDIT_V1"
EXPECTED_UTIL_BLOB="1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

E0=["rock","river","signal","system","brain"]
# Exact generated-word collisions with forced structural literals from the\n# pinned source: Section/SECTION and the two exact end phrases.  `phrase` was\n# previously used here but is not forced by any checker; `can` is forced by\n# the second end phrase and therefore must be represented.\nE1=["section","other","anything","can","help"]
F0=["apple","market","glass","shoe","hotel"]
F1=list(E0)
F2=list(E1)

DOMAINS={
 "keywords:existence":[("existence",E0),("existence",E1)],
 "keywords:forbidden_words":[("forbidden",F0),("forbidden",F1),("forbidden",F2)],
 "length_constraints:number_paragraphs":[("paragraphs",n) for n in range(1,6)],
 "length_constraints:number_words":[("words",(500,"at least")),("words",(100,"less than"))],
 "length_constraints:number_sentences":[
   ("sentences",(20,"at least")),
   ("sentences",(2,"less than")),
   ("sentences",(1,"less than")),
 ],
 "length_constraints:nth_paragraph_first_word":[
   ("nth",(n,k,w))
   for n in range(1,6) for k in range(1,n+1) for w in ("river","section")
 ],
 "detectable_content:postscript":[("postscript","P.S."),("postscript","P.P.S")],
 "detectable_format:number_bullet_lists":[("bullets",n) for n in range(1,6)],
 "detectable_format:title":[(None,None)],
 "detectable_format:multiple_sections":[
   ("sections",(sp,n)) for sp in ("Section","SECTION") for n in range(1,6)
 ],
 "detectable_format:json_format":[(None,None)],
 "combination:repeat_prompt":[(None,None)],
 "combination:two_responses":[(None,None)],
 "startend:end_checker":[
   ("end","Any other questions?"),
   ("end","Is there anything else I can help with?"),
 ],
 "startend:quotation":[(None,None)],
}

DEFAULT={
 "name":"BOUNDARY",
 "existence":E0,
 "forbidden":F0,
 "paragraphs":2,
 "words":(500,"at least"),
 "sentences":(20,"at least"),
 "nth":(3,2,"river"),
 "postscript":"P.S.",
 "bullets":2,
 "sections":("Section",2),
 "end":"Any other questions?",
}

def assignments(ids):
    ds=[DOMAINS[i] for i in ids]
    for choices in product(*ds):
        p=dict(DEFAULT)
        tags=[]
        for key,value in choices:
            if key is not None:
                p[key]=value
                tags.append(f"{key}={value!r}")
        p["name"]="|".join(tags)
        yield p

def audit(livebench_root: Path, max_failures:int=100):
    legacy=livebench_root/"livebench/if_runner/instruction_following_eval"
    assert base.git_blob_sha(legacy/"instructions_registry.py")==base.FROZEN_REGISTRY_BLOB
    assert base.git_blob_sha(legacy/"instructions.py")==base.FROZEN_INSTRUCTIONS_BLOB
    assert base.git_blob_sha(legacy/"instructions_util.py")==EXPECTED_UTIL_BLOB
    sys.path.insert(0,str(livebench_root/"livebench/if_runner"))
    from instruction_following_eval import instructions_registry as registry
    from instruction_following_eval import instructions, instructions_util

    # Mechanically derive the lexical words that the witness is forced to emit\n    # when SectionChecker or EndChecker is active.  Intersecting with the exact\n    # frozen generator WORD_LIST yields the complete forbidden-word collision\n    # class; this prevents hand-picked representatives from silently missing a\n    # generated word such as `can`.\n    forced_text=" ".join(list(instructions._SECTION_SPLITER)+list(instructions._ENDING_OPTIONS))
    structural_collision_words=sorted(set(re.findall(r"[a-z]+",forced_text.lower())) & set(instructions_util.WORD_LIST))
    assert structural_collision_words==sorted(F2), structural_collision_words
    assert len(instructions_util.WORD_LIST)==1525
    assert len(set(instructions_util.WORD_LIST))==1525
    assert all(re.fullmatch(r"[a-z]+",w) for w in instructions_util.WORD_LIST)

    sets=archetypes.enumerate_compatible_sets()
    assert len(sets)==928
    total=passes=runtime_blocks=exact_fails=0
    runtime_errors=Counter()
    failed_ids=Counter()
    failed_shapes=Counter()
    by_archetype=defaultdict(Counter)
    failures=[]

    for ids in sets:
        arch=archetypes.archetype(ids)
        for profile in assignments(ids):
            # Forward order is sufficient for parameter coverage; the separate
            # 7424 audit independently verifies forward/reverse order symmetry
            # for every structural identity set.
            total+=1
            prompt,records=base.render_prompt(ids,profile,registry,False)
            out=witness.solve(prompt)
            if out.get("status")!="PASS_CANDIDATE_JOINT_LEGACY15_WITNESS":
                runtime_blocks+=1
                reason=str(out.get("error") or out.get("status"))
                runtime_errors[reason]+=1
                failed_shapes[tuple(ids)]+=1
                by_archetype[arch]["runtime_block"]+=1
                if len(failures)<max_failures:
                    failures.append({"ids":list(ids),"profile":profile["name"],"stage":"runtime","reason":reason})
                continue
            ok,failed=base.exact_check(str(out["response"]),records,registry)
            if ok:
                passes+=1
                by_archetype[arch]["pass"]+=1
            else:
                exact_fails+=1
                failed_shapes[tuple(ids)]+=1
                by_archetype[arch]["exact_fail"]+=1
                for x in failed: failed_ids[x]+=1
                if len(failures)<max_failures:
                    failures.append({"ids":list(ids),"profile":profile["name"],"stage":"checker","failed_ids":failed})

    result={
      "schema":SCHEMA,
      "status":"PASS_NO_FAILURES" if passes==total else "FAILURE_CLASSES_LOCALIZED",
      "bindings":{
        "livebench_commit":base.FROZEN_LIVEBENCH_COMMIT,
        "registry_blob":base.FROZEN_REGISTRY_BLOB,
        "instructions_blob":base.FROZEN_INSTRUCTIONS_BLOB,
        "witness_schema":witness.SCHEMA,
        "archetype_schema":archetypes.SCHEMA,
      },
      "scope":{
        "compatible_identity_sets":len(sets),
        "word_list_size":len(instructions_util.WORD_LIST),
        "structural_forbidden_collision_words":structural_collision_words,
        "boundary_cases":total,
        "terminal_rows_read":0,
        "terminal_prompts_read":0,
        "terminal_scores_read":0,
        "order_symmetry_proof_source":"PROJECT_BRAIN_LIVEBENCH_LEGACY15_END2END_EXACT_SYNTHETIC_AUDIT_V2__7424_OF_7424_AFTER_GENERIC_REPAIRS",
      },
      "results":{
        "pass":passes,"runtime_block":runtime_blocks,"exact_fail":exact_fails,
        "pass_fraction":passes/total,
        "failed_identity_shape_count":len(failed_shapes),
      },
      "runtime_errors":dict(runtime_errors.most_common()),
      "exact_failed_instruction_ids":dict(failed_ids.most_common()),
      "by_archetype":{k:dict(v) for k,v in sorted(by_archetype.items())},
      "failed_identity_shapes_top":[{"ids":list(k),"failures":v} for k,v in failed_shapes.most_common(50)],
      "failure_samples":failures,
      "basis_semantics":[
        "NUMBER_WORDS_AT_LEAST_TESTS_SOURCE_MAX_500__LESS_THAN_TESTS_SOURCE_MIN_100",
        "NUMBER_SENTENCES_AT_LEAST_TESTS_SOURCE_MAX_20__LESS_THAN_TESTS_2_AND_SOURCE_MIN_1",
        "EXACT_COUNTS_ENUMERATE_ALL_SOURCE_VALUES_1_TO_5",
        "NTH_ENUMERATES_ALL_15_NUMERIC_COUNT_INDEX_PAIRS_AND_NORMAL_PLUS_COLLISION_WORD_CLASSES",
        "POSTSCRIPT_SECTION_SPLITTER_END_PHRASE_ENUMERATE_ALL_SOURCE_ENUM_VALUES",
        "LEXICAL_BASIS_INCLUDES_REQUIRED_FORBIDDEN_OVERLAP_AND_COMPLETE_SOURCE_DERIVED_FIXED_STRUCTURE_WORD_COLLISIONS",
        "STRUCTURAL_FORBIDDEN_COLLISION_CLASS_IS_DERIVED_MECHANICALLY_FROM_PINNED_SECTION_AND_END_LITERALS_INTERSECTED_WITH_PINNED_WORD_LIST",
      ],
      "hard_nonclaims":[
        "BOUNDARY_BASIS_IS_NOT_BY_ITSELF_A_FORMAL_UNIVERSAL_PARAMETER_PROOF",
        "NO_TERMINAL_CASE_CONTENT_READ",
        "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
      ],
    }
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--livebench-root",required=True)
    ap.add_argument("--output",required=True)
    ns=ap.parse_args()
    r=audit(Path(ns.livebench_root).resolve())
    Path(ns.output).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":r["status"],**r["results"],"runtime_errors":r["runtime_errors"],"exact_failed_instruction_ids":r["exact_failed_instruction_ids"]},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
