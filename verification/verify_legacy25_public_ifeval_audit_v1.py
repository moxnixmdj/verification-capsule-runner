#!/usr/bin/env python3
# trigger-after-default-install-v1
from __future__ import annotations
import collections
import hashlib
import importlib.util
import json
import urllib.request
from pathlib import Path

DATA_URL="https://raw.githubusercontent.com/google-research/google-research/master/instruction_following_eval/data/input_data.jsonl"
DATA_GIT_BLOB="cbe52f6eecf3986fdac745b4acba4da1408eb146"
SUBJECT=Path(__file__).resolve().parent/"subjects"/"livebench_legacy25_prompt_inverter_v1__brain_de598627.py"
SUBJECT_GIT_BLOB="de598627156582ca51e2058b3b824208db9293eb"

def git_blob_sha_bytes(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load_subject():
    raw=SUBJECT.read_bytes()
    assert git_blob_sha_bytes(raw)==SUBJECT_GIT_BLOB, (git_blob_sha_bytes(raw),SUBJECT_GIT_BLOB)
    spec=importlib.util.spec_from_file_location("legacy25_subject", SUBJECT)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def norm(v):
    if isinstance(v,list):
        return sorted(norm(x) for x in v)
    if isinstance(v,dict):
        return {k:norm(v[k]) for k in sorted(v)}
    if isinstance(v,str):
        return v.strip().lower()
    return v

def main():
    raw=urllib.request.urlopen(DATA_URL,timeout=60).read()
    observed=git_blob_sha_bytes(raw)
    assert observed==DATA_GIT_BLOB,(observed,DATA_GIT_BLOB)
    rows=[json.loads(x) for x in raw.decode().splitlines() if x.strip()]
    subject=load_subject()

    expected_types=collections.Counter()
    recognized_types=collections.Counter()
    missing_types=collections.Counter()
    extra_types=collections.Counter()
    row_exact=0
    row_expected_subset=0
    ambiguous=0
    param_pairs=0
    param_agree=0
    param_disagree=[]
    recognition_failures=[]

    for row in rows:
        out=subject.recognize(row["prompt"])
        exp=list(row.get("instruction_id_list") or [])
        got=[m["instruction_id"] for m in out.get("matches",[])]
        es=set(exp); gs=set(got)
        expected_types.update(exp)
        recognized_types.update(got)
        missing_types.update(es-gs)
        extra_types.update(gs-es)
        if es==gs:
            row_exact+=1
        if es.issubset(gs):
            row_expected_subset+=1
        if out.get("status")!="PASS":
            ambiguous+=1
        if es!=gs and len(recognition_failures)<80:
            recognition_failures.append({
                "key":row.get("key"),
                "expected":sorted(es),
                "recognized":sorted(gs),
                "missing":sorted(es-gs),
                "extra":sorted(gs-es),
            })

        matches={}
        for m in out.get("matches",[]):
            matches.setdefault(m["instruction_id"],[]).append(m.get("kwargs") or {})
        for idx,iid in enumerate(exp):
            if iid=="combination:repeat_prompt":
                continue
            if iid not in matches or len(matches[iid])!=1:
                continue
            expected_kw=(row.get("kwargs") or [{}])[idx] or {}
            parsed_kw=matches[iid][0]
            # Only compare fields the parser claims to recover from visible text.
            fields=[k for k,v in parsed_kw.items() if v is not None and not k.endswith("_recovery")]
            if not fields:
                continue
            param_pairs+=1
            lhs={k:norm(parsed_kw[k]) for k in fields}
            rhs={k:norm(expected_kw.get(k)) for k in fields}
            if lhs==rhs:
                param_agree+=1
            elif len(param_disagree)<80:
                param_disagree.append({
                    "key":row.get("key"),"instruction_id":iid,
                    "parsed":lhs,"hidden_kwargs":rhs,
                })

    all25=set(subject.LEGACY_INSTRUCTION_IDS)
    present=set(expected_types)
    result={
        "schema":"PROJECT_BRAIN_LEGACY25_PUBLIC_GOOGLE_IFEVAL_AUDIT_V1",
        "status":"AUDIT_COMPLETE",
        "bindings":{
            "google_ifeval_data_url":DATA_URL,
            "google_ifeval_data_git_blob_sha":DATA_GIT_BLOB,
            "subject_git_blob_sha":SUBJECT_GIT_BLOB,
            "subject_livebench_commit":subject.PINNED_LIVEBENCH_COMMIT,
            "subject_registry_blob":subject.PINNED_REGISTRY_BLOB,
            "subject_instructions_blob":subject.PINNED_INSTRUCTIONS_BLOB,
        },
        "population":{
            "rows":len(rows),
            "expected_instruction_instances":sum(expected_types.values()),
            "expected_type_count":len(present),
            "subject_registry_type_count":len(all25),
            "public_dataset_missing_subject_types":sorted(all25-present),
        },
        "recognition":{
            "rows_exact_type_set":row_exact,
            "rows_expected_subset_of_recognized":row_expected_subset,
            "row_exact_rate":row_exact/len(rows),
            "ambiguous_fail_closed_rows":ambiguous,
            "missing_by_type":dict(sorted(missing_types.items())),
            "extra_by_type":dict(sorted(extra_types.items())),
            "recognized_by_type":dict(sorted(recognized_types.items())),
            "expected_by_type":dict(sorted(expected_types.items())),
        },
        "visible_parameter_crosscheck":{
            "compared_instances":param_pairs,
            "agreement_instances":param_agree,
            "agreement_rate":(param_agree/param_pairs if param_pairs else None),
            "disagreements":param_disagree,
            "note":"Disagreement is reported, not automatically charged to the prompt parser, because the public Google corpus is known to contain prompt/hidden-kwargs inconsistencies.",
        },
        "recognition_failures":recognition_failures,
        "hard_nonclaims":[
            "PUBLIC_GOOGLE_IFEVAL_CORPUS_IS_NONTERMINAL_EVIDENCE_ONLY",
            "NO_FROZEN_LIVEBENCH_TERMINAL_PROMPT_OR_RESPONSE_CONTENT_READ",
            "NO_ACCEPTANCE_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT",
            "PUBLIC_GOOGLE_IFEVAL_WORDING_NEED_NOT_EQUAL_FROZEN_LIVEBENCH_RENDERING",
        ],
    }
    Path("legacy25_public_ifeval_audit_v1.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "rows":len(rows),
        "row_exact":row_exact,
        "row_exact_rate":row_exact/len(rows),
        "expected_subset":row_expected_subset,
        "missing_by_type":dict(sorted(missing_types.items())),
        "extra_by_type":dict(sorted(extra_types.items())),
        "param_pairs":param_pairs,
        "param_agree":param_agree,
        "param_rate":param_agree/param_pairs if param_pairs else None,
    },indent=2,sort_keys=True))

if __name__=="__main__":
    main()
