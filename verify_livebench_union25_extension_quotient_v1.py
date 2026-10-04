#!/usr/bin/env python3
from __future__ import annotations

import itertools, json, pathlib, sys
from collections import Counter, defaultdict

LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
ACTIVE15=(
"keywords:existence",
"keywords:forbidden_words",
"length_constraints:number_paragraphs",
"length_constraints:number_words",
"length_constraints:number_sentences",
"length_constraints:nth_paragraph_first_word",
"detectable_content:postscript",
"detectable_format:number_bullet_lists",
"detectable_format:title",
"detectable_format:multiple_sections",
"detectable_format:json_format",
"combination:repeat_prompt",
"combination:two_responses",
"startend:end_checker",
"startend:quotation",
)
ADDED10=(
"keywords:frequency",
"keywords:letter_frequency",
"language:response_language",
"detectable_content:number_placeholders",
"detectable_format:constrained_response",
"detectable_format:number_highlighted_sections",
"change_case:capital_word_frequency",
"change_case:english_capital",
"change_case:english_lowercase",
"punctuation:no_comma",
)

def main():
    root=pathlib.Path("/tmp/LiveBench")
    sys.path.insert(0,str(root/"livebench/if_runner"))
    from instruction_following_eval import instructions_registry as reg

    ids=tuple(reg.INSTRUCTION_DICT)
    assert len(ids)==25, len(ids)
    assert set(ids)==set(ACTIVE15)|set(ADDED10)
    assert not (set(ACTIVE15)&set(ADDED10))

    conflicts=reg.conflict_make({k:set(v) for k,v in reg.INSTRUCTION_CONFLICTS.items()})
    def compatible(comb):
        s=set(comb)
        return all(not ((conflicts[a]-{a}) & (s-{a})) for a in comb)

    compatible_sets=[]
    by_size=Counter()
    for k in range(1,6):
        for comb in itertools.combinations(ids,k):
            if compatible(comb):
                compatible_sets.append(comb)
                by_size[k]+=1
    assert len(compatible_sets)==14559, len(compatible_sets)

    active_only=[c for c in compatible_sets if set(c)<=set(ACTIVE15)]
    assert len(active_only)==928, len(active_only)

    extension=[c for c in compatible_sets if set(c)&set(ADDED10)]
    extra_subsets=set()
    extra_subset_structural_counts=Counter()
    extra_subset_active_projection_counts=defaultdict(set)
    added_count=Counter()
    active_count=Counter()
    extra_family_incidence=Counter()
    pair_incidence=Counter()
    max_active_projection=0

    for c in extension:
        e=tuple(sorted(set(c)&set(ADDED10)))
        a=tuple(sorted(set(c)&set(ACTIVE15)))
        extra_subsets.add(e)
        extra_subset_structural_counts[e]+=1
        extra_subset_active_projection_counts[e].add(a)
        added_count[len(e)]+=1
        active_count[len(a)]+=1
        max_active_projection=max(max_active_projection,len(a))
        for x in e:
            extra_family_incidence[x]+=1
        for x,y in itertools.combinations(e,2):
            pair_incidence[(x,y)]+=1

    # Exact structural extension quotient: all active projections that share the
    # same added-family set use the same added-family checker *types*. Parameter
    # and semantic interactions are deliberately a later quotient, not claimed here.
    per_extra=[]
    for e in sorted(extra_subsets,key=lambda x:(len(x),x)):
        per_extra.append({
            "added_families":list(e),
            "added_family_count":len(e),
            "compatible_union25_sets":extra_subset_structural_counts[e],
            "distinct_active15_projections":len(extra_subset_active_projection_counts[e]),
        })

    out={
      "schema":"PROJECT_BRAIN_LIVEBENCH_UNION25_STRUCTURAL_EXTENSION_QUOTIENT_INDEPENDENT_V1",
      "status":"PASS__EXACT_PINNED_REGISTRY25_STRUCTURAL_EXTENSION_QUOTIENT__ZERO_TERMINAL_ROWS",
      "livebench_commit":LIVEBENCH_COMMIT,
      "registry_family_count":25,
      "active15_family_count":15,
      "added_family_count":10,
      "compatible_union25_sets_1_to_5":len(compatible_sets),
      "compatible_active15_only_sets_1_to_5":len(active_only),
      "extension_sets_with_at_least_one_added_family":len(extension),
      "compatible_sets_by_cardinality":dict(sorted(by_size.items())),
      "distinct_added_family_subsets":len(extra_subsets),
      "added_family_subset_count_by_size":dict(sorted(Counter(map(len,extra_subsets)).items())),
      "extension_sets_by_added_family_count":dict(sorted(added_count.items())),
      "extension_sets_by_active15_projection_size":dict(sorted(active_count.items())),
      "max_active15_families_in_extension_set":max_active_projection,
      "extra_family_incidence":dict(sorted(extra_family_incidence.items())),
      "coactive_added_family_pair_count":len(pair_incidence),
      "per_added_subset":per_extra,
      "terminal_rows_read":0,
      "hidden_kwargs_read":0,
      "target_scores_read":0,
      "acceptance_credit":False,
      "hard_nonclaims":[
        "STRUCTURAL_QUOTIENT_IS_NOT_YET_A_SEMANTIC_POINTWISE_OPTIMALITY_PROOF",
        "PARAMETER_INTERACTIONS_INSIDE_EACH_EXTENSION_SIGNATURE_REMAIN_TO_BE_REDUCED",
        "NO_LIVEBENCH_ACCEPTANCE_CREDIT_FROM_THIS_RECEIPT_ALONE"
      ]
    }
    pathlib.Path("livebench_union25_extension_quotient_v1.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
