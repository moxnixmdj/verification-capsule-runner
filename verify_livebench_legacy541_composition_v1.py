#!/usr/bin/env python3
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT_ROOT = ROOT / "subject/legacy541"
SOLVER_PATH = SUBJECT_ROOT / "canonical/runtime/livebench_legacy_ifeval_constructive_solver_v1.py"
INVERTER_PATH = SUBJECT_ROOT / "canonical/runtime/livebench_legacy_ifeval_prompt_inverter_v1.py"

EXPECTED_SOLVER_BLOB = "c293426df092ca1b82d77aa194ef182b510a0294"
EXPECTED_INVERTER_BLOB = "74904d2a00ed3f0bb2e8ab7787c59c0a8f828f7a"

GOOGLE_IFEVAL_COMMIT = "e49bbfe381c9c0e564b937f1c4e163a2273c65cc"
GOOGLE_IFEVAL_BLOB = "cbe52f6eecf3986fdac745b4acba4da1408eb146"
GOOGLE_IFEVAL_URL = (
    "https://raw.githubusercontent.com/google-research/google-research/"
    + GOOGLE_IFEVAL_COMMIT
    + "/instruction_following_eval/data/input_data.jsonl"
)

LIVEBENCH_ROOT = pathlib.Path("/tmp/LiveBench")
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
LEGACY_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
LEGACY_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
SCORE_UTILS_BLOB = "8ce01747887ec0792c8f024e1972e34ece781676"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def row_score(flags: list[bool]) -> float:
    if not flags:
        return 0.0
    return ((1.0 if all(flags) else 0.0) + sum(1 for x in flags if x) / len(flags)) / 2.0


def exact_checkers(prompt: str, ids: list[str], kwargs_list: list[dict], response: str):
    from instruction_following_eval import instructions_registry

    flags = []
    for iid, raw_kwargs in zip(ids, kwargs_list):
        checker_cls = instructions_registry.INSTRUCTION_DICT[iid]
        checker = checker_cls(iid)
        kwargs = {k: v for k, v in dict(raw_kwargs or {}).items() if v is not None}
        checker.build_description(**kwargs)
        args = checker.get_instruction_args()
        if args and "prompt" in args:
            checker.build_description(prompt=prompt)
        ok = bool(str(response or "").strip()) and bool(checker.check_following(str(response)))
        flags.append(ok)
    return flags


