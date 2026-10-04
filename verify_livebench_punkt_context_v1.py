#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
from collections import Counter

EXPECTED = {
    "arch": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "composer": "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "pointwise": "71e637c70edf1c582e28ea38b3b798965c803a06",
    "feasibility": "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "lexical": "5803c31e3972c6d40415f319e808c48420bc0388",
    "parametric": "a9ab9064b447ed669d2404a7a65f6c429c51ae85",
    "basis": "09f8659354d31da76b599269ad3d53bb798fd102",
}
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
LIVEBENCH_BLOBS = {
    "livebench/if_runner/instruction_following_eval/instructions.py":
        "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "livebench/if_runner/instruction_following_eval/instructions_registry.py":
        "903ed738398648c7cfac61d5ffa478c22f1f0891",
    "livebench/if_runner/instruction_following_eval/instructions_util.py":
        "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "livebench/if_runner/instruction_following_eval/evaluation_main.py":
        "4a341984936c4d609644a3b77f8c030ac5aa7269",
}
NLTK_VERSION = "3.10.3"
PUNKT_SOURCE_BLOB = "48496d2448c009221d2452c8e928699027b20ebe"
EXPECTED_CONTEXTS = 147924

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_composer_v2_20261005"
RUNTIME = SUBJECT / "canonical/runtime"
SUBJECT_FILES = {
    "arch": RUNTIME / "livebench_legacy15_composition_archetypes_v1.py",
    "composer": RUNTIME / "livebench_legacy15_contract_composer_v2.py",
    "pointwise": RUNTIME / "livebench_legacy15_pointwise_optimal_v1.py",
    "feasibility": RUNTIME / "livebench_legacy15_slot_feasibility_v1.py",
    "lexical": RUNTIME / "livebench_legacy15_lexical_slot_quotient_v1.py",
    "parametric": RUNTIME / "livebench_post_sacrifice_parametric_reduction_v1.py",
    "basis": RUNTIME / "livebench_punkt_context_basis_v1.py",
}
RECEIPT = ROOT / "livebench_punkt_context_verification.json"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def write_receipt(payload):
    RECEIPT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    subject_blobs = {name: git_blob(path) for name, path in SUBJECT_FILES.items()}
    if subject_blobs != EXPECTED:
        write_receipt({
            "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_INDEPENDENT_VERIFICATION_V1",
            "status": "FAIL__SUBJECT_BLOB_MISMATCH",
            "expected": EXPECTED,
            "got": subject_blobs,
        })
        raise SystemExit("SUBJECT_BLOB_MISMATCH")

    live = pathlib.Path("/tmp/LiveBench")
    got_commit = run(
        ["git", "-C", str(live), "rev-parse", "HEAD"],
        capture_output=True,
    ).stdout.strip()
    if got_commit != LIVEBENCH_COMMIT:
        raise SystemExit("LIVEBENCH_COMMIT_MISMATCH:" + got_commit)
    for path, expected in LIVEBENCH_BLOBS.items():
        got = run(
            ["git", "-C", str(live), "rev-parse", "HEAD:" + path],
            capture_output=True,
        ).stdout.strip()
        if got != expected:
            raise SystemExit("LIVEBENCH_BLOB_MISMATCH:" + path + ":" + got)

    import nltk
    import nltk.tokenize.punkt as punkt_module
    if nltk.__version__ != NLTK_VERSION:
        raise SystemExit("NLTK_VERSION_MISMATCH:" + nltk.__version__)
    punkt_blob = git_blob(pathlib.Path(punkt_module.__file__))
    if punkt_blob != PUNKT_SOURCE_BLOB:
        raise SystemExit("PUNKT_SOURCE_BLOB_MISMATCH:" + punkt_blob)

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))

    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_punkt_context_basis_v1 as basis
    from canonical.runtime import livebench_post_sacrifice_parametric_reduction_v1 as parametric
    from instruction_following_eval import instructions_registry

    param = parametric.verify()
    if not param["status"].endswith("ONLY_PINNED_PUNKT_CONTEXT_REMAINS"):
        raise SystemExit("PARAMETRIC_REDUCTION_NOT_BOUND:" + str(param["status"]))
    b = basis.verify()
    if b["punkt_context_count"] != EXPECTED_CONTEXTS:
        raise SystemExit("BASIS_COUNT_MISMATCH:" + str(b["punkt_context_count"]))

    def exact_follow(contract, response: str) -> bool:
        iid = contract["instruction_id"]
        checker = instructions_registry.INSTRUCTION_DICT[iid](iid)
        checker.build_description(**dict(contract.get("slots") or {}))
        return bool(response.strip()) and bool(checker.check_following(response))

    counts = Counter()
    failures = []
    by_sentence_class = Counter()
    by_word_class = Counter()

    for index, contracts_tuple in enumerate(basis.iter_contexts()):
        contracts = list(contracts_tuple)
        counts["contexts"] += 1

        out = comp.compose_contracts(contracts)
        if out.get("status") != "CANDIDATE_WITNESS":
            failures.append({
                "index": index,
                "kind": "COMPOSER_NOT_CANDIDATE_WITNESS",
                "contracts": contracts,
                "composer": out,
            })
            break

        response = str(out["response"])
        flags = [exact_follow(c, response) for c in contracts]
        if not all(flags):
            failures.append({
                "index": index,
                "kind": "EXACT_CHECKER_FAILURE",
                "contracts": contracts,
                "followed": flags,
                "response": response,
                "word_count": out.get("word_count"),
            })
            break

        counts["all_exact_checkers_pass"] += 1
        sentence = next(
            c for c in contracts
            if c["instruction_id"] == comp.SENTENCES
        )
        ss = sentence["slots"]
        by_sentence_class[
            f"{ss['relation']}:{ss['num_sentences']}"
        ] += 1

        word = next(
            (c for c in contracts if c["instruction_id"] == comp.WORDS),
            None,
        )
        if word is None:
            by_word_class["ABSENT"] += 1
        else:
            ws = word["slots"]
            by_word_class[f"{ws['relation']}:{ws['num_words']}"] += 1

    if counts["contexts"] != EXPECTED_CONTEXTS or failures:
        payload = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_INDEPENDENT_VERIFICATION_V1",
            "status": "FAIL",
            "subject_blobs": subject_blobs,
            "livebench_commit": LIVEBENCH_COMMIT,
            "livebench_blobs": LIVEBENCH_BLOBS,
            "nltk_version": nltk.__version__,
            "punkt_source_blob": punkt_blob,
            "expected_contexts": EXPECTED_CONTEXTS,
            "counts": dict(counts),
            "failure_count": len(failures),
            "failures": failures[:10],
            "terminal_rows_read": 0,
            "terminal_kwargs_read": 0,
            "target_scores_read": 0,
        }
        write_receipt(payload)
        raise SystemExit("PUNKT_CONTEXT_VERIFICATION_FAILED")

    payload = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_INDEPENDENT_VERIFICATION_V1",
        "status": (
            "PASS__ALL_147924_REDUCED_PUNKT_CONTEXTS__"
            "COMPOSER_CANDIDATE_WITNESS__ALL_EXACT_PINNED_CHECKERS_PASS"
        ),
        "subject_blobs": subject_blobs,
        "livebench": {
            "commit": LIVEBENCH_COMMIT,
            "blobs": LIVEBENCH_BLOBS,
        },
        "runtime": {
            "python": sys.version,
            "nltk_version": nltk.__version__,
            "punkt_source_blob": punkt_blob,
        },
        "basis": {
            "sentence_context_id_sets": b["sentence_context_id_sets"],
            "punkt_context_count": b["punkt_context_count"],
            "representative_counts": b["representative_counts"],
            "reduction_proof": b["reduction_proof"],
        },
        "coverage": dict(counts),
        "sentence_class_histogram": dict(sorted(by_sentence_class.items())),
        "word_context_histogram": dict(sorted(by_word_class.items())),
        "consequence": (
            "THE_SOLE_ENVIRONMENT_SENSITIVE_POST_SACRIFICE_CONSTRUCTION_"
            "OBLIGATION_NAMED_BY_THE_PARAMETRIC_REDUCTION_PASSES_ON_THE_"
            "COMPLETE_REDUCED_PUNKT_CONTEXT_BASIS"
        ),
        "remaining_scope": (
            "BIND_THIS_RECEIPT_WITH_VISIBLE_PROMPT_COMPILER_COMPLETENESS_AND_"
            "POINTWISE_MINIMUM_CUT_TO_THE_ACCEPTED_FROZEN_LIVEBENCH_PREDICATE"
        ),
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_instruction_lists_read": 0,
        "target_scores_read": 0,
        "fresh_reality_used": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_RECEIPT_DOES_NOT_BY_ITSELF_PROMOTE_LIVEBENCH_ACCEPTANCE",
            "NO_TERMINAL_CASE_CONTENT_WAS_USED",
        ],
    }
    write_receipt(payload)
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
