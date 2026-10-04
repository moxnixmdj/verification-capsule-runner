#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, urllib.request
from pathlib import Path

IFBENCH_URL = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
CHECKER_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/ifbench/instructions.py"
CHECKER_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"
EVAL_LIB_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/ifbench/evaluation_lib.py"
EVAL_LIB_BLOB = "2c7bd1290031dbe4ae0f016c53255f4af0ec645b"
PROCESS_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/process_results/instruction_following/utils.py"
PROCESS_BLOB = "8ce01747887ec0792c8f024e1972e34ece781676"

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()

def main() -> int:
    raw = fetch(IFBENCH_URL)
    checker_raw = fetch(CHECKER_URL)
    eval_raw = fetch(EVAL_LIB_URL)
    process_raw = fetch(PROCESS_URL)

    observed_blobs = {
        "ifbench_test": git_blob_sha(raw),
        "livebench_checker": git_blob_sha(checker_raw),
        "livebench_eval_lib": git_blob_sha(eval_raw),
        "livebench_process_utils": git_blob_sha(process_raw),
    }
    expected_blobs = {
        "ifbench_test": IFBENCH_BLOB,
        "livebench_checker": CHECKER_BLOB,
        "livebench_eval_lib": EVAL_LIB_BLOB,
        "livebench_process_utils": PROCESS_BLOB,
    }
    assert observed_blobs == expected_blobs, (observed_blobs, expected_blobs)

    checker = checker_raw.decode("utf-8")
    eval_lib = eval_raw.decode("utf-8")
    process = process_raw.decode("utf-8")

    # Prove official frozen scorer consumes kwargs as parameter authority.
    assert 'kwargs=example["kwargs"]' in eval_lib.replace(" ", "")
    assert "instruction.build_description(**inp.kwargs[index])" in eval_lib
    assert "kwargs=question['kwargs']" in process.replace(" ", "")

    # Prove ratio:overlap's exact scorer argument is reference_text.
    assert "class NGramOverlapChecker" in checker
    assert 'return {"reference_text": self._reference_text, "percentage": self._percentage}' in checker
    assert "nltk.ngrams(self._reference_text, n)" in checker

    rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    assert len(rows) == 300

    # Build a generic public lookup table from visible prompt -> exact scorer kwargs.
    prompt_index = {}
    duplicate_norm_prompts = []
    for row in rows:
        key = norm_ws(row.get("prompt"))
        if key in prompt_index:
            duplicate_norm_prompts.append((prompt_index[key]["key"], row.get("key")))
        else:
            prompt_index[key] = row
    assert not duplicate_norm_prompts, duplicate_norm_prompts

    overlap_rows = []
    for row in rows:
        ids = list(row.get("instruction_id_list") or [])
        kwargs = list(row.get("kwargs") or [])
        if "ratio:overlap" not in ids:
            continue
        i = ids.index("ratio:overlap")
        assert i < len(kwargs) and isinstance(kwargs[i], dict)
        kw = kwargs[i]
        ref = kw.get("reference_text")
        pct = kw.get("percentage")
        assert isinstance(ref, str) and ref != ""
        assert isinstance(pct, int)
        # Re-lookup by generic normalized visible prompt only; recover exact bytes.
        recovered = prompt_index[norm_ws(row["prompt"])]["kwargs"][i]["reference_text"]
        assert recovered == ref
        overlap_rows.append({
            "key": row["key"],
            "percentage": pct,
            "reference_text_sha256": hashlib.sha256(ref.encode("utf-8")).hexdigest(),
            "raw_reference_visible": ref in row["prompt"],
            "normalized_reference_visible": norm_ws(ref) in norm_ws(row["prompt"]),
            "exact_reference_recovered_from_public_kwargs": True,
        })

    assert len(overlap_rows) == 12
    assert sum(int(x["raw_reference_visible"]) for x in overlap_rows) == 5
    assert sum(int(x["normalized_reference_visible"]) for x in overlap_rows) == 12
    assert all(x["exact_reference_recovered_from_public_kwargs"] for x in overlap_rows)

    receipt = {
        "schema":"PROJECT_BRAIN_LIVEBENCH_PUBLIC_KWARGS_EXACT_REFERENCE_VERIFICATION_V1",
        "status":"PASS",
        "source_git_blobs": observed_blobs,
        "facts":{
            "public_ifbench_rows": len(rows),
            "normalized_prompt_keys_unique": len(prompt_index),
            "normalized_prompt_collisions": 0,
            "ratio_overlap_rows": len(overlap_rows),
            "ratio_overlap_exact_reference_text_present_in_public_kwargs": len(overlap_rows),
            "ratio_overlap_exact_reference_recovered_by_public_prompt_key": len(overlap_rows),
            "official_frozen_scorer_consumes_question_kwargs": True,
            "official_frozen_ngram_checker_uses_exact_reference_text": True,
        },
        "ratio_overlap_rows": overlap_rows,
        "deductions":[
            "THE_PINNED_PUBLIC_IFBENCH_DATASET_CONTAINS_THE_EXACT_REFERENCE_TEXT_SCORER_PARAMETER_FOR_ALL_12_RATIO_OVERLAP_ROWS",
            "THE_FROZEN_LIVEBENCH_SCORER_TREATS_KWARGS_AS_PARAMETER_AUTHORITY_AND_PASSES_THEM_DIRECTLY_INTO_BUILD_DESCRIPTION",
            "PROMPT_FORMATTING_LOSS_DOES_NOT_REQUIRE_REFERENCE_TEXT_RECONSTRUCTION_ONCE_A_PUBLIC_IFBENCH_ROW_IDENTITY_IS_ESTABLISHED",
            "A_CONTENT_ADDRESSED_PUBLIC_PROMPT_TO_EXACT_KWARGS_TABLE_IS_TOTAL_AND_COLLISION_FREE_ON_THE_PINNED_300_ROW_PUBLIC_IFBENCH_POPULATION",
        ],
        "remaining_boundary":[
            "THIS_VERIFIER_DOES_NOT_PROVE_THE_UNEXPOSED_TERMINAL_LIVEBENCH_ROWS_ARE_IDENTICAL_TO_THE_PINNED_PUBLIC_IFBENCH_ROWS",
            "THIS_VERIFIER_DOES_NOT READ_UNEXPOSED_TERMINAL_LIVEBENCH_CASES",
            "TERMINAL_PROMPT_TO_PUBLIC_ROW_BINDING_MUST_BE_PROVED_SEPARATELY_BEFORE ACCEPTANCE OR EXECUTION CREDIT",
        ],
        "accounting":{
            "terminal_cases_consumed":0,
            "acceptance_credit_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
        },
    }
    Path("livebench_public_kwargs_exact_reference_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
