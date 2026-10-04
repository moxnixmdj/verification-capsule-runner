#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import pathlib
import subprocess
import sys
from collections import Counter

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
ACTIVE15_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
ROOT = pathlib.Path(__file__).resolve().parent
ACTIVE15_PATH = ROOT / "subject/livebench_composer_v2_20261005/canonical/runtime/livebench_legacy15_composition_archetypes_v1.py"

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)

def git_blob(path: pathlib.Path) -> str:
    return run(["git","hash-object",str(path)],capture_output=True).stdout.strip()

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
    sys.path.insert(0,str(ACTIVE15_PATH.parents[3]))
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as active15

    live=pathlib.Path("/tmp/LiveBench")
    assert run(["git","-C",str(live),"rev-parse","HEAD"],capture_output=True).stdout.strip()==LIVEBENCH_COMMIT
    regpath="livebench/if_runner/instruction_following_eval/instructions_registry.py"
    assert run(["git","-C",str(live),"rev-parse",f"HEAD:{regpath}"],capture_output=True).stdout.strip()==REGISTRY_BLOB
    sys.path.insert(0,str(live/"livebench/if_runner"))
    from instruction_following_eval import instructions_registry as registry

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
        "THE_156_KERNELS_STILL_REQUIRE_SEMANTIC_INTERACTION_CLOSURE_WITH_COMPATIBLE_ACTIVE15_RESIDUES",
        "NO_LIVEBENCH_ACCEPTANCE_CREDIT_FROM_THIS_RECEIPT_ALONE"
      ]
    }
    pathlib.Path("livebench_union25_delta10_factorization_v1.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__":
    main()