def main() -> int:
    assert git_blob(SOLVER_PATH.read_bytes()) == EXPECTED_SOLVER_BLOB
    assert git_blob(INVERTER_PATH.read_bytes()) == EXPECTED_INVERTER_BLOB

    instructions_path = LIVEBENCH_ROOT / "livebench/if_runner/instruction_following_eval/instructions.py"
    registry_path = LIVEBENCH_ROOT / "livebench/if_runner/instruction_following_eval/instructions_registry.py"
    score_utils_path = LIVEBENCH_ROOT / "livebench/process_results/instruction_following/utils.py"
    assert git_blob(instructions_path.read_bytes()) == LEGACY_INSTRUCTIONS_BLOB
    assert git_blob(registry_path.read_bytes()) == LEGACY_REGISTRY_BLOB
    assert git_blob(score_utils_path.read_bytes()) == SCORE_UTILS_BLOB

    score_source = score_utils_path.read_text(encoding="utf-8")
    assert "avg_score = (score_1 + score_2) / 2" in score_source
    assert 'results = results["strict"]' in score_source

    sys.path.insert(0, str(SUBJECT_ROOT))
    sys.path.insert(0, str(LIVEBENCH_ROOT / "livebench/if_runner"))

    from canonical.runtime import livebench_legacy_ifeval_constructive_solver_v1 as solver
    from canonical.runtime import livebench_legacy_ifeval_prompt_inverter_v1 as inverter
    from instruction_following_eval import instructions_registry

    assert len(instructions_registry.INSTRUCTION_DICT) == 25

    raw = fetch(GOOGLE_IFEVAL_URL)
    assert git_blob(raw) == GOOGLE_IFEVAL_BLOB
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    assert len(rows) == 541

    counts = collections.Counter()
    reason_counts = collections.Counter()
    instruction_distribution = collections.Counter()
    by_checker = collections.defaultdict(lambda: collections.Counter(total=0, passed=0))
    by_arity = collections.defaultdict(lambda: collections.Counter(rows=0, candidates=0, full=0, score4=0))
    failures = []
    score_sum = 0.0
    exact_id_set_matches = 0
    subset_id_matches = 0

    for row in rows:
        prompt = str(row.get("prompt") or "")
        ids = list(row.get("instruction_id_list") or [])
        kwargs_list = list(row.get("kwargs") or [])
        assert ids and len(ids) == len(kwargs_list)
        assert all(iid in instructions_registry.INSTRUCTION_DICT for iid in ids)

        instruction_distribution[len(ids)] += 1
        inv_matches = inverter.recognize(prompt)
        recognized_ids = [str(x.get("instruction_id")) for x in inv_matches]
        if collections.Counter(recognized_ids) == collections.Counter(ids):
            exact_id_set_matches += 1
        if set(ids).issubset(set(recognized_ids)):
            subset_id_matches += 1

        out = solver.synthesize(prompt)
        response = out.get("response")
        ar = by_arity[len(ids)]
        ar["rows"] += 1

        if response and out.get("status") == "CANDIDATE_PASS_PENDING_EXACT_PINNED_CHECKER_REPLAY":
            counts["candidate_rows"] += 1
            ar["candidates"] += 1
            try:
                flags = exact_checkers(prompt, ids, kwargs_list, str(response))
            except Exception as exc:
                flags = [False] * len(ids)
                reason = "EXACT_CHECKER_EXCEPTION:" + type(exc).__name__
                reason_counts[reason] += 1
                if len(failures) < 120:
                    failures.append({
                        "key": row.get("key"),
                        "ids": ids,
                        "stage": reason,
                    })
        else:
            flags = [False] * len(ids)
            reason = str(out.get("reason") or out.get("error") or out.get("status") or "NO_CANDIDATE")
            reason_counts[reason] += 1
            if len(failures) < 120:
                failures.append({
                    "key": row.get("key"),
                    "ids": ids,
                    "stage": "NO_CANDIDATE",
                    "reason": reason,
                })

        for iid, ok in zip(ids, flags):
            by_checker[iid]["total"] += 1
            if ok:
                by_checker[iid]["passed"] += 1

        score = row_score(flags)
        score_sum += score
        ar["score4"] += round(score * 4)

        if all(flags):
            counts["full_rows"] += 1
            ar["full"] += 1
        elif any(flags):
            counts["partial_rows"] += 1
            if len(failures) < 120:
                failures.append({
                    "key": row.get("key"),
                    "ids": ids,
                    "stage": "PARTIAL_CHECKER_PASS",
                    "passed": [iid for iid, ok in zip(ids, flags) if ok],
                    "failed": [iid for iid, ok in zip(ids, flags) if not ok],
                })
        else:
            counts["zero_rows"] += 1
            if response and len(failures) < 120:
                failures.append({
                    "key": row.get("key"),
                    "ids": ids,
                    "stage": "CANDIDATE_ZERO_CHECKER_PASS",
                })

    public_percent = 100.0 * score_sum / len(rows)
    checker_rows = {
        iid: {
            "total": int(v["total"]),
            "passed": int(v["passed"]),
            "failed": int(v["total"] - v["passed"]),
            "pass_fraction": (v["passed"] / v["total"]) if v["total"] else 0.0,
        }
        for iid, v in sorted(by_checker.items())
    }
    arity_rows = {
        str(k): {
            "rows": int(v["rows"]),
            "candidate_rows": int(v["candidates"]),
            "full_rows": int(v["full"]),
            "score_mass": v["score4"] / 4.0,
            "mean_percent": (100.0 * (v["score4"] / 4.0) / v["rows"]) if v["rows"] else 0.0,
        }
        for k, v in sorted(by_arity.items())
    }

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY541_COMPOSITION_PUBLIC_AUDIT_V1",
        "status": "PUBLIC_EXACT_LEGACY_CHECKER_AUDIT_COMPLETE__ZERO_TERMINAL_CASES__ZERO_CREDIT",
        "subject": {
            "brain_pr": 1774,
            "solver_blob": EXPECTED_SOLVER_BLOB,
            "inverter_blob": EXPECTED_INVERTER_BLOB,
        },
        "pinned_public_sources": {
            "google_ifeval_commit": GOOGLE_IFEVAL_COMMIT,
            "google_ifeval_blob": GOOGLE_IFEVAL_BLOB,
            "google_rows": len(rows),
            "livebench_commit": LIVEBENCH_COMMIT,
            "legacy_instructions_blob": LEGACY_INSTRUCTIONS_BLOB,
            "legacy_registry_blob": LEGACY_REGISTRY_BLOB,
            "score_utils_blob": SCORE_UTILS_BLOB,
        },
        "recognition": {
            "exact_instruction_multiset_rows": exact_id_set_matches,
            "all_ground_truth_ids_recognized_rows": subset_id_matches,
        },
        "score": {
            "candidate_rows": int(counts["candidate_rows"]),
            "full_rows": int(counts["full_rows"]),
            "partial_rows": int(counts["partial_rows"]),
            "zero_rows": int(counts["zero_rows"]),
            "strict_livebench_score_mass": score_sum,
            "strict_livebench_mean_percent": public_percent,
            "clears_65_7_on_this_public_population": public_percent >= 65.7,
        },
        "instruction_count_distribution": dict(sorted(instruction_distribution.items())),
        "by_arity": arity_rows,
        "by_checker": checker_rows,
        "blocked_or_error_reasons": dict(reason_counts.most_common()),
        "failure_samples": failures,
        "hard_nonclaims": [
            "PUBLIC_GOOGLE_IFEVAL_POPULATION_ONLY",
            "NO_TERMINAL_LIVEBENCH_PROMPT_KWARGS_IDS_RESPONSES_OR_SCORES_READ",
            "NO_TERMINAL_POPULATION_EQUIVALENCE_INFERRED",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "SCORE_CONTRACT_SUCCESS_DOES_NOT_PROVE_SEMANTIC_QUALITY",
        ],
        "accounting": {
            "new_terminal_cases_exposed": 0,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "ownership_credit_delta": 0,
            "incremental_spend_usd": 0,
        },
    }
    pathlib.Path("livebench_legacy541_composition_public_audit_v1.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
