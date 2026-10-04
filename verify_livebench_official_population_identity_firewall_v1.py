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

EXPECTED_RUNTIME_BLOB = "7b134265f7513292248a49edeb3313acab51c665"
EXPECTED_GOVERNANCE_BLOB = "786bfb0373743702394180ba3d7f325f468edc0b"
EXPECTED_PROXY_RECEIPT_BLOB = "fd05652cda4f5b4d1f69617a5488f9bfeae4c225"

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


def load_runtime():
    assert_blob(RUNTIME, EXPECTED_RUNTIME_BLOB)
    spec = importlib.util.spec_from_file_location("identity_firewall", RUNTIME)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    gov = json.loads(assert_blob(GOVERNANCE, EXPECTED_GOVERNANCE_BLOB))
    proxy = json.loads(assert_blob(PROXY_RECEIPT, EXPECTED_PROXY_RECEIPT_BLOB))

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

    receipt = {
        "schema":"PROJECT_BRAIN_LIVEBENCH_OFFICIAL_POPULATION_IDENTITY_FIREWALL_INDEPENDENT_VERIFICATION_V1",
        "status":"PASS__PROXY_ONLY_LEGACY_COLLAPSE_FAILS_CLOSED__DUAL_FAMILY_ESCAPE_VERIFIED",
        "brain_runtime_git_blob_sha":EXPECTED_RUNTIME_BLOB,
        "brain_governance_git_blob_sha":EXPECTED_GOVERNANCE_BLOB,
        "historical_proxy_receipt_git_blob_sha":EXPECTED_PROXY_RECEIPT_BLOB,
        "upstream_livebench_commit":UPSTREAM_COMMIT,
        "upstream_readme_git_blob_sha":EXPECTED_README_BLOB,
        "upstream_changelog_git_blob_sha":EXPECTED_CHANGELOG_BLOB,
        "upstream_router_git_blob_sha":EXPECTED_ROUTER_BLOB,
        "proved":[
            "PUBLIC_HF_PROXY_CAN_LAG_CURRENT_RELEASE",
            "2025_11_25_REFRESHED_INSTRUCTION_FOLLOWING_AND_IS_SCORER_ROUTING_BOUNDARY",
            "VERIFIED_PROXY_IS_200_LEGACY_ROWS",
            "PROXY_CARDINALITY_DOES_NOT_BIND_OFFICIAL_2026_ROW_IDENTITY",
            "PROXY_ONLY_SINGLE_FAMILY_COLLAPSE_FAILS_CLOSED",
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
