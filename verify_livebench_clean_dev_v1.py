#!/usr/bin/env python3
import collections, hashlib, json, os, random, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/tmp/LiveBench/livebench/if_runner")
from instruction_following_eval import instructions_registry as registry

from canonical.runtime import livebench_legacy25_clean_witness_v1 as candidate

NP_SEED=2026100401
PY_SEED=2026100402
N=200
ALL_CONSTRAINTS=[
 "length_constraints:number_sentences","length_constraints:number_paragraphs",
 "length_constraints:number_words","length_constraints:nth_paragraph_first_word",
 "keywords:existence","keywords:frequency","keywords:forbidden_words","keywords:letter_frequency",
 "detectable_content:number_placeholders","detectable_content:postscript",
 "detectable_format:number_bullet_lists","detectable_format:constrained_response",
 "detectable_format:number_highlighted_sections","detectable_format:multiple_sections",
 "detectable_format:json_format","detectable_format:title",
 "combination:two_responses","combination:repeat_prompt",
 "startend:end_checker","startend:quotation",
 "change_case:capital_word_frequency","change_case:english_capital","change_case:english_lowercase",
 "punctuation:no_comma",
]
TASK_PROMPTS=[
 "Please paraphrase based on the sentences provided.",
 "Please summarize based on the sentences provided.",
 "Please explain in simpler terms what this text means.",
 "Please generate a story based on the sentences provided.",
]

def disallowed_pairs(conflicts):
    out=[]
    for key in conflicts:
        for value in conflicts[key]:
            out.append([key,value])
    return out

def generate_instruction_lists():
    np.random.seed(NP_SEED)
    random.seed(PY_SEED)
    draws=np.random.randint(2,6,N)
    raw=[np.random.choice(ALL_CONSTRAINTS,int(draw),replace=False).tolist() for draw in draws]
    created=disallowed_pairs(registry.INSTRUCTION_CONFLICTS)
    original=created.copy()
    out=[]
    for instruction_set in raw:
        xs=instruction_set.copy()
        np.random.shuffle(created)
        for pair in created:
            if set(pair).issubset(set(xs)) and len(set(pair)) != 1:
                removed=np.random.choice(pair)
                xs.remove(removed)
        created=original.copy()
        out.append(list(set(xs)))
    return out

def generate_case(i, ids):
    kwargs_all=[]
    combined=""
    for iid in ids:
        obj=registry.INSTRUCTION_DICT[iid](iid)
        txt=obj.build_description()
        kw=obj.get_instruction_args()
        if kw is None:
            kw={}
        kwargs_all.append(kw)
        combined+=" "+txt
    task=TASK_PROMPTS[i//50]
    article=(
      f"Synthetic clean article {i} contains neutral public nonterminal text. "
      f"It exists only to occupy the historical article envelope and is never scored semantically."
    )
    prompt=(
      "The following are the beginning sentences of a news article from the Guardian.\n"
      "-------\n"+article+"\n-------\n"+task+" "+combined
    )
    if "combination:repeat_prompt" in ids:
        idx=ids.index("combination:repeat_prompt")
        kwargs_all[idx]["prompt_to_repeat"]=prompt.split(
          "First repeat the request word for word without change,"
        )[0]
    return prompt, kwargs_all, task

def score_case(prompt, ids, kwargs_all):
    result=candidate.solve(prompt)
    response=result.get("response")
    if not isinstance(response,str):
        return 0.0, [], result
    checks=[]
    for iid,kw in zip(ids,kwargs_all):
        try:
            obj=registry.INSTRUCTION_DICT[iid](iid)
            obj.build_description(**kw)
            checks.append(bool(obj.check_following(response)))
        except Exception as exc:
            checks.append(False)
    if not checks:
        return 0.0, checks, result
    strict=1.0 if all(checks) else 0.0
    loose=sum(checks)/len(checks)
    return (strict+loose)/2.0, checks, result

def main():
    assert os.environ.get("PYTHONHASHSEED")=="0"
    assert len(ALL_CONSTRAINTS)==25
    assert set(ALL_CONSTRAINTS)==set(registry.INSTRUCTION_DICT.keys())
    ids_list=generate_instruction_lists()
    scores=[]
    error_counts=collections.Counter()
    instruction_seen=collections.Counter()
    instruction_failed=collections.Counter()
    strict_pass=0
    case_digest=hashlib.sha256()
    case_summaries=[]
    for i,ids in enumerate(ids_list):
        prompt,kwargs_all,task=generate_case(i,ids)
        case_digest.update(json.dumps(
          {"i":i,"ids":ids,"kwargs":kwargs_all,"prompt":prompt},
          ensure_ascii=False,sort_keys=True
        ).encode())
        score,checks,result=score_case(prompt,ids,kwargs_all)
        scores.append(score)
        if score==1.0:
            strict_pass+=1
        if result.get("status")!="PASS_CANDIDATE_CLEAN_SOURCE_DERIVED":
            error_counts[str(result.get("error") or result.get("status"))]+=1
        for iid,ok in zip(ids,checks):
            instruction_seen[iid]+=1
            if not ok:
                instruction_failed[iid]+=1
        case_summaries.append({
          "i":i,"constraint_count":len(ids),"score":score,
          "candidate_status":result.get("status"),
          "candidate_error":result.get("error"),
          "failed_instruction_ids":[iid for iid,ok in zip(ids,checks) if not ok],
        })
    mean=sum(scores)/len(scores)
    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_CLEAN_EQUIVALENT_DEVELOPMENT_RESULT_V1",
      "status":"DEVELOPMENT_RESULT_ONLY__NO_ACCEPTANCE_CREDIT",
      "population_count":N,
      "numpy_seed":NP_SEED,
      "python_random_seed":PY_SEED,
      "python_hash_seed":0,
      "clean_population_sha256":case_digest.hexdigest(),
      "target_dataset_rows_used":0,
      "target_question_ids_used":0,
      "mean_score":mean,
      "strict_full_case_pass_count":strict_pass,
      "strict_full_case_pass_rate":strict_pass/N,
      "candidate_error_counts":dict(error_counts),
      "instruction_seen_counts":dict(sorted(instruction_seen.items())),
      "instruction_failed_counts":dict(sorted(instruction_failed.items())),
      "case_summaries":case_summaries,
      "candidate_acceptance_credit":False,
      "development_population_may_not_be_used_for_acceptance":True,
    }
    Path("livebench_clean_dev_v1_receipt.json").write_text(
      json.dumps(receipt,indent=2,sort_keys=True)+"\n"
    )
    print(json.dumps({
      "status":receipt["status"],"mean_score":mean,
      "strict_pass_count":strict_pass,"errors":dict(error_counts),
      "failed":dict(sorted(instruction_failed.items()))
    },sort_keys=True))
if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        diag={
          "schema":"PROJECT_BRAIN_LIVEBENCH_CLEAN_DEV_V1_DIAGNOSTIC",
          "status":"DEVELOPMENT_HARNESS_EXCEPTION",
          "exception_type":type(exc).__name__,
          "exception":str(exc),
          "traceback":traceback.format_exc(),
          "target_dataset_rows_used":0,
          "acceptance_credit":False,
        }
        Path("livebench_clean_dev_v1_receipt.json").write_text(
          json.dumps(diag,indent=2,sort_keys=True)+"\\n"
        )
        print(json.dumps(diag,sort_keys=True))
        raise
