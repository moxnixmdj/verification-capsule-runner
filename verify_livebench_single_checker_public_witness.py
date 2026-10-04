#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import os
import sys
import tempfile
import traceback
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

IFBENCH_URL = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PUBLIC_FILES = {
    "instructions.py": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/ifbench/instructions.py",
        "02b2dfeb50f036b89bec3df34522c73f756d8f44",
    ),
    "instructions_util.py": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/ifbench/instructions_util.py",
        "21b13c7fcfc2c2de01e80c9e7dd222b9bca81342",
    ),
    "instructions_registry.py": (
        f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/ifbench/instructions_registry.py",
        "adfed4832877566e62970257b50c6fa32c302fb2",
    ),
}
SUBJECT_ROOT = Path(__file__).resolve().parent / "subjects" / "livebench_single_checker_v1"
SUBJECT_SOLVER_BLOB = "b21e2a0946523e7aaa2d4a929676574ddc14c92b"
SUBJECT_HELPER_BLOB = "bcd4a4ede2e70e17e90a33416f3f4a564162f3ea"\nSUBJECT_REPEAT_BLOB = "332fbb1fac1cdee2632dc454b497376d319e2287"
RECEIPT = Path("livebench_single_checker_public_witness_receipt.json")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def local_blob(path: Path) -> str:
    return git_blob_sha(path.read_bytes())


def install_public_checker() -> tuple[object, dict[str, str]]:
    td = Path(tempfile.mkdtemp(prefix="livebench-ifbench-checker-"))
    pkg = td / "livebench" / "if_runner" / "ifbench"
    pkg.mkdir(parents=True)
    for p in [td / "livebench" / "__init__.py", td / "livebench" / "if_runner" / "__init__.py", pkg / "__init__.py"]:
        p.write_text("", encoding="utf-8")

    observed = {}
    for name, (url, expected_blob) in PUBLIC_FILES.items():
        raw = fetch(url)
        actual = git_blob_sha(raw)
        if actual != expected_blob:
            raise AssertionError(f"PUBLIC_BLOB_MISMATCH:{name}:{actual}:{expected_blob}")
        (pkg / name).write_bytes(raw)
        observed[name] = actual

    sys.path.insert(0, str(td))
    registry = importlib.import_module("livebench.if_runner.ifbench.instructions_registry")
    return registry, observed


def instantiate_checker(registry: object, iid: str, kwargs: dict | None, prompt: str):
    mapping = getattr(registry, "INSTRUCTION_DICT")
    cls = mapping[iid]
    inst = cls(iid)
    # Mirror frozen evaluation_lib.test_instruction_following_strict:
    # remove null kwargs, build once, then rebuild with prompt iff requested.
    kw = {key: value for key, value in dict(kwargs or {}).items() if value is not None}
    inst.build_description(**kw)
    args = inst.get_instruction_args()
    if args and "prompt" in args:
        inst.build_description(prompt=prompt)
    return inst


def package_versions() -> dict[str, str]:
    out = {}
    for name in ("nltk", "emoji", "syllapy", "spacy"):
        try:
            out[name] = importlib.metadata.version(name)
        except Exception as exc:
            out[name] = f"UNAVAILABLE:{type(exc).__name__}"
    return out


