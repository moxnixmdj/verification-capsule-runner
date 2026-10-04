#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import urllib.request

SUBJECT_DIR = pathlib.Path("subject/livebench_official_population_identity_firewall_v1")
RUNTIME = SUBJECT_DIR / "livebench_official_population_identity_firewall_v1.py"
GOVERNANCE = SUBJECT_DIR / "LIVEBENCH_OFFICIAL_POPULATION_IDENTITY_TRUTH_REPAIR_V1.json"
PROXY_RECEIPT = SUBJECT_DIR / "LIVEBENCH_ACTIVE_SCORER_FAMILY_INDEPENDENT_VERIFICATION_20261004_V1.json"
HISTORICAL_POPULATION_VERIFIER = SUBJECT_DIR / "verify-livebench-if-release-population-v2.yml"
ROOT_PRECEDENCE_RUNTIME = SUBJECT_DIR / "livebench_root_identity_precedence_v1.py"
ROOT_PRECEDENCE_GOVERNANCE = SUBJECT_DIR / "LIVEBENCH_ROOT_IDENTITY_PRECEDENCE_TRUTH_REPAIR_V1.json"
V6_RECONCILIATION = SUBJECT_DIR / "v6_reconciliation.json"
V6_EXECUTION_LOG = SUBJECT_DIR / "v6_execution.log"
V6_HISTORICAL_VERIFIER = SUBJECT_DIR / "verify_livebench_v6_forced_fail_20261004.py"

EXPECTED_RUNTIME_BLOB = "7b134265f7513292248a49edeb3313acab51c665"
EXPECTED_GOVERNANCE_BLOB = "786bfb0373743702394180ba3d7f325f468edc0b"
EXPECTED_PROXY_RECEIPT_BLOB = "fd05652cda4f5b4d1f69617a5488f9bfeae4c225"
EXPECTED_HISTORICAL_POPULATION_VERIFIER_BLOB = "043e9b8339fca0effc921cb1d721567e5e0d0358"
EXPECTED_ROOT_PRECEDENCE_RUNTIME_BLOB = "1b709f4c542720d8ccddb7a807b4977df8be1eba"
EXPECTED_ROOT_PRECEDENCE_GOVERNANCE_BLOB = "e50a34646baeefce79077dc19cafa209a98e5966"
EXPECTED_V6_RECONCILIATION_BLOB = "b1e14f11d97673a499f2d9a5e2c708d9aba969fb"
EXPECTED_V6_EXECUTION_LOG_BLOB = "6c9c89cd2f7e977405017cb5ddfa8033126f4bf2"
EXPECTED_V6_HISTORICAL_VERIFIER_BLOB = "bae0957c258d1211249bdc7be94244487d223cbc"

UPSTREAM_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
README_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{UPSTREAM_COMMIT}/README.md"
CHANGELOG_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{UPSTREAM_COMMIT}/changelog.md"
ROUTER_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{UPSTREAM_COMMIT}/livebench/gen_ground_truth_judgment.py"

EXPECTED_README_BLOB = "24201c730e23a98ff01f1ce422b9fc899233646f"
EXPECTED_CHANGELOG_BLOB = "97a0b6ffd845aec29f48f96ca24b96ac100e4162"
EXPECTED_ROUTER_BLOB = "b36561da5b54380c724c507462d0ee65feefeac8"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def assert_blob(path: pathlib.Path, expected: str) -> bytes:
    raw = path.read_bytes()
    actual = git_blob_sha(raw)
    assert actual == expected, (path.as_posix(), actual, expected)
    return raw


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch_pinned(url: str, expected_blob: str) -> str:
    raw = fetch(url)
    actual = git_blob_sha(raw)
    assert actual == expected_blob, (url, actual, expected_blob)
    return raw.decode("utf-8")


def load_module(path: pathlib.Path, expected_blob: str, name: str):
    assert_blob(path, expected_blob)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_runtime():
    return load_module(RUNTIME, EXPECTED_RUNTIME_BLOB, "identity_firewall")


def same_counts_do_not_imply_identity() -> None:
    tasks = ("paraphrase", "simplify", "story_generation", "summarize")
    proxy = [(f"proxy-{task}-{i:02d}", task) for task in tasks for i in range(50)]
    official = [(f"official-{task}-{i:02d}", task) for task in tasks for i in range(50)]
    assert len(proxy) == len(official) == 200
    for task in tasks:
        assert sum(t == task for _, t in proxy) == 50
        assert sum(t == task for _, t in official) == 50
    assert {qid for qid, _ in proxy}.isdisjoint({qid for qid, _ in official})


