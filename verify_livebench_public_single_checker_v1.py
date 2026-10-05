#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import types
from collections import Counter

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject"/"livebench_public_single_checker_v1"/"livebench_if_public_single_checker_witness_v1.py"
EXPECTED_SUBJECT_BLOB="2d7da2b60f64151c99da4eabe4e4d532a99853c3"
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
IFBENCH_COMMIT="1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d"

def git_blob_sha(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load_subject():
    observed=git_blob_sha(SUBJECT)
    if observed!=EXPECTED_SUBJECT_BLOB:
        raise AssertionError(f"SUBJECT_BLOB_DRIFT:{observed}:{EXPECTED_SUBJECT_BLOB}")
    spec=importlib.util.spec_from_file_location("subject_livebench_single_checker",SUBJECT)
    if spec is None or spec.loader is None:
        raise RuntimeError("SUBJECT_IMPORT_SPEC_FAILED")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def install_dead_spacy_stub():
    spacy=types.ModuleType("spacy")
    spacy.util=types.SimpleNamespace(is_package=lambda _name: True)
    spacy_cli=types.ModuleType("spacy.cli")
    spacy_cli.download=lambda _name: (_ for _ in ()).throw(RuntimeError("DEAD_SPACY_PATH_INVOKED"))
    sys.modules["spacy"]=spacy
    sys.modules["spacy.cli"]=spacy_cli

def main()->int:
    lb=pathlib.Path(os.environ["LIVEBENCH_ROOT"])
    data_path=pathlib.Path(os.environ["IFBENCH_DATA"])
    sys.path.insert(0,str(lb))
    install_dead_spacy_stub()

    from livebench.if_runner.ifbench.evaluation_lib import InputExample, test_instruction_following_strict

    subject=load_subject()
    rows=[json.loads(line) for line in data_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows)!=300:
        raise AssertionError(f"PUBLIC_ROW_COUNT_DRIFT:{len(rows)}")

    activated=0
    full_pass=0
    score_mass=0.0
    blocked=0
    multi_activations=[]
    rejected=[]
    status_counts=Counter()
    checker_activations=Counter()

    for row in rows:
        prompt=str(row["prompt"])
        cand=subject.construct_single_checker_witness(prompt)
        status=str(cand.get("status"))
        status_counts[status]+=1
        if status!="PASS_CANDIDATE":
            blocked+=1
            continue

        activated+=1
        checker_id=str(cand.get("checker_id"))
        checker_activations[checker_id]+=1
        ids=list(row["instruction_id_list"])
        if len(ids)!=1:
            multi_activations.append({"key":row["key"],"ids":ids,"checker_id":checker_id})
            continue

        inp=InputExample(
            key=int(row["key"]),
            instruction_id_list=ids[:],
            prompt=prompt,
            kwargs=copy.deepcopy(row["kwargs"]),
        )
        out=test_instruction_following_strict(inp,str(cand.get("response") or ""))
        s=sum(bool(x) for x in out.follow_instruction_list)
        k=len(out.follow_instruction_list)
        score=(int(out.follow_all_instructions)+(s/k))/2.0
        score_mass+=score
        if out.follow_all_instructions:
            full_pass+=1
        else:
            rejected.append({
                "key":row["key"],
                "ids":ids,
                "checker_id":checker_id,
                "follow":out.follow_instruction_list,
                "response":cand.get("response"),
            })

    result={
        "schema":"PROJECT_BRAIN_LIVEBENCH_PUBLIC_SINGLE_CHECKER_V1_EXACT_PUBLIC_SCORER_VERIFICATION",
        "conclusion":"PASS" if not multi_activations and not rejected and score_mass/300>=0.657 else "FAIL",
        "subject_blob":EXPECTED_SUBJECT_BLOB,
        "livebench_commit":LIVEBENCH_COMMIT,
        "ifbench_commit":IFBENCH_COMMIT,
        "public_rows":300,
        "activated_rows":activated,
        "blocked_rows":blocked,
        "full_pass_rows":full_pass,
        "score_mass":score_mass,
        "score_percent":100.0*score_mass/300.0,
        "threshold_percent":65.7,
        "multi_instruction_activations":multi_activations,
        "official_scorer_rejections":rejected,
        "status_counts":dict(status_counts),
        "checker_activations":dict(sorted(checker_activations.items())),
        "terminal_cases_consumed":0,
        "acceptance_credit_delta":0,
    }
    pathlib.Path("livebench_public_single_checker_v1_receipt.json").write_text(
        json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8"
    )
    print(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False))

    if multi_activations:
        raise AssertionError(f"MULTI_INSTRUCTION_ACTIVATION:{len(multi_activations)}")
    if rejected:
        raise AssertionError(f"OFFICIAL_SCORER_REJECTIONS:{len(rejected)}")
    if score_mass/300 < 0.657:
        raise AssertionError(f"PUBLIC_SCORE_BELOW_65_7:{100*score_mass/300:.6f}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