def main() -> int:
    sys.path.insert(0, str(SUBJECT_ROOT))
    solver_file = SUBJECT_ROOT / "canonical" / "runtime" / "livebench_if_single_checker_solver_v1.py"
    helper_file = SUBJECT_ROOT / "canonical" / "runtime" / "livebench_ngram_reference_free_v1.py"
    assert local_blob(solver_file) == SUBJECT_SOLVER_BLOB
    assert local_blob(helper_file) == SUBJECT_HELPER_BLOB

    import nltk
    for resource in ("punkt", "punkt_tab", "stopwords", "averaged_perceptron_tagger", "averaged_perceptron_tagger_eng"):
        try:
            nltk.download(resource, quiet=True)
        except Exception:
            pass

    solver = importlib.import_module("canonical.runtime.livebench_if_single_checker_solver_v1")
    registry, checker_blobs = install_public_checker()

    raw = fetch(IFBENCH_URL)
    assert git_blob_sha(raw) == IFBENCH_BLOB
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    assert len(rows) == 300

    single = [r for r in rows if len(r.get("instruction_id_list") or []) == 1]
    dual = [r for r in rows if len(r.get("instruction_id_list") or []) == 2]
    assert len(single) == 256
    assert len(dual) == 44

    family_total = Counter()
    family_solved = Counter()
    family_pass = Counter()
    failure_kinds = Counter()
    failures = []

    for row in single:
        iid = str(row["instruction_id_list"][0])
        family_total[iid] += 1
        record = {
            "key": str(row.get("key")),
            "instruction_id": iid,
        }
        try:
            out = solver.solve(str(row["prompt"]))
            record["solver_status"] = out.get("status")
            record["recognized_checker_ids"] = out.get("recognized_checker_ids")
            record["checker_id"] = out.get("checker_id")
            response = out.get("response")
            if out.get("status") != "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS" or not isinstance(response, str) or not response:
                failure_kinds["SOLVER_FAIL_CLOSED"] += 1
                record["failure"] = "SOLVER_FAIL_CLOSED"
                record["solver_error"] = out.get("error")
                failures.append(record)
                continue
            if out.get("checker_id") != iid:
                failure_kinds["WRONG_CHECKER_ID"] += 1
                record["failure"] = "WRONG_CHECKER_ID"
                failures.append(record)
                continue

            family_solved[iid] += 1
            checker = instantiate_checker(registry, iid, row["kwargs"][0] if row.get("kwargs") else None, str(row["prompt"]))
            passed = bool(checker.check_following(response))
            record["exact_checker_pass"] = passed
            record["response_chars"] = len(response)
            if passed:
                family_pass[iid] += 1
            else:
                failure_kinds["EXACT_CHECKER_FALSE"] += 1
                record["failure"] = "EXACT_CHECKER_FALSE"
                failures.append(record)
        except Exception as exc:
            failure_kinds["EXCEPTION"] += 1
            record["failure"] = "EXCEPTION"
            record["exception_type"] = type(exc).__name__
            record["exception_message"] = str(exc)[:1000]
            record["traceback_tail"] = traceback.format_exc().splitlines()[-8:]
            failures.append(record)

    family_rows = []
    for iid in sorted(family_total):
        total = family_total[iid]
        solved = family_solved[iid]
        passed = family_pass[iid]
        family_rows.append({
            "instruction_id": iid,
            "rows": total,
            "solver_emitted_witness": solved,
            "exact_checker_passes": passed,
            "exact_checker_failures": total - passed,
        })

    exact_passes = sum(family_pass.values())
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_SINGLE_CHECKER_PUBLIC_WITNESS_INDEPENDENT_VERIFICATION_V1",
        "status": (
            "PASS__ALL_256_SINGLE_CHECKER_ROWS"
            if exact_passes == len(single)
            else "FAIL__PUBLIC_SINGLE_CHECKER_WITNESS_RESIDUALS_FOUND"
        ),
        "subject": {
            "solver_git_blob_sha": SUBJECT_SOLVER_BLOB,
            "ngram_helper_git_blob_sha": SUBJECT_HELPER_BLOB,\n            "repeat_compiler_git_blob_sha": SUBJECT_REPEAT_BLOB,
        },
        "public_sources": {
            "ifbench_test_git_blob_sha": git_blob_sha(raw),
            "livebench_commit": LIVEBENCH_COMMIT,
            "checker_blobs": checker_blobs,
        },
        "environment": {
            "python": sys.version,
            "packages": package_versions(),
        },
        "population": {
            "public_rows": len(rows),
            "single_checker_rows": len(single),
            "two_checker_rows_not_executed": len(dual),
            "instruction_family_count_in_single_rows": len(family_total),
        },
        "result": {
            "solver_witnesses_emitted": sum(family_solved.values()),
            "exact_checker_passes": exact_passes,
            "exact_checker_failures": len(single) - exact_passes,
            "pass_rate_single_checker": exact_passes / len(single),
            "failure_kinds": dict(sorted(failure_kinds.items())),
        },
        "families": family_rows,
        "failures": failures,
        "hard_nonclaims": [
            "PUBLIC_IFBENCH_SINGLE_CHECKER_ROWS_ONLY",
            "NO_TWO_CHECKER_COMPOSITION_CLAIM",
            "NO_FROZEN_TERMINAL_POPULATION_EQUIVALENCE_CLAIM",
            "NO_TERMINAL_CASE_CONTENT_READ",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if exact_passes == len(single) else 1


if __name__ == "__main__":
    raise SystemExit(main())
