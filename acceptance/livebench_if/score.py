#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, pathlib, sys
import pyarrow.parquet as pq

DATASET=pathlib.Path(os.environ.get("LIVEBENCH_IF_DATASET","/tmp/livebench_if.parquet"))
CONFIGURED=pathlib.Path(os.environ.get("CONFIGURED_OUT","configured_responses.jsonl"))
ABLATION=pathlib.Path(os.environ.get("ABLATION_OUT","ablation_responses.jsonl"))
LIVEBENCH_ROOT=pathlib.Path(os.environ.get("LIVEBENCH_ROOT","/tmp/livebench"))
sys.path.insert(0,str(LIVEBENCH_ROOT))
from livebench.if_runner.ifbench import evaluation_lib

THRESHOLD=0.657

def _load_responses(path):
    rows=[json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    out={}
    for row in rows:
        qid=str(row["question_id"])
        if qid in out: raise RuntimeError("DUPLICATE_RESPONSE_ID")
        out[qid]=row["response"]
    return out

def _score(response_map, data_rows):
    prompt_total=prompt_correct=instruction_total=instruction_correct=0
    by_id={}
    for row in data_rows:
        qid=str(row["question_id"])
        if qid not in response_map: continue
        turns=row["turns"]
        inp=evaluation_lib.InputExample(
            key=qid,
            instruction_id_list=list(row["instruction_id_list"]),
            prompt=turns[0],
            kwargs=[dict(x) for x in row["kwargs"]],
        )
        o=evaluation_lib.test_instruction_following_loose(inp,response_map[qid])
        prompt_total+=1
        prompt_correct+=int(o.follow_all_instructions)
        instruction_total+=len(o.follow_instruction_list)
        instruction_correct+=sum(bool(x) for x in o.follow_instruction_list)
        by_id[qid]={
            "follow_all_instructions":bool(o.follow_all_instructions),
            "instruction_count":len(o.follow_instruction_list),
            "instruction_pass_count":sum(bool(x) for x in o.follow_instruction_list),
        }
    return {
        "prompt_total":prompt_total,
        "prompt_correct":prompt_correct,
        "prompt_accuracy":prompt_correct/prompt_total if prompt_total else 0,
        "instruction_total":instruction_total,
        "instruction_correct":instruction_correct,
        "instruction_accuracy":instruction_correct/instruction_total if instruction_total else 0,
        "per_question":by_id,
    }

def main():
    table=pq.read_table(DATASET)
    rows=table.to_pylist()
    if len(rows)!=400: raise RuntimeError("DATASET_ROW_COUNT_NOT_400")
    configured=_load_responses(CONFIGURED)
    if len(configured)!=400: raise RuntimeError("CONFIGURED_RESPONSE_COUNT_NOT_400")
    ablation=_load_responses(ABLATION)
    if len(ablation)!=40: raise RuntimeError("ABLATION_RESPONSE_COUNT_NOT_40")

    c=_score(configured,rows)
    a=_score(ablation,rows)
    result={
        "schema":"PROJECT_BRAIN_LIVEBENCH_IF_PUBLIC_BAR_RESULT_V1",
        "metric":"LOOSE_PROMPT_LEVEL_ACCURACY",
        "threshold":THRESHOLD,
        "configured":{
            "prompt_total":c["prompt_total"],
            "prompt_correct":c["prompt_correct"],
            "prompt_accuracy":c["prompt_accuracy"],
            "instruction_total":c["instruction_total"],
            "instruction_correct":c["instruction_correct"],
            "instruction_accuracy":c["instruction_accuracy"],
        },
        "ablation_40":{
            "prompt_total":a["prompt_total"],
            "prompt_correct":a["prompt_correct"],
            "prompt_accuracy":a["prompt_accuracy"],
            "instruction_total":a["instruction_total"],
            "instruction_correct":a["instruction_correct"],
            "instruction_accuracy":a["instruction_accuracy"],
            "acceptance_role":"NONE__DIAGNOSTIC_ONLY",
        },
        "pass":c["prompt_total"]==400 and c["prompt_accuracy"]>=THRESHOLD,
        "candidate_hidden_evaluator_information_consumed":False,
        "terminal_v3_replay":False,
        "incremental_spend_usd":0,
        "configured_response_sha256":hashlib.sha256(CONFIGURED.read_bytes()).hexdigest(),
        "ablation_response_sha256":hashlib.sha256(ABLATION.read_bytes()).hexdigest(),
    }
    pathlib.Path("livebench_if_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    pathlib.Path("livebench_if_per_question.json").write_text(json.dumps(c["per_question"],sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    if not result["pass"]:
        raise SystemExit(2)

if __name__=="__main__":
    main()
