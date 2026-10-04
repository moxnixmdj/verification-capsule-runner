#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, importlib.util, json, urllib.request
from pathlib import Path

DATA_URL="https://raw.githubusercontent.com/google-research/google-research/e49bbfe381c9c0e564b937f1c4e163a2273c65cc/instruction_following_eval/data/input_data.jsonl"
DATA_BLOB="cbe52f6eecf3986fdac745b4acba4da1408eb146"
SUBJECT=Path(__file__).resolve().parent/"subjects"/"livebench_legacy_paraphrase_inverter_v1__brain_3bfedacc.py"
SUBJECT_BLOB="3bfedaccbe5471d735134575a976cb82426e3497"

CASE_INSENSITIVE_FIELDS={"keyword","letter","first_word","end_phrase","postscript_marker","section_spliter","language"}
LIST_CASE_INSENSITIVE_FIELDS={"keywords","forbidden_words"}

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load_subject():
    raw=SUBJECT.read_bytes()
    assert git_blob(raw)==SUBJECT_BLOB,(git_blob(raw),SUBJECT_BLOB)
    spec=importlib.util.spec_from_file_location("subject",SUBJECT)
    mod=importlib.util.module_from_spec(spec); assert spec and spec.loader
    spec.loader.exec_module(mod); return mod

def norm_kw(iid:str, kw:dict)->dict:
    out={}
    for k,v in (kw or {}).items():
        if v is None or k.endswith("_recovery"):
            continue
        if isinstance(v,str):
            v=v.strip()
            if k in CASE_INSENSITIVE_FIELDS:
                v=v.lower()
        elif isinstance(v,list):
            if k in LIST_CASE_INSENSITIVE_FIELDS:
                v=sorted(str(x).strip().lower() for x in v)
            else:
                v=sorted(v)
        out[k]=v
    return {k:out[k] for k in sorted(out)}

def atom(iid,kw):
    return json.dumps([iid,norm_kw(iid,kw)],sort_keys=True,ensure_ascii=False)

def main():
    raw=urllib.request.urlopen(DATA_URL,timeout=60).read()
    assert git_blob(raw)==DATA_BLOB,(git_blob(raw),DATA_BLOB)
    rows=[json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    subject=load_subject()
    family_expected=collections.Counter()
    family_good=collections.Counter()
    family_missing=collections.Counter()
    family_extra=collections.Counter()
    exact_rows=0
    type_exact_rows=0
    failures=[]
    unresolved_rows=0

    for row in rows:
        exp_atoms=[]
        for iid,kw in zip(row["instruction_id_list"],row["kwargs"]):
            exp_atoms.append(atom(iid,kw or {}))
            family_expected[iid]+=1
        out=subject.recognize(row["prompt"])
        got_atoms=[atom(m["instruction_id"],m.get("kwargs") or {}) for m in out.get("matches",[])]
        ec=collections.Counter(exp_atoms); gc=collections.Counter(got_atoms)
        if ec==gc:
            exact_rows+=1
            for iid in row["instruction_id_list"]: family_good[iid]+=1
        et=collections.Counter(row["instruction_id_list"])
        gt=collections.Counter(m["instruction_id"] for m in out.get("matches",[]))
        if et==gt: type_exact_rows+=1
        if out.get("unresolved_parameter_cues"): unresolved_rows+=1

        missing=ec-gc; extra=gc-ec
        for s,n in missing.items():
            iid=json.loads(s)[0]; family_missing[iid]+=n
        for s,n in extra.items():
            iid=json.loads(s)[0]; family_extra[iid]+=n
        if (missing or extra) and len(failures)<180:
            failures.append({
                "key":row.get("key"),
                "expected_ids":list(row["instruction_id_list"]),
                "recognized_ids":[m["instruction_id"] for m in out.get("matches",[])],
                "missing_atoms":[{"atom":json.loads(s),"count":n} for s,n in missing.items()],
                "extra_atoms":[{"atom":json.loads(s),"count":n} for s,n in extra.items()],
                "unresolved":out.get("unresolved_parameter_cues") or [],
            })

    receipt={
        "schema":"PROJECT_BRAIN_LEGACY_PARAPHRASE_INVERTER_PUBLIC_AUDIT_V1",
        "status":"PASS_541_OF_541_EXACT" if exact_rows==len(rows) else "FAIL_CLOSED_REPAIR_LEDGER",
        "bindings":{"data_blob":DATA_BLOB,"subject_blob":SUBJECT_BLOB},
        "population":{"rows":len(rows),"instruction_instances":sum(family_expected.values()),"families":len(family_expected)},
        "results":{
            "exact_rows":exact_rows,
            "exact_row_fraction":exact_rows/len(rows),
            "type_multiset_exact_rows":type_exact_rows,
            "type_multiset_exact_fraction":type_exact_rows/len(rows),
            "unresolved_parameter_rows":unresolved_rows,
            "expected_by_family":dict(sorted(family_expected.items())),
            "missing_by_family":dict(sorted(family_missing.items())),
            "extra_by_family":dict(sorted(family_extra.items())),
        },
        "failures":failures,
        "hard_nonclaims":[
            "PUBLIC_CLASSIC_IFEVAL_IS_NONTERMINAL_ONLY",
            "NO_FROZEN_LIVEBENCH_PROMPT_CONTENT_READ",
            "NO_TERMINAL_ACCEPTANCE_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "accounting":{"incremental_spend_usd":0,"new_terminal_cases_exposed":0,"acceptance_credit_delta":0}
    }
    Path("legacy_paraphrase_inverter_public_audit_v1.json").write_text(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    print(json.dumps({k:receipt["results"][k] for k in ("exact_rows","exact_row_fraction","type_multiset_exact_rows","type_multiset_exact_fraction","unresolved_parameter_rows","missing_by_family","extra_by_family")},indent=2,sort_keys=True))
    # The audit job succeeds even for candidate failure so the repair ledger is durable.
    # Promotion logic must inspect receipt.status, never CI green alone.

if __name__=="__main__":
    main()

# trigger: audit subject after workflow installation
