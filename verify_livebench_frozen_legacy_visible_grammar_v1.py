#!/usr/bin/env python3
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

DATASET_REV = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
DATASET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
DATASET_BYTES = 537024
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
LEGACY_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
LEGACY_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
LEGACY_EVAL_BLOB = "4a341984936c4d609644a3b77f8c030ac5aa7269"
POPULATION = 200
FROZEN_RELEASE = "2026-06-25"

ACTIVE = {
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
}
ACTIVE_COMMITMENT = "af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    cp = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if cp.returncode != 0:
        raise RuntimeError("SUBPROCESS_FAILED")
    return cp


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip()).casefold()


def iso(v) -> str:
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.strftime("%Y-%m-%d")
    return "" if v is None else str(v)[:10]


def selected_rows(parquet: Path) -> list[dict]:
    import pyarrow.parquet as pq

    valid = {
        "2024-06-24","2024-07-26","2024-08-31","2024-11-25",
        "2025-04-02","2025-04-25","2025-05-30","2025-11-25",
        "2025-12-23","2026-01-08","2026-06-25",
    }
    rows = pq.read_table(parquet).to_pylist()
    out = []
    for q in rows:
        release = iso(q.get("livebench_release_date"))
        removal = iso(q.get("livebench_removal_date"))
        if release not in valid:
            continue
        if removal and removal <= FROZEN_RELEASE:
            continue
        if q.get("category") != "instruction_following":
            continue
        out.append(q)
    out.sort(key=lambda q: str(q["question_id"]))
    if len(out) != POPULATION:
        raise RuntimeError("FROZEN_POPULATION_COUNT_MISMATCH")
    return out


