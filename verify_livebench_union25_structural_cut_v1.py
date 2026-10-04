#!/usr/bin/env python3
from __future__ import annotations
import itertools, json, pathlib, sys
from collections import Counter, defaultdict

PINNED = "8f8e5c381a16e3f24257776edd53471fe86f8091"
ACTIVE15 = frozenset({
    "keywords:existence","keywords:forbidden_words",
    "length_constraints:number_paragraphs","length_constraints:number_words",
    "length_constraints:number_sentences","length_constraints:nth_paragraph_first_word",
    "detectable_content:postscript","detectable_format:number_bullet_lists",
    "detectable_format:title","detectable_format:multiple_sections",
    "detectable_format:json_format","combination:repeat_prompt",
    "combination:two_responses","startend:end_checker","startend:quotation",
})
CONSTRAINED="detectable_format:constrained_response"
JSON_ID="detectable_format:json_format"
TWO="combination:two_responses"
REPEAT="combination:repeat_prompt"
LANG="language:response_language"
NOCOMMA="punctuation:no_comma"

def main():
    root=pathlib.Path("/tmp/LiveBench")
    head=__import__("subprocess").run(
        ["git","-C",str(root),"rev-parse","HEAD"],check=True,text=True,capture_output=True
    ).stdout.strip()
    assert head==PINNED, (head,PINNED)
    sys.path.insert(0,str(root/"livebench/if_runner"))
    from instruction_following_eval import instructions_registry as r
    conflicts={k:set(v) for k,v in r.INSTRUCTION_CONFLICTS.items()}
    conflicts=r.conflict_make(conflicts)
    ids=tuple(r.INSTRUCTION_DICT.keys())
    assert len(ids)==25 and len(set(ids))==25
    extras=frozenset(ids)-ACTIVE15
    assert len(extras)==10

    def ok(s):
        ss=set(s)
        return all(not ((conflicts[a]-{a}) & ss) for a in ss)

    sets=[]
    for n in range(1,6):
        sets.extend(tuple(c) for c in itertools.combinations(ids,n) if ok(c))
    assert len(sets)==14559
    by_size=Counter(map(len,sets))
    assert dict(by_size)=={1:25,2:203,3:1055,4:3750,5:9526}

    def branch(s):
        q=set(s)
        if CONSTRAINED in q: return "CONSTRAINED"
        if JSON_ID in q: return "JSON"
        if TWO in q: return "TWO"
        if REPEAT in q: return "REPEAT"
        return "GENERAL"

    by_branch=Counter(branch(s) for s in sets)
    active_only=[s for s in sets if set(s)<=ACTIVE15]
    assert len(active_only)==928
    new=[s for s in sets if not set(s)<=ACTIVE15]

    constrained=[s for s in sets if CONSTRAINED in s]
    assert constrained==[(CONSTRAINED,)] or (len(constrained)==1 and set(constrained[0])=={CONSTRAINED})

    json_sets=[s for s in sets if JSON_ID in s]
    assert all(set(s)<=ACTIVE15 for s in json_sets)

    repeat_sets=[s for s in sets if REPEAT in s]
    assert all((set(s)-ACTIVE15)<= {NOCOMMA} for s in repeat_sets)

    two_sets=[s for s in sets if TWO in s]
    assert all((set(s)-ACTIVE15)<= {LANG,NOCOMMA} for s in two_sets)

    ext_sig=Counter(tuple(sorted(set(s)-ACTIVE15)) for s in new)
    general_new=[s for s in new if branch(s)=="GENERAL"]
    general_sig=Counter(tuple(sorted(set(s)-ACTIVE15)) for s in general_new)

    per_extra=Counter()
    pairs=Counter()
    for s in new:
        e=sorted(set(s)-ACTIVE15)
        for x in e: per_extra[x]+=1
        for a,b in itertools.combinations(e,2): pairs[(a,b)]+=1

    receipt={
        "schema":"PROJECT_BRAIN_LIVEBENCH_UNION25_STRUCTURAL_CUT_INDEPENDENT_V1",
        "status":"PASS__EXACT_PINNED_REGISTRY25_STRUCTURAL_CUT__ZERO_TERMINAL_ROWS",
        "pinned_livebench_commit":PINNED,
        "registry_family_count":25,
        "active15_family_count":15,
        "extension_family_count":10,
        "conflict_pair_count":sum(1 for a,b in itertools.combinations(ids,2) if b in conflicts[a]),
        "compatible_sets_1_to_5":len(sets),
        "counts_by_size":dict(sorted(by_size.items())),
        "active15_inherited_sets":len(active_only),
        "new_union25_sets":len(new),
        "branch_counts":dict(sorted(by_branch.items())),
        "new_branch_counts":dict(sorted(Counter(branch(s) for s in new).items())),
        "topology_lemmas":{
            "constrained_response_is_singleton_only":True,
            "json_adds_zero_new_union25_structures":True,
            "repeat_new_extension_universe":[NOCOMMA],
            "two_responses_new_extension_universe":[LANG,NOCOMMA],
        },
        "distinct_new_extension_signatures":len(ext_sig),
        "distinct_general_extension_signatures":len(general_sig),
        "general_new_sets":len(general_new),
        "new_sets_per_extra":dict(sorted(per_extra.items())),
        "new_extension_signatures":[
            {"extras":list(sig),"set_count":n,"branch_counts":dict(sorted(Counter(branch(s) for s in new if tuple(sorted(set(s)-ACTIVE15))==sig).items()))}
            for sig,n in sorted(ext_sig.items(), key=lambda kv:(len(kv[0]),kv[0]))
        ],
        "general_extension_signatures":[
            {"extras":list(sig),"set_count":n}
            for sig,n in sorted(general_sig.items(), key=lambda kv:(len(kv[0]),kv[0]))
        ],
        "terminal_rows_read":0,
        "hidden_terminal_ids_read":0,
        "hidden_kwargs_read":0,
        "acceptance_credit_delta":0,
        "hard_nonclaims":[
            "STRUCTURAL_REDUCTION_ONLY__NO_POINTWISE_SEMANTIC_CLOSURE",
            "GENERAL_EXTENSION_SIGNATURES_STILL_REQUIRE_CONSTRUCTIVE_AND_EXACT_CHECKER_PROOFS",
            "NO_LIVEBENCH_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }
    pathlib.Path("livebench_union25_structural_cut_v1.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__":
    main()
