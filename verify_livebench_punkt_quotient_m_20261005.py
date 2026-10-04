#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import pathlib
import subprocess
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_punkt_quotient_m_20261005"

EXPECTED_SUBJECT = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py": "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py": "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py": "5803c31e3972c6d40415f319e808c48420bc0388",
    "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py": "71e637c70edf1c582e28ea38b3b798965c803a06",
    "canonical/runtime/livebench_legacy15_numeric_quotient_v1.py": "72189bb8adb12ad36a52ee666a1f79fbb201b06b",
    "canonical/runtime/livebench_pointwise_minimum_cut_v1.py": "0d4e563b618f8fd7f37396a88738cefb50979ff3",
    "canonical/runtime/livebench_post_sacrifice_parametric_reduction_v1.py": "a9ab9064b447ed669d2404a7a65f6c429c51ae85",
    "canonical/runtime/livebench_legacy15_punkt_context_quotient_v1.py": "10a738cfe8a9b1ebdebc7c4276fcb7de62c279aa",
}

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
LIVEBENCH_BLOBS = {
    "livebench/if_runner/instruction_following_eval/instructions.py": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "livebench/if_runner/instruction_following_eval/instructions_registry.py": "903ed738398648c7cfac61d5ffa478c22f1f0891",
    "livebench/if_runner/instruction_following_eval/instructions_util.py": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "livebench/if_runner/instruction_following_eval/evaluation_main.py": "4a341984936c4d609644a3b77f8c030ac5aa7269",
}
NLTK_VERSION = "3.10.3"
NLTK_WHEEL_SHA256 = "ff9598a8e20518ee0d557745890cc4435b9578489e2dcbc69c4f81fa060caf7c"
NLTK_DATA_COMMIT = "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"
PUNKT_BLOBS = {
    "packages/tokenizers/punkt.zip": "da7ffbd1e6fd6cc5c2f6879c2d4da23c7691944c",
    "packages/tokenizers/punkt_tab.zip": "5e5ff6137d5ee6025e400d1c3a7b21914c48b635",
}

def run(cmd):
    return subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()

def git_blob(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)])

def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def exact_follow(registry, contract, response: str) -> bool:
    iid = contract["instruction_id"]
    checker = registry.INSTRUCTION_DICT[iid](iid)
    checker.build_description(**dict(contract.get("slots") or {}))
    return bool(response.strip()) and bool(checker.check_following(response))

