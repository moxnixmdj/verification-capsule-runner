#!/usr/bin/env python3
from __future__ import annotations
import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import pyarrow.parquet as pq

REV="4f7ab12f0d47848da31de92bd7cc3d7d4acfe695"
SHA256="57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
BYTES=277319
ROWS=200
V1_BLOB="e986035ff68b53c0dc7a7eb478f6e3d8882214aa"
V2_BLOB="0e7519f4f2b7d40084effc83a5bef814ee7fd487"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def canon(v):
    if isinstance(v,str):
        return v.strip()
    if isinstance(v,list):
        return [canon(x) for x in v]
    if isinstance(v,tuple):
        return [canon(x) for x in v]
    return v


def prompt_of(row):
    turns=row.get("turns")
    if isinstance(turns,list) and turns:
        return str(turns[0])
    return str(row.get("prompt") or "")


def main():
    v1=Path("subject/canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py")
    v2=Path("subject/canonical/runtime/livebench_legacy_visible_constraint_compiler_v2.py")
    assert git_blob_sha(v1.read_bytes())==V1_BLOB
    assert git_blob_sha(v2.read_bytes())==V2_BLOB
    sys.path.insert(0,str(Path("subject").resolve()))
    from canonical.runtime import livebench_legacy_visible_constraint_compiler_v2 as compiler

    url=f"https://huggingface.co/datasets/livebench/instruction_following/resolve/{REV}/data/test-00000-of-00001.parquet?download=true"
    p=Path("/tmp/predecessor.parquet")
    subprocess.run(["curl","--fail","--location","--retry","3","--silent","--show-error",url,"-o",str(p)],check=True)
    raw=p.read_bytes()
    assert len(raw)==BYTES,(len(raw),BYTES)
    assert hashlib.sha256(raw).hexdigest()==SHA256
    rows=pq.read_table(p).to_pylist()
    assert len(rows)==ROWS

    expected_total=0
    recovered_total=0
    exact_rows=0
    all_expected_rows=0
    exact_kwargs_instances=0
    kwargs_instances=0
    parse_fail_rows=0
    parameter_incomplete_rows=0
    expected_families=collections.Counter()
    missing_families=collections.Counter()
    extra_families=collections.Counter()
    kwarg_mismatch_families=collections.Counter()
    task_counts=collections.Counter()
    release_counts=collections.Counter()
    removal_counts=collections.Counter()

    for row in rows:
        task_counts[str(row.get("task") or "")]+=1
        release_counts[str(row.get("livebench_release_date") or "")[:10]]+=1
        removal_counts[str(row.get("livebench_removal_date") or "")[:10]]+=1
        prompt=prompt_of(row)
        expected_ids=[str(x) for x in (row.get("instruction_id_list") or [])]
        expected_kwargs=list(row.get("kwargs") or [])
        assert len(expected_ids)==len(expected_kwargs)
        expected_total+=len(expected_ids)
        expected_families.update(expected_ids)

        out=compiler.compile_visible_constraints(prompt)
        if out.get("status")!="PASS":
            parse_fail_rows+=1
        if not out.get("all_recognized_parameters_complete"):
            parameter_incomplete_rows+=1
        constraints=list(out.get("constraints") or [])
        observed_ids=[str(x.get("instruction_id")) for x in constraints]
        E=collections.Counter(expected_ids)
        O=collections.Counter(observed_ids)
        overlap=E&O
        recovered_total+=sum(overlap.values())
        missing_families.update(list((E-O).elements()))
        extra_families.update(list((O-E).elements()))
        if overlap==E:
            all_expected_rows+=1
        if O==E:
            exact_rows+=1

        by_id=collections.defaultdict(list)
        for c in constraints:
            by_id[str(c.get("instruction_id"))].append(c)
        used=collections.Counter()
        for i,instruction_id in enumerate(expected_ids):
            occurrence=used[instruction_id]
            used[instruction_id]+=1
            candidates=by_id.get(instruction_id,[])
            if occurrence>=len(candidates):
                continue
            hidden={k:v for k,v in dict(expected_kwargs[i] or {}).items() if v is not None}
            slots=dict(candidates[occurrence].get("slots") or {})
            kwargs_instances+=1
            # Compare exactly the scorer-relevant historical kwargs. Extra human-readable
            # slots such as language_name are allowed but cannot substitute for a hidden key.
            observed={k:slots.get(k) for k in hidden}
            if canon(observed)==canon(hidden):
                exact_kwargs_instances+=1
            else:
                kwarg_mismatch_families[instruction_id]+=1

    strict=(
        recovered_total==expected_total
        and exact_rows==ROWS
        and exact_kwargs_instances==kwargs_instances==expected_total
        and parse_fail_rows==0
        and parameter_incomplete_rows==0
        and not missing_families
        and not extra_families
        and not kwarg_mismatch_families
    )
    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY_V2_PREDECESSOR_REPLAY_V1",
      "status":"PASS__STRICT_PREDECESSOR_REPLAY" if strict else "MEASUREMENT_COMPLETE__STRICT_PREDECESSOR_REPLAY_NOT_CLOSED",
      "subject":{
        "v1_git_blob_sha":V1_BLOB,
        "v2_git_blob_sha":V2_BLOB,
        "runtime_inputs":"VISIBLE_PROMPT_ONLY",
        "hidden_instruction_ids_used_by_subject":False,
        "hidden_kwargs_used_by_subject":False,
      },
      "historical_predecessor":{
        "repository":"livebench/instruction_following",
        "revision":REV,
        "sha256":SHA256,
        "bytes":BYTES,
        "rows":ROWS,
      },
      "results":{
        "strict_success":strict,
        "expected_instruction_instances":expected_total,
        "recognized_expected_instruction_instances":recovered_total,
        "instruction_instance_recall":recovered_total/expected_total if expected_total else 1.0,
        "rows_all_expected_recognized":all_expected_rows,
        "rows_exact_instruction_multiset":exact_rows,
        "score_relevant_kwarg_instances_compared":kwargs_instances,
        "score_relevant_kwarg_instances_exact":exact_kwargs_instances,
        "parse_fail_rows":parse_fail_rows,
        "parameter_incomplete_rows":parameter_incomplete_rows,
        "actual_instruction_family_count":len(expected_families),
        "actual_instruction_families":sorted(expected_families),
        "expected_family_counts":dict(sorted(expected_families.items())),
        "missing_family_counts":dict(sorted(missing_families.items())),
        "extra_family_counts":dict(sorted(extra_families.items())),
        "kwarg_mismatch_family_counts":dict(sorted(kwarg_mismatch_families.items())),
        "task_counts":dict(sorted(task_counts.items())),
        "release_date_counts":dict(sorted(release_counts.items())),
        "removal_date_counts":dict(sorted(removal_counts.items())),
      },
      "hard_nonclaims":[
        "NO_ACTIVE_2024_11_25_TERMINAL_PROMPT_READ",
        "NO_ACTIVE_TERMINAL_CASE_ID_OR_KWARG_READ",
        "NO_ACTIVE_TERMINAL_SCORE_CLAIM",
        "NO_BYTE_LEVEL_PROOF_THAT_2024_11_25_GENERATOR_IS_IDENTICAL_TO_PREDECESSOR",
        "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
      ],
      "accounting":{"incremental_spend_usd":0,"current_active_terminal_cases_consumed":0,"acceptance_credit_delta":0},
    }
    Path("livebench_legacy_v2_predecessor_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__":
    main()
