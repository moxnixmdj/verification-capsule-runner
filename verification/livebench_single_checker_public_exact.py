#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json, os, sys, types
from collections import Counter, defaultdict
from pathlib import Path

SUBJECT = Path("subject")
SOLVER = SUBJECT / "canonical/runtime/livebench_if_single_checker_solver_v1.py"
NGRAM = SUBJECT / "canonical/runtime/livebench_ngram_reference_free_v1.py"
EXPECTED_SOLVER_BLOB = "1071240dd19225d4b7e26f42cfb9da34538eed46"
EXPECTED_NGRAM_BLOB = "bcd4a4ede2e70e17e90a33416f3f4a564162f3ea"
EXPECTED_PUBLIC_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
EXPECTED_CHECKER_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"
EXPECTED_SINGLE_ROWS = 256
EXPECTED_TOTAL_ROWS = 300

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def main() -> int:
    livebench_root = Path(os.environ["LIVEBENCH_ROOT"])
    public_path = Path(os.environ["IFBENCH_DATA"])
    checker_path = livebench_root / "livebench/if_runner/ifbench/instructions.py"

    observed = {
        "solver": git_blob_sha(SOLVER.read_bytes()),
        "ngram": git_blob_sha(NGRAM.read_bytes()),
        "public_ifbench": git_blob_sha(public_path.read_bytes()),
        "frozen_checker": git_blob_sha(checker_path.read_bytes()),
    }
    expected = {
        "solver": EXPECTED_SOLVER_BLOB,
        "ngram": EXPECTED_NGRAM_BLOB,
        "public_ifbench": EXPECTED_PUBLIC_BLOB,
        "frozen_checker": EXPECTED_CHECKER_BLOB,
    }
    assert observed == expected, (observed, expected)

    # Candidate import. Namespace package is rooted at subject/.
    sys.path.insert(0, str(SUBJECT.resolve()))

    # Frozen checker imports spaCy even though the 58 frozen checker bodies do
    # not require it. Stub only the dead bootstrap import; any real use fails.
    spacy = types.ModuleType("spacy")
    spacy.util = types.SimpleNamespace(is_package=lambda _name: True)
    spacy_cli = types.ModuleType("spacy.cli")
    spacy_cli.download = lambda _name: (_ for _ in ()).throw(RuntimeError("dead spacy path invoked"))
    sys.modules["spacy"] = spacy
    sys.modules["spacy.cli"] = spacy_cli

    sys.path.insert(0, str(livebench_root.resolve()))
    from canonical.runtime import livebench_if_single_checker_solver_v1 as solver
    from livebench.if_runner.ifbench import evaluation_lib

    rows = [json.loads(x) for x in public_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == EXPECTED_TOTAL_ROWS
    singles = [r for r in rows if len(r.get("instruction_id_list") or []) == 1]
    assert len(singles) == EXPECTED_SINGLE_ROWS

    results = []
    failures = []
    by_checker = defaultdict(lambda: Counter(total=0, detected=0, constructed=0, exact_pass=0))

    for row in singles:
        expected_id = row["instruction_id_list"][0]
        by_checker[expected_id]["total"] += 1
        try:
            out = solver.solve(row["prompt"])
        except Exception as exc:
            rec = {
                "key": row.get("key"), "checker_id": expected_id,
                "stage": "solver_exception",
                "error": f"{type(exc).__name__}:{exc}",
                "pass": False,
            }
            results.append(rec); failures.append(rec)
            continue

        detected = out.get("checker_id") == expected_id
        if detected:
            by_checker[expected_id]["detected"] += 1

        response = out.get("response")
        constructed = out.get("status") == "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS" and isinstance(response, str) and bool(response)
        if constructed:
            by_checker[expected_id]["constructed"] += 1

        exact_pass = False
        exact_error = None
        if detected and constructed:
            try:
                inp = evaluation_lib.InputExample(
                    key=row["key"],
                    instruction_id_list=list(row["instruction_id_list"]),
                    prompt=row["prompt"],
                    kwargs=copy.deepcopy(row["kwargs"]),
                )
                scored = evaluation_lib.test_instruction_following_strict(inp, response)
                exact_pass = bool(scored.follow_all_instructions)
            except Exception as exc:
                exact_error = f"{type(exc).__name__}:{exc}"

        if exact_pass:
            by_checker[expected_id]["exact_pass"] += 1

        rec = {
            "key": row.get("key"),
            "checker_id": expected_id,
            "solver_status": out.get("status"),
            "recognized_checker_ids": out.get("recognized_checker_ids") or ([out.get("checker_id")] if out.get("checker_id") else []),
            "detected_expected_checker": detected,
            "constructed": constructed,
            "exact_strict_pass": exact_pass,
            "exact_error": exact_error,
            "response_sha256": hashlib.sha256((response or "").encode("utf-8")).hexdigest() if response else None,
            "pass": bool(detected and constructed and exact_pass),
        }
        results.append(rec)
        if not rec["pass"]:
            failures.append(rec)

    by_checker_out = {
        k: dict(v) | {"all_exact_pass": v["exact_pass"] == v["total"]}
        for k, v in sorted(by_checker.items())
    }
    passed = sum(1 for r in results if r["pass"])
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_IF_SINGLE_CHECKER_PUBLIC_EXACT_VERIFICATION_V1",
        "status": "PASS" if passed == EXPECTED_SINGLE_ROWS else "FAIL",
        "source_git_blobs": observed,
        "facts": {
            "public_rows": len(rows),
            "public_single_checker_rows": len(singles),
            "public_two_checker_rows": len(rows) - len(singles),
            "single_checker_rows_detected_constructed_and_exact_strict_passed": passed,
            "single_checker_exact_pass_rate": passed / len(singles),
            "failed_single_checker_rows": len(failures),
            "terminal_case_content_read": False,
            "model_dependency_count": 0,
        },
        "by_checker": by_checker_out,
        "failures": failures,
        "accounting": {
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
        "hard_boundary": [
            "PUBLIC_IFBENCH_SINGLE_CHECKER_POPULATION_ONLY",
            "NO_UNEXPOSED_TERMINAL_LIVEBENCH_CASES_READ",
            "NO_TERMINAL_SCORE_OR_ACCEPTANCE_CLAIM",
            "TERMINAL_POPULATION_PROVENANCE_BINDING_REMAINS_SEPARATE",
        ],
    }
    Path("livebench_single_checker_public_exact_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("RESULT_JSON=" + json.dumps(receipt, sort_keys=True))
    return 0 if passed == EXPECTED_SINGLE_ROWS else 1

if __name__ == "__main__":
    raise SystemExit(main())