def main() -> int:
    subject_blobs = {}
    for rel, expected in EXPECTED_SUBJECT.items():
        got = git_blob(SUBJECT / rel)
        subject_blobs[rel] = got
        assert got == expected, (rel, got, expected)

    assert tuple(sys.version_info[:2]) == (3, 12), sys.version
    assert importlib.metadata.version("nltk") == NLTK_VERSION

    wheel_dir = pathlib.Path("/tmp/nltk_wheel")
    wheels = sorted(wheel_dir.glob("nltk-3.10.3-*.whl"))
    assert len(wheels) == 1, wheels
    wheel_sha = sha256(wheels[0])
    assert wheel_sha == NLTK_WHEEL_SHA256, wheel_sha

    live = pathlib.Path("/tmp/LiveBench")
    assert run(["git", "-C", str(live), "rev-parse", "HEAD"]) == LIVEBENCH_COMMIT
    source_blobs = {}
    for rel, expected in LIVEBENCH_BLOBS.items():
        got = run(["git", "-C", str(live), "rev-parse", "HEAD:" + rel])
        source_blobs[rel] = got
        assert got == expected, (rel, got, expected)

    data_repo = pathlib.Path("/tmp/nltk_data_repo")
    commit_obj = run(["git", "-C", str(data_repo), "rev-parse", NLTK_DATA_COMMIT + "^{commit}"])
    assert commit_obj == NLTK_DATA_COMMIT, commit_obj
    data_blobs = {}
    for rel, expected in PUNKT_BLOBS.items():
        got = run(["git", "-C", str(data_repo), "rev-parse", NLTK_DATA_COMMIT + ":" + rel])
        data_blobs[rel] = got
        assert got == expected, (rel, got, expected)

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))

    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_punkt_context_quotient_v1 as quotient
    from canonical.runtime import livebench_post_sacrifice_parametric_reduction_v1 as reduction
    from instruction_following_eval import instructions_registry, instructions_util

    reduced = reduction.verify()
    assert reduced["status"] == (
        "PASS__NON_SENTENCE_POST_SACRIFICE_CONSTRUCTION_REDUCED_"
        "PARAMETRICALLY__ONLY_PINNED_PUNKT_CONTEXT_REMAINS"
    ), reduced

    q = quotient.verify_quotient()
    contexts = quotient.reachable_contexts()
    assert q["reachable_context_count"] == 146, q["reachable_context_count"]
    assert len(contexts) == 146
    assert len(set(contexts)) == 146

    counts = Counter()
    failures = []

    def check(name: str, contracts, relation: str, threshold: int):
        built = comp.compose_contracts(contracts)
        counts["constructed"] += 1
        if built.get("status") != "CANDIDATE_WITNESS":
            failures.append({"name": name, "kind": "construction", "built": built})
            return
        response = str(built["response"])
        flags = [exact_follow(instructions_registry, c, response) for c in contracts]
        sentence_count = int(instructions_util.count_sentences(response))
        sentence_ok = (
            sentence_count < threshold
            if relation == "less than"
            else sentence_count >= threshold
        )
        if not all(flags) or not sentence_ok:
            failures.append({
                "name": name,
                "kind": "exact_checker_failure",
                "context_contracts": contracts,
                "flags": flags,
                "sentence_count": sentence_count,
                "relation": relation,
                "threshold": threshold,
                "response": response,
            })
            return
        counts["exact_all_pass"] += 1
        counts["sentence_checks"] += 1
        counts["sentence_count_" + str(sentence_count)] += 1

    for idx, ctx in enumerate(contexts):
        contracts = quotient.representative_contracts(
            ctx, relation="less than", threshold=2
        )
        check(f"lt2:{idx}", contracts, "less than", 2)
        counts["less_than_2_contexts"] += 1

        for n in range(1, 21):
            contracts = quotient.representative_contracts(
                ctx, relation="at least", threshold=n
            )
            check(f"atleast:{n}:{idx}", contracts, "at least", n)
            counts["at_least_context_threshold_pairs"] += 1

    expected_checks = 146 * 21
    assert counts["less_than_2_contexts"] == 146
    assert counts["at_least_context_threshold_pairs"] == 146 * 20
    assert counts["sentence_checks"] == expected_checks, counts

    if failures:
        receipt = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_INDEPENDENT_VERIFICATION_20261005_V1",
            "status": "FAIL_CLOSED",
            "failure_count": len(failures),
            "failures": failures[:100],
            "counts": dict(counts),
        }
        pathlib.Path("livebench_punkt_context_verification.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        raise SystemExit("PUNKT_CONTEXT_FAILURES:" + str(len(failures)))

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_INDEPENDENT_VERIFICATION_20261005_V1",
        "status": "PASS__146_OF_146_REACHABLE_PUNKT_CONTEXTS__3066_OF_3066_EXACT_SENTENCE_OBLIGATIONS",
        "subject_blobs": subject_blobs,
        "pinned_livebench": {
            "commit": LIVEBENCH_COMMIT,
            "source_blobs": source_blobs,
        },
        "pinned_runtime": {
            "python_major_minor": [3, 12],
            "nltk_version": NLTK_VERSION,
            "nltk_wheel_sha256": wheel_sha,
            "nltk_data_commit": NLTK_DATA_COMMIT,
            "punkt_archive_git_blobs": data_blobs,
        },
        "exact_result": {
            "reachable_punkt_contexts": len(contexts),
            "less_than_2_context_checks": counts["less_than_2_contexts"],
            "at_least_context_threshold_checks": counts["at_least_context_threshold_pairs"],
            "total_exact_sentence_obligations": counts["sentence_checks"],
            "all_exact_checkers_passed": counts["exact_all_pass"],
        },
        "theorem_supported": (
            "FOR_EVERY_REACHABLE_ACTIVE15_POST_SACRIFICE_PUNKT_CONTEXT__"
            "THE_CURRENT_COMPOSER_SATISFIES_PINNED_NUMBER_OF_SENTENCES_FOR_LT2_"
            "AND_FOR_EVERY_PUBLIC_AT_LEAST_THRESHOLD_1_TO_20__WITH_EXACT_"
            "NLTK_3_10_3_AND_PINNED_PUNKT_DATA"
        ),
        "zero_terminal_boundary": {
            "terminal_rows_read": 0,
            "hidden_kwargs_read": 0,
            "terminal_instruction_id_lists_read": 0,
            "target_scores_read": 0,
        },
        "acceptance_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_RECEIPT_DISCHARGES_ONLY_THE_PRECOMMITTED_PUNKT_CONTEXT_RESIDUAL",
            "LIVEBENCH_ACCEPTANCE_REQUIRES_COMPOSITION_WITH_THE_OTHER_FROZEN_UNIVERSAL_CLOSURE_GATE_CLAUSES",
        ],
    }
    pathlib.Path("livebench_punkt_context_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