def main() -> int:
    if len(ACTIVE) != 15:
        raise RuntimeError("ACTIVE_SURFACE_DRIFT")
    got_active = hashlib.sha256(json.dumps(sorted(ACTIVE)).encode()).hexdigest()
    if got_active != ACTIVE_COMMITMENT:
        raise RuntimeError("ACTIVE_COMMITMENT_DRIFT")

    with tempfile.TemporaryDirectory(prefix="lb-grammar-audit-") as td:
        base = Path(td)
        parquet = base / "test.parquet"
        url = (
            "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
            + DATASET_REV + "/data/test-00000-of-00001.parquet?download=true"
        )
        run(["curl","--fail","--location","--retry","3","--silent","--show-error",url,"-o",str(parquet)])
        if parquet.stat().st_size != DATASET_BYTES or sha256(parquet) != DATASET_SHA256:
            raise RuntimeError("FROZEN_DATASET_BINDING_MISMATCH")

        lb = base / "LiveBench"
        run(["git","clone","--quiet","--filter=blob:none","--no-checkout","https://github.com/LiveBench/LiveBench.git",str(lb)])
        run(["git","-C",str(lb),"fetch","--quiet","--depth=1","origin",LIVEBENCH_COMMIT])
        run(["git","-C",str(lb),"checkout","--quiet","--detach",LIVEBENCH_COMMIT])

        binds = {
            "livebench/if_runner/instruction_following_eval/instructions_registry.py": LEGACY_REGISTRY_BLOB,
            "livebench/if_runner/instruction_following_eval/instructions.py": LEGACY_INSTRUCTIONS_BLOB,
            "livebench/if_runner/instruction_following_eval/evaluation_main.py": LEGACY_EVAL_BLOB,
        }
        for path, expected in binds.items():
            got = run(["git","-C",str(lb),"rev-parse",f"HEAD:{path}"]).stdout.strip()
            if got != expected:
                raise RuntimeError("PINNED_SCORER_BLOB_DRIFT")

        sys.path.insert(0, str(lb / "livebench" / "if_runner"))
        from instruction_following_eval import instructions_registry

        rows = selected_rows(parquet)

        distinct = set()
        all_instances_exact = True
        all_instances_norm = True
        all_rows_exact = True
        all_rows_norm = True
        repeat_seen = False
        repeat_hidden_substring_all = True
        repeat_prompt_starts_hidden_all = True
        repeat_hidden_eq_prefix_before_desc_all = True
        repeat_hidden_eq_suffix_after_desc_all = True
        repeat_hidden_eq_prompt_without_desc_all = True

        for q in rows:
            prompt = str((q.get("turns") or [""])[0])
            ids = list(q.get("instruction_id_list") or [])
            kwargs = list(q.get("kwargs") or [])
            if not ids or len(ids) != len(kwargs):
                raise RuntimeError("ROW_CONTRACT_SHAPE_MISMATCH")
            row_exact = True
            row_norm = True

            for idx, iid in enumerate(ids):
                distinct.add(iid)
                if iid not in ACTIVE:
                    raise RuntimeError("ACTIVE_ID_SURFACE_MISMATCH")
                cls = instructions_registry.INSTRUCTION_DICT.get(iid)
                if cls is None:
                    raise RuntimeError("LEGACY_REGISTRY_LOOKUP_FAILED")
                inst = cls(iid)
                kw = {k:v for k,v in dict(kwargs[idx] or {}).items() if v is not None}
                desc = str(inst.build_description(**kw))

                exact = desc in prompt
                normalized = norm(desc) in norm(prompt)
                all_instances_exact = all_instances_exact and exact
                all_instances_norm = all_instances_norm and normalized
                row_exact = row_exact and exact
                row_norm = row_norm and normalized

                if iid == "combination:repeat_prompt":
                    repeat_seen = True
                    hidden = str(kw.get("prompt_to_repeat") or "")
                    if not hidden:
                        raise RuntimeError("REPEAT_HIDDEN_VALUE_MISSING")
                    repeat_hidden_substring_all = repeat_hidden_substring_all and (hidden in prompt)
                    repeat_prompt_starts_hidden_all = repeat_prompt_starts_hidden_all and prompt.startswith(hidden)

                    if exact:
                        before, _, after = prompt.partition(desc)
                        repeat_hidden_eq_prefix_before_desc_all = (
                            repeat_hidden_eq_prefix_before_desc_all and norm(before) == norm(hidden)
                        )
                        repeat_hidden_eq_suffix_after_desc_all = (
                            repeat_hidden_eq_suffix_after_desc_all and norm(after) == norm(hidden)
                        )
                        without = (before.rstrip() + " " + after.lstrip()).strip()
                        repeat_hidden_eq_prompt_without_desc_all = (
                            repeat_hidden_eq_prompt_without_desc_all and norm(without) == norm(hidden)
                        )
                    else:
                        repeat_hidden_eq_prefix_before_desc_all = False
                        repeat_hidden_eq_suffix_after_desc_all = False
                        repeat_hidden_eq_prompt_without_desc_all = False

            all_rows_exact = all_rows_exact and row_exact
            all_rows_norm = all_rows_norm and row_norm

        distinct_commitment = hashlib.sha256(json.dumps(sorted(distinct)).encode()).hexdigest()
        if distinct_commitment != ACTIVE_COMMITMENT:
            raise RuntimeError("FROZEN_DISTINCT_ID_COMMITMENT_MISMATCH")

        result = {
            "schema": "LIVEBENCH_FROZEN_LEGACY_VISIBLE_GRAMMAR_AGGREGATE_V1",
            "status": "PASS",
            "population_count": POPULATION,
            "active_distinct_id_count": len(distinct),
            "active_id_commitment_matches": True,
            "all_instruction_instances_exact_canonical_description_present": all_instances_exact,
            "all_instruction_instances_whitespace_normalized_description_present": all_instances_norm,
            "all_rows_all_exact_canonical_descriptions_present": all_rows_exact,
            "all_rows_all_whitespace_normalized_descriptions_present": all_rows_norm,
            "repeat_family_present": repeat_seen,
            "repeat_hidden_is_verbatim_substring_for_all_repeat_rows": repeat_hidden_substring_all if repeat_seen else False,
            "repeat_visible_prompt_starts_with_hidden_for_all_repeat_rows": repeat_prompt_starts_hidden_all if repeat_seen else False,
            "repeat_hidden_equals_prefix_before_canonical_repeat_description_for_all_repeat_rows": repeat_hidden_eq_prefix_before_desc_all if repeat_seen else False,
            "repeat_hidden_equals_suffix_after_canonical_repeat_description_for_all_repeat_rows": repeat_hidden_eq_suffix_after_desc_all if repeat_seen else False,
            "repeat_hidden_equals_prompt_with_canonical_repeat_description_removed_for_all_repeat_rows": repeat_hidden_eq_prompt_without_desc_all if repeat_seen else False,
            "prompt_text_emitted": False,
            "kwargs_emitted": False,
            "case_ids_emitted": False,
            "per_instruction_frequency_emitted": False,
            "per_case_results_emitted": False,
            "new_candidate_inferences": 0,
            "new_candidate_responses": 0,
            "incremental_spend_usd": 0,
        }
        print(json.dumps(result, sort_keys=True))
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Deliberately emit only the failure class, never row content.
        print(json.dumps({
            "schema": "LIVEBENCH_FROZEN_LEGACY_VISIBLE_GRAMMAR_AGGREGATE_V1",
            "status": "FAIL_CLOSED",
            "failure_class": type(exc).__name__,
            "prompt_text_emitted": False,
            "kwargs_emitted": False,
            "case_ids_emitted": False,
        }, sort_keys=True))
        raise SystemExit(1)