def main() -> int:
    runtime = load_runtime()
    root_precedence = load_module(
        ROOT_PRECEDENCE_RUNTIME,
        EXPECTED_ROOT_PRECEDENCE_RUNTIME_BLOB,
        "root_identity_precedence",
    )
    gov = json.loads(assert_blob(GOVERNANCE, EXPECTED_GOVERNANCE_BLOB))
    root_gov = json.loads(assert_blob(
        ROOT_PRECEDENCE_GOVERNANCE,
        EXPECTED_ROOT_PRECEDENCE_GOVERNANCE_BLOB,
    ))
    v6_rec = json.loads(assert_blob(V6_RECONCILIATION, EXPECTED_V6_RECONCILIATION_BLOB))
    v6_log = assert_blob(V6_EXECUTION_LOG, EXPECTED_V6_EXECUTION_LOG_BLOB).decode("utf-8")
    historical_v6_verifier = assert_blob(
        V6_HISTORICAL_VERIFIER,
        EXPECTED_V6_HISTORICAL_VERIFIER_BLOB,
    ).decode("utf-8")
    proxy = json.loads(assert_blob(PROXY_RECEIPT, EXPECTED_PROXY_RECEIPT_BLOB))
    historical_verifier = assert_blob(
        HISTORICAL_POPULATION_VERIFIER,
        EXPECTED_HISTORICAL_POPULATION_VERIFIER_BLOB,
    ).decode("utf-8")

    readme = fetch_pinned(README_URL, EXPECTED_README_BLOB)
    changelog = fetch_pinned(CHANGELOG_URL, EXPECTED_CHANGELOG_BLOB)
    router = fetch_pinned(ROUTER_URL, EXPECTED_ROUTER_BLOB)

    # First-party evidence: public HF data can lag the current LiveBench release.
    assert "not all questions for this release are public on Huggingface" in readme
    assert "--livebench-release-option 2024-11-25" in readme

    # First-party evidence: the scorer-boundary release materially refreshed IF.
    assert "### 2025-11-25" in changelog
    section = changelog.split("### 2025-11-25", 1)[1].split("### ", 1)[0]
    assert "instruction following" in section.lower()
    assert "newer articles" in section.lower()
    assert "new, more difficult types of instructions" in section.lower()

    # First-party routing: only pre-boundary IF rows use the old evaluator.
    compact = " ".join(router.split())
    assert 'm.question.get("livebench_release_date", "") < "2025-11-25"' in compact
    assert "old_instruction_following_matches" in router
    assert "normal_matches" in router

    # The already-verified receipt establishes a specific public proxy revision.
    pinned = proxy["pinned_inputs"]
    result = proxy["verified_result"]
    assert pinned["frozen_dataset_repository"] == "livebench/instruction_following"
    assert pinned["frozen_dataset_revision"] == "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
    assert result["active_population_count"] == 200
    assert result["legacy_ifeval_active_rows"] == 200
    assert result["modern_ifbench_active_rows"] == 0

    # Crucially, that receipt contains no content-addressed join to official 2026
    # comparator row identity. Cardinality and task counts cannot supply it.
    serialized_proxy = json.dumps(proxy, sort_keys=True).lower()
    for forbidden_identity_claim in (
        "official_row_identity_bound",
        "official_comparator_row_ids",
        "official_2026_row_ids",
        "official_2026_comparator_sha",
    ):
        assert forbidden_identity_claim not in serialized_proxy
    same_counts_do_not_imply_identity()

    # Audit the exact historical verifier that promoted "active population identity".
    # It checks leaderboard aggregate scores/counts and, separately, public-HF
    # question IDs/counts. It never obtains a leaderboard-side question-ID set.
    release_step = historical_verifier.split(
        "- name: Verify first-party release and comparator bar", 1
    )[1].split("- name: Download exact frozen HF parquet", 1)[0]
    hf_step = historical_verifier.split(
        "- name: Verify metadata-only active population", 1
    )[1].split("- name: Verify fail-closed consequence", 1)[0]
    assert "public/table_2026_06_25.csv" in release_step
    assert "public/cost_2026_06_25.csv" in release_step
    assert "nq_" in release_step
    assert "question_id" not in release_step
    assert 'cols=["question_id","task","livebench_release_date","livebench_removal_date"]' in hf_step
    assert 'ids=[r["question_id"] for r in rows]' in hf_step
    assert "len(ids)==len(set(ids))" in hf_step
    assert "table_question_ids" not in historical_verifier
    assert "official_question_ids" not in historical_verifier
    assert "leaderboard_question_ids" not in historical_verifier

    # Exact candidate semantics must fail closed on proxy-only single-family claims.
    blocked = runtime.adjudicate({
        "proxy_only_evidence": True,
        "official_row_identity_bound": False,
        "official_scorer_family": "LEGACY_IFEVAL",
    })
    assert blocked["status"] == "BLOCKED_OFFICIAL_POPULATION_IDENTITY_UNPROVED"
    assert blocked["single_family_collapse_authorized"] is False
    assert blocked["release_agnostic_successor_authorized"] is False

    legacy_bound = runtime.adjudicate({
        "official_row_identity_bound": True,
        "official_scorer_family": "LEGACY_IFEVAL",
    })
    modern_bound = runtime.adjudicate({
        "official_row_identity_bound": True,
        "official_scorer_family": "MODERN_IFBENCH",
    })
    assert legacy_bound["status"] == "PASS_OFFICIAL_IDENTITY_BOUND"
    assert modern_bound["status"] == "PASS_OFFICIAL_IDENTITY_BOUND"
    assert legacy_bound["single_family_collapse_authorized"] is True
    assert modern_bound["single_family_collapse_authorized"] is True

    universal = runtime.adjudicate({
        "official_row_identity_bound": False,
        "universal_legacy_verified": True,
        "universal_modern_verified": True,
    })
    assert universal["status"] == "PASS_IDENTITY_IRRELEVANT_BY_UNIVERSAL_COVERAGE"
    assert universal["release_agnostic_successor_authorized"] is True

    partial = runtime.adjudicate({
        "official_row_identity_bound": False,
        "universal_legacy_verified": True,
        "universal_modern_verified": False,
    })
    assert partial["status"] == "BLOCKED_OFFICIAL_POPULATION_IDENTITY_UNPROVED"
    assert "MODERN_IFBENCH_VERIFIED_COVERAGE" in partial["missing_for_identity_independent_route"]

    assert gov["problem"]["logical_gap"].startswith("NO_CONTENT_ADDRESSED_JOIN")
    assert gov["repair"]["identity_independent_escape"] == (
        "VERIFY_SUCCESSOR_COVERAGE_FOR_BOTH_LEGACY_IFEVAL_AND_MODERN_IFBENCH"
    )

    # Preserve the exact V6 failure, but prove it is scoped to the bound proxy.
    cases = []
    terminal = None
    for line in v6_log.splitlines():
        if line.startswith("LIVEBENCH_CASE_RECEIPT="):
            cases.append(json.loads(line.split("=", 1)[1]))
        elif line.startswith("LIVEBENCH_TERMINAL_RESULT="):
            terminal = json.loads(line.split("=", 1)[1])
    assert len(cases) == 72
    assert len({x["question_id"] for x in cases}) == 72
    assert all(float(x["score"]) == 0.0 for x in cases)
    assert all(x.get("scoring_error") is None for x in cases)
    assert terminal is not None
    assert terminal["dataset_revision"] == "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
    assert terminal["dataset_sha256"] == "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
    assert int(terminal["population_count"]) == 200
    assert float(terminal["conservative_full_population_upper_percent"]) == 64.0
    assert terminal["status"] == "FAIL_FORCED"
    assert v6_rec["threshold_proof"]["conservative_full_population_upper_percent"] == 64
    assert 'assert len(cases)==72' in historical_v6_verifier
    assert 'assert all(float(x["score"])==0.0 for x in cases)' in historical_v6_verifier
    assert 'assert all(x.get("scoring_error") is None for x in cases)' in historical_v6_verifier

    # Upstream identity has precedence over downstream exact proxy score.
    quarantined = root_precedence.adjudicate({
        "proxy_v6_exact_fail": True,
        "official_population_identity_bound": False,
    })
    assert quarantined["status"] == "PROXY_EXACT_FAIL_QUARANTINED_FROM_OFFICIAL_ROOT_CLASSIFICATION"
    assert quarantined["terminal_predicate_root"] == "ROOT2_ONLY"
    assert quarantined["proxy_failure_preserved"] is True
    assert quarantined["root1_authorized"] is False

    promotable = root_precedence.adjudicate({
        "proxy_v6_exact_fail": True,
        "official_population_identity_bound": True,
    })
    assert promotable["status"] == "PROXY_EXACT_FAIL_PROMOTABLE_BY_PROVED_POPULATION_IDENTITY"
    assert promotable["terminal_predicate_root"] == "ROOT1_POSITIVE_OPERATIVE_GAP"
    assert promotable["root1_authorized"] is True

    direct_fail = root_precedence.adjudicate({"official_exact_fail": True})
    assert direct_fail["terminal_predicate_root"] == "ROOT1_POSITIVE_OPERATIVE_GAP"
    direct_pass = root_precedence.adjudicate({"official_exact_pass": True})
    assert direct_pass["terminal_predicate_root"] == "CLOSED_PASS"

    assert root_gov["precedence_theorem"]["statement"].startswith(
        "ROOT_CLASSIFICATION_FOR_THE_OFFICIAL_TERMINAL_PREDICATE"
    )

    receipt = {
        "schema":"PROJECT_BRAIN_LIVEBENCH_OFFICIAL_POPULATION_IDENTITY_FIREWALL_INDEPENDENT_VERIFICATION_V1",
        "status":"PASS__POPULATION_IDENTITY_FIREWALL_AND_ROOT_PRECEDENCE__V6_PROXY_FAILURE_PRESERVED",
        "brain_runtime_git_blob_sha":EXPECTED_RUNTIME_BLOB,
        "brain_governance_git_blob_sha":EXPECTED_GOVERNANCE_BLOB,
        "historical_proxy_receipt_git_blob_sha":EXPECTED_PROXY_RECEIPT_BLOB,
        "historical_population_verifier_git_blob_sha":EXPECTED_HISTORICAL_POPULATION_VERIFIER_BLOB,
        "root_precedence_runtime_git_blob_sha":EXPECTED_ROOT_PRECEDENCE_RUNTIME_BLOB,
        "root_precedence_governance_git_blob_sha":EXPECTED_ROOT_PRECEDENCE_GOVERNANCE_BLOB,
        "v6_reconciliation_git_blob_sha":EXPECTED_V6_RECONCILIATION_BLOB,
        "v6_execution_log_git_blob_sha":EXPECTED_V6_EXECUTION_LOG_BLOB,
        "v6_historical_verifier_git_blob_sha":EXPECTED_V6_HISTORICAL_VERIFIER_BLOB,
        "upstream_livebench_commit":UPSTREAM_COMMIT,
        "upstream_readme_git_blob_sha":EXPECTED_README_BLOB,
        "upstream_changelog_git_blob_sha":EXPECTED_CHANGELOG_BLOB,
        "upstream_router_git_blob_sha":EXPECTED_ROUTER_BLOB,
        "proved":[
            "PUBLIC_HF_PROXY_CAN_LAG_CURRENT_RELEASE",
            "2025_11_25_REFRESHED_INSTRUCTION_FOLLOWING_AND_IS_SCORER_ROUTING_BOUNDARY",
            "VERIFIED_PROXY_IS_200_LEGACY_ROWS",
            "HISTORICAL_POPULATION_VERIFIER_HAS_NO_LEADERBOARD_SIDE_QUESTION_ID_SET_OR_ROW_ID_JOIN",
            "PROXY_CARDINALITY_DOES_NOT_BIND_OFFICIAL_2026_ROW_IDENTITY",
            "PROXY_ONLY_SINGLE_FAMILY_COLLAPSE_FAILS_CLOSED",
            "V6_PROXY_EXACT_FAILURE_72_OF_72_ZERO_SCORES_IS_PRESERVED",
            "PROXY_EXACT_FAILURE_CANNOT_RECLASSIFY_OFFICIAL_PREDICATE_WITHOUT_POPULATION_IDENTITY",
            "DUAL_FAMILY_VERIFIED_COVERAGE_CAN_DELETE_IDENTITY_DEPENDENCY",
        ],
        "not_proved":[
            "OFFICIAL_2026_COMPARATOR_IS_LEGACY_ONLY",
            "OFFICIAL_2026_COMPARATOR_IS_MODERN_ONLY",
            "OFFICIAL_2026_COMPARATOR_ROW_IDS_EQUAL_PROXY_ROW_IDS",
        ],
        "terminal_prompt_or_response_content_read":False,
        "new_terminal_cases_consumed":0,
        "incremental_spend_usd":0,
        "acceptance_credit":False,
    }
    pathlib.Path("livebench_official_population_identity_firewall_v1_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
