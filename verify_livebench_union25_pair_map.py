#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"subject"))
sys.path.insert(0,str(ROOT/"upstream"))

from canonical.runtime import livebench_legacy_ifeval_constructive_solver_v1 as solver
from instruction_following_eval import instructions_registry as registry

BASE_REQUEST="Explain why deterministic verification matters"
SAMPLE_ARGS={
 "keywords:existence":{"keywords":["alpha","beta"]},
 "keywords:frequency":{"keyword":"alpha","frequency":3,"relation":"at least"},
 "keywords:forbidden_words":{"forbidden_words":["omega","zeta"]},
 "keywords:letter_frequency":{"letter":"q","let_frequency":4,"let_relation":"less than"},
 "language:response_language":{"language":"en"},
 "length_constraints:number_sentences":{"num_sentences":4,"relation":"at least"},
 "length_constraints:number_paragraphs":{"num_paragraphs":3},
 "length_constraints:number_words":{"num_words":17,"relation":"at least"},
 "length_constraints:nth_paragraph_first_word":{"num_paragraphs":3,"nth_paragraph":2,"first_word":"alpha"},
 "detectable_content:number_placeholders":{"num_placeholders":3},
 "detectable_content:postscript":{"postscript_marker":"P.S."},
 "detectable_format:number_bullet_lists":{"num_bullets":4},
 "detectable_format:constrained_response":{},
 "detectable_format:number_highlighted_sections":{"num_highlights":3},
 "detectable_format:multiple_sections":{"section_spliter":"Section","num_sections":3},
 "detectable_format:json_format":{},
 "detectable_format:title":{},
 "combination:two_responses":{},
 "combination:repeat_prompt":{"prompt_to_repeat":BASE_REQUEST},
 "startend:end_checker":{"end_phrase":"Any other questions?"},
 "change_case:capital_word_frequency":{"capital_frequency":3,"capital_relation":"at least"},
 "change_case:english_capital":{},
 "change_case:english_lowercase":{},
 "punctuation:no_comma":{},
 "startend:quotation":{},
}

def main():
    ids=list(registry.INSTRUCTION_DICT)
    assert len(ids)==25 and set(ids)==set(SAMPLE_ARGS)
    conflicts=registry.conflict_make(copy.deepcopy(registry.INSTRUCTION_CONFLICTS))
    descriptions={}
    checkers={}
    for iid in ids:
        obj=registry.INSTRUCTION_DICT[iid](iid)
        descriptions[iid]=obj.build_description(**SAMPLE_ARGS[iid])
        checkers[iid]=obj

    compatible=[]
    blocked=[]
    invalid=[]
    exceptions=[]
    full=0
    orientations=0
    for i,a in enumerate(ids):
        for b in ids[i+1:]:
            if b in conflicts[a] or a in conflicts[b]:
                continue
            compatible.append((a,b))
            for order in ((a,b),(b,a)):
                orientations+=1
                prompt=BASE_REQUEST+"\n"+descriptions[order[0]]+"\n"+descriptions[order[1]]
                try:
                    out=solver.synthesize(prompt)
                    if not str(out.get("status","")).startswith("CANDIDATE_PASS"):
                        blocked.append({"pair":[a,b],"order":list(order),"reason":out.get("reason"),
                                        "recognized":out.get("recognized_instruction_ids")})
                        continue
                    response=str(out.get("response") or "")
                    va=bool(checkers[a].check_following(response))
                    vb=bool(checkers[b].check_following(response))
                    if va and vb:
                        full+=1
                    else:
                        invalid.append({"pair":[a,b],"order":list(order),
                                        "verdicts":{a:va,b:vb},
                                        "recognized":out.get("recognized_instruction_ids"),
                                        "dominant_shape":out.get("dominant_shape"),
                                        "response":response[:500]})
                except Exception as exc:
                    exceptions.append({"pair":[a,b],"order":list(order),
                                       "type":type(exc).__name__,"message":str(exc)[:500]})

    gap_pairs=sorted({tuple(x["pair"]) for x in blocked+invalid+exceptions})
    by_family={iid:{"compatible_pair_count":0,"gap_pair_count":0} for iid in ids}
    for a,b in compatible:
        by_family[a]["compatible_pair_count"]+=1
        by_family[b]["compatible_pair_count"]+=1
    for a,b in gap_pairs:
        by_family[a]["gap_pair_count"]+=1
        by_family[b]["gap_pair_count"]+=1

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_UNION25_REPRESENTATIVE_PAIR_MAP_V1",
      "status":"PASS__ALL_REPRESENTATIVE_COMPATIBLE_PAIRS" if not gap_pairs else "FAIL__REPRESENTATIVE_PAIR_GAPS_FOUND",
      "subject":{
        "brain_pr":1774,
        "solver_blob":"45ad0f2b3818ef733cb4d3c9fb92c28d1e24cddb",
        "inverter_blob":"74904d2a00ed3f0bb2e8ab7787c59c0a8f828f7a",
      },
      "pinned_livebench_commit":"8f8e5c381a16e3f24257776edd53471fe86f8091",
      "registry_family_count":len(ids),
      "compatible_unordered_pairs":len(compatible),
      "tested_orientations":orientations,
      "full_exact_checker_pass_orientations":full,
      "blocked_orientations":len(blocked),
      "invalid_witness_orientations":len(invalid),
      "exception_orientations":len(exceptions),
      "gap_unordered_pairs":len(gap_pairs),
      "gap_pairs":[list(x) for x in gap_pairs],
      "by_family":by_family,
      "blocked_examples":blocked[:100],
      "invalid_examples":invalid[:100],
      "exception_examples":exceptions[:100],
      "terminal_rows_read":0,
      "terminal_kwargs_read":0,
      "terminal_scores_read":0,
      "models_used":0,
      "incremental_spend_usd":0,
      "hard_nonclaim":"REPRESENTATIVE_SLOT_PAIR_MAP_ONLY__NOT_UNIVERSAL_SLOT_OR_N_WAY_CLOSURE",
    }
    pathlib.Path("livebench_union25_pair_map_receipt.json").write_text(
      json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    if gap_pairs:
        raise SystemExit(1)
    print("LIVEBENCH_UNION25_REPRESENTATIVE_PAIR_MAP=PASS")

if __name__=="__main__":
    main()
