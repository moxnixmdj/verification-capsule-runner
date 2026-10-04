#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.metadata
import itertools
import json
import os
import pathlib
import re
import subprocess
import sys
import zipfile
from collections import Counter

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
EVALUATION_MAIN_BLOB = "4a341984936c4d609644a3b77f8c030ac5aa7269"

PINNED_PYTHON = (3, 12, 10)
PINNED_NLTK_VERSION = "3.10.3"
PINNED_NLTK_WHEEL_SHA256 = "ff9598a8e20518ee0d557745890cc4435b9578489e2dcbc69c4f81fa060caf7c"
PINNED_NLTK_DATA_COMMIT = "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"
PINNED_DATA_ARCHIVES = {
    "punkt.zip": "da7ffbd1e6fd6cc5c2f6879c2d4da23c7691944c",
    "punkt_tab.zip": "5e5ff6137d5ee6025e400d1c3a7b21914c48b635",
}

ARCH_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
FEAS_BLOB = "7477f5ea5bdeac3595ee2784a38d078fe2f385b0"
COMPOSER_BLOB = "d73ec366b32252996258eae6d10d67d4d6a5e042"
PLANNER_BLOB = "71e637c70edf1c582e28ea38b3b798965c803a06"

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_composer_v2_20261005"
ARCH = SUBJECT / "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py"
FEAS = SUBJECT / "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py"
COMPOSER = SUBJECT / "canonical/runtime/livebench_legacy15_contract_composer_v2.py"
PLANNER = SUBJECT / "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def hash_object(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()


def contract(iid: str, **slots):
    return {"instruction_id": iid, "slots": slots}


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_member(name: str) -> pathlib.Path:
    rel = pathlib.Path(name)
    assert not rel.is_absolute() and ".." not in rel.parts, ("unsafe archive member", name)
    return rel


def verify_hermetic_nltk() -> dict:
    assert tuple(sys.version_info[:3]) == PINNED_PYTHON, sys.version_info
    assert importlib.metadata.version("nltk") == PINNED_NLTK_VERSION

    wheel = pathlib.Path(os.environ["NLTK_WHEEL"]).resolve()
    assert wheel.is_file(), wheel
    assert sha256_file(wheel) == PINNED_NLTK_WHEEL_SHA256

    import nltk

    package_root = pathlib.Path(nltk.__file__).resolve().parent
    site_root = package_root.parent
    package_files = 0
    with zipfile.ZipFile(wheel) as zf:
        names = [
            name for name in zf.namelist()
            if name.startswith("nltk/") and not name.endswith("/")
        ]
        assert names
        for name in names:
            rel = safe_member(name)
            installed = site_root / rel
            assert installed.is_file(), ("missing installed nltk file", rel)
            assert installed.read_bytes() == zf.read(name), ("installed nltk drift", rel)
            package_files += 1

    data_repo = pathlib.Path("/tmp/nltk_data_repo")
    data_commit = run(
        ["git", "-C", str(data_repo), "rev-parse", "HEAD"],
        capture_output=True,
    ).stdout.strip()
    assert data_commit == PINNED_NLTK_DATA_COMMIT

    data_root = pathlib.Path(os.environ["NLTK_DATA"]).resolve()
    extracted_files = 0
    archive_blobs = {}
    for archive_name, expected_blob in PINNED_DATA_ARCHIVES.items():
        archive = data_root / "tokenizers" / archive_name
        assert archive.is_file(), archive
        observed_blob = hash_object(archive)
        assert observed_blob == expected_blob, (archive_name, observed_blob, expected_blob)
        archive_blobs["tokenizers/" + archive_name] = observed_blob
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                rel = safe_member(info.filename)
                extracted = data_root / "tokenizers" / rel
                assert extracted.is_file(), ("missing extracted punkt file", extracted)
                assert extracted.read_bytes() == zf.read(info.filename), (
                    "extracted punkt drift",
                    extracted,
                )
                extracted_files += 1

    nltk.data.path[:] = [str(data_root)]
    nltk.data.load("nltk:tokenizers/punkt/english.pickle")

    return {
        "python": ".".join(map(str, PINNED_PYTHON)),
        "nltk_version": PINNED_NLTK_VERSION,
        "nltk_wheel_sha256": PINNED_NLTK_WHEEL_SHA256,
        "nltk_data_commit": PINNED_NLTK_DATA_COMMIT,
        "nltk_data_archive_git_blobs": archive_blobs,
        "verified_installed_nltk_package_file_count": package_files,
        "verified_extracted_nltk_data_file_count": extracted_files,
        "network_used_during_proof_step": False,
    }


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_member(name: str) -> pathlib.Path:
    rel = pathlib.Path(name)
    assert not rel.is_absolute() and ".." not in rel.parts, ("unsafe archive member", name)
    return rel


def verify_hermetic_nltk() -> dict:
    assert tuple(sys.version_info[:3]) == PINNED_PYTHON, sys.version_info
    assert importlib.metadata.version("nltk") == PINNED_NLTK_VERSION

    wheel = pathlib.Path(os.environ["NLTK_WHEEL"]).resolve()
    assert wheel.is_file(), wheel
    assert sha256_file(wheel) == PINNED_NLTK_WHEEL_SHA256

    import nltk

    package_root = pathlib.Path(nltk.__file__).resolve().parent
    site_root = package_root.parent
    package_files = 0
    with zipfile.ZipFile(wheel) as zf:
        names = [
            name for name in zf.namelist()
            if name.startswith("nltk/") and not name.endswith("/")
        ]
        assert names
        for name in names:
            rel = safe_member(name)
            installed = site_root / rel
            assert installed.is_file(), ("missing installed nltk file", rel)
            assert installed.read_bytes() == zf.read(name), ("installed nltk drift", rel)
            package_files += 1

    data_repo = pathlib.Path("/tmp/nltk_data_repo")
    data_commit = run(
        ["git", "-C", str(data_repo), "rev-parse", "HEAD"],
        capture_output=True,
    ).stdout.strip()
    assert data_commit == PINNED_NLTK_DATA_COMMIT

    data_root = pathlib.Path(os.environ["NLTK_DATA"]).resolve()
    extracted_files = 0
    archive_blobs = {}
    for archive_name, expected_blob in PINNED_DATA_ARCHIVES.items():
        archive = data_root / "tokenizers" / archive_name
        assert archive.is_file(), archive
        observed_blob = hash_object(archive)
        assert observed_blob == expected_blob, (archive_name, observed_blob, expected_blob)
        archive_blobs["tokenizers/" + archive_name] = observed_blob
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                rel = safe_member(info.filename)
                extracted = data_root / "tokenizers" / rel
                assert extracted.is_file(), ("missing extracted punkt file", extracted)
                assert extracted.read_bytes() == zf.read(info.filename), (
                    "extracted punkt drift",
                    extracted,
                )
                extracted_files += 1

    nltk.data.path[:] = [str(data_root)]
    nltk.data.load("nltk:tokenizers/punkt/english.pickle")

    return {
        "python": ".".join(map(str, PINNED_PYTHON)),
        "nltk_version": PINNED_NLTK_VERSION,
        "nltk_wheel_sha256": PINNED_NLTK_WHEEL_SHA256,
        "nltk_data_commit": PINNED_NLTK_DATA_COMMIT,
        "nltk_data_archive_git_blobs": archive_blobs,
        "verified_installed_nltk_package_file_count": package_files,
        "verified_extracted_nltk_data_file_count": extracted_files,
        "network_used_during_proof_step": False,
    }


def main() -> int:
    assert hash_object(ARCH) == ARCH_BLOB
    assert hash_object(FEAS) == FEAS_BLOB
    assert hash_object(COMPOSER) == COMPOSER_BLOB
    assert hash_object(PLANNER) == PLANNER_BLOB
    runtime_binding = verify_hermetic_nltk()

    live = pathlib.Path("/tmp/LiveBenchPunkt")
    assert run(["git", "-C", str(live), "rev-parse", "HEAD"], capture_output=True).stdout.strip() == LIVEBENCH_COMMIT
    for path, expected in {
        "livebench/if_runner/instruction_following_eval/instructions.py": INSTRUCTIONS_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_registry.py": REGISTRY_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_util.py": UTIL_BLOB,
        "livebench/if_runner/instruction_following_eval/evaluation_main.py": EVALUATION_MAIN_BLOB,
    }.items():
        got = run(["git", "-C", str(live), "rev-parse", f"HEAD:{path}"], capture_output=True).stdout.strip()
        assert got == expected, (path, got, expected)

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as opt
    from instruction_following_eval import instructions_registry, instructions_util

    words = list(instructions_util.WORD_LIST)
    assert len(words) == 1525 and len(set(words)) == 1525
    assert all(re.fullmatch(r"[A-Za-z]+", w) for w in words)

    required = ["apple", "bridge", "cloud", "dream", "energy"]
    forbidden = ["western", "signal", "dump", "spot", "potato"]
    first_word = "river"
    assert all(w in words for w in required + forbidden + [first_word])
    assert not set(required) & set(forbidden)
    assert first_word not in forbidden

    # Source-level lexical guard for fixed punctuation-bearing literals.
    end_phrases = (
        "Any other questions?",
        "Is there anything else I can help with?",
    )
    wordset = set(words)
    end_intersection = {
        w.lower()
        for phrase in end_phrases
        for w in re.findall(r"[A-Za-z]+", phrase)
        if w.lower() in wordset
    }
    assert end_intersection == {"other", "anything", "can", "help"}
    assert "p" not in wordset and "s" not in wordset

    def kwargs_for(c):
        return dict(c.get("slots") or {})

    def exact_follow(c, response: str) -> bool:
        iid = c["instruction_id"]
        checker = instructions_registry.INSTRUCTION_DICT[iid](iid)
        checker.build_description(**kwargs_for(c))
        return bool(response.strip()) and bool(checker.check_following(response))

    def exact_flags(contracts, response):
        return [exact_follow(c, response) for c in contracts]

    def slot_options(iid):
        if iid == comp.EXIST:
            return ({"keywords": required},)
        if iid == comp.FORBIDDEN:
            return ({"forbidden_words": forbidden},)
        if iid == comp.WORDS:
            # Parametric representatives: minimum upper bound and both endpoints
            # of the monotone lower-bound padding range.
            return (
                {"num_words": 100, "relation": "less than"},
                {"num_words": 100, "relation": "at least"},
                {"num_words": 500, "relation": "at least"},
            )
        if iid == comp.NTH:
            return tuple(
                {"num_paragraphs": p, "nth_paragraph": k, "first_word": first_word}
                for p in range(1, 6)
                for k in range(1, p + 1)
            )
        if iid == comp.POSTSCRIPT:
            return (
                {"postscript_marker": "P.S."},
                {"postscript_marker": "P.P.S"},
            )
        if iid == comp.BULLETS:
            return tuple({"num_bullets": n} for n in range(1, 6))
        if iid == comp.TITLE:
            return ({},)
        if iid == comp.SECTIONS:
            return tuple(
                {"section_spliter": splitter, "num_sections": n}
                for splitter in ("Section", "SECTION")
                for n in range(1, 6)
            )
        if iid == comp.END:
            return tuple({"end_phrase": phrase} for phrase in end_phrases)
        if iid == comp.QUOTE:
            return ({},)
        if iid == comp.PARAGRAPHS:
            raise AssertionError("SENTENCE_PARAGRAPH_CONFLICT_DRIFT")
        if iid in {comp.JSON_ID, comp.REPEAT, comp.TWO}:
            raise AssertionError("SPECIAL_ROUTE_WITH_SENTENCE_CONFLICT_DRIFT:" + iid)
        if iid == comp.SENTENCES:
            raise AssertionError("SENTENCE_SLOT_IS_CONTROLLED_SEPARATELY")
        raise AssertionError("UNKNOWN_ID:" + iid)

    def make_contracts(ids, slots_by_id, relation, n):
        out = []
        for iid in ids:
            if iid == comp.SENTENCES:
                out.append(contract(iid, num_sentences=n, relation=relation))
            else:
                out.append(contract(iid, **slots_by_id[iid]))
        return out

    counts = Counter()
    failures = []
    sentence_sets = [ids for ids in arch.enumerate_compatible_sets() if comp.SENTENCES in ids]
    assert sentence_sets

    for set_index, ids in enumerate(sentence_sets):
        others = [iid for iid in ids if iid != comp.SENTENCES]
        domains = [slot_options(iid) for iid in others]
        for combo_index, combo in enumerate(itertools.product(*domains)):
            slots_by_id = dict(zip(others, combo))
            counts["sentence_contexts"] += 1

            # At-least is exhaustively checked for every public threshold.
            for n in range(1, 21):
                contracts = make_contracts(ids, slots_by_id, "at least", n)
                plan = opt.solve_contracts(contracts)
                counts["at_least_cases"] += 1
                if plan.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
                    failures.append(("atleast_status", set_index, combo_index, n, plan))
                    continue
                response = str(plan["response"])
                sentence_count = instructions_util.count_sentences(response)
                flags = exact_flags(contracts, response)
                exact_pass = sum(flags)
                if sentence_count < n:
                    failures.append(("atleast_sentence_count", set_index, combo_index, n, sentence_count, response))
                if exact_pass != int(plan["theoretical_max_pass_count"]):
                    failures.append(("atleast_pointwise", set_index, combo_index, n, flags, plan, response))

            # less-than-one is intrinsically lost under strict nonempty scoring.
            contracts = make_contracts(ids, slots_by_id, "less than", 1)
            plan = opt.solve_contracts(contracts)
            counts["lt_one_cases"] += 1
            if plan.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
                failures.append(("lt1_status", set_index, combo_index, plan))
            else:
                response = str(plan["response"])
                flags = exact_flags(contracts, response)
                sentence_count = instructions_util.count_sentences(response)
                if comp.SENTENCES not in set(plan.get("sacrificed_instruction_ids") or []):
                    failures.append(("lt1_not_sacrificed", set_index, combo_index, plan))
                if sentence_count < 1:
                    failures.append(("lt1_nonempty_punkt_drift", set_index, combo_index, sentence_count, response))
                if sum(flags) != int(plan["theoretical_max_pass_count"]):
                    failures.append(("lt1_pointwise", set_index, combo_index, flags, plan, response))

            # For n>=2 the composer code path is threshold-invariant, but the
            # exact checker threshold changes. Exhaust all 19 public values.
            canonical_response = None
            canonical_count = None
            for n in range(2, 21):
                contracts = make_contracts(ids, slots_by_id, "less than", n)
                plan = opt.solve_contracts(contracts)
                counts["lt_ge_two_cases"] += 1
                if plan.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
                    failures.append(("lt_status", set_index, combo_index, n, plan))
                    continue
                response = str(plan["response"])
                sentence_count = instructions_util.count_sentences(response)
                flags = exact_flags(contracts, response)
                if canonical_response is None:
                    canonical_response = response
                    canonical_count = sentence_count
                elif response != canonical_response or sentence_count != canonical_count:
                    failures.append(("lt_threshold_output_drift", set_index, combo_index, n))
                if not sentence_count < n:
                    failures.append(("lt_sentence_count", set_index, combo_index, n, sentence_count, response))
                if sum(flags) != int(plan["theoretical_max_pass_count"]):
                    failures.append(("lt_pointwise", set_index, combo_index, n, flags, plan, response))

            if failures and len(failures) >= 100:
                break
        if failures and len(failures) >= 100:
            break

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_INDEPENDENT_VERIFICATION_V1",
        "status": "FAIL" if failures else "PASS__ALL_GENERATOR_ADMITTED_SENTENCE_CONTEXT_QUOTIENTS__EXACT_PINNED_PUNKT",
        "pinned_livebench": {
            "commit": LIVEBENCH_COMMIT,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "registry_blob": REGISTRY_BLOB,
            "instructions_util_blob": UTIL_BLOB,
            "evaluation_main_blob": EVALUATION_MAIN_BLOB,
            "strict_nonempty_gate_bound": True,
        },
        "hermetic_runtime": runtime_binding,
        "subject_blobs": {
            "archetypes": ARCH_BLOB,
            "slot_feasibility": FEAS_BLOB,
            "composer": COMPOSER_BLOB,
            "pointwise_planner": PLANNER_BLOB,
        },
        "sentence_id_sets": len(sentence_sets),
        "coverage": dict(counts),
        "fixed_end_phrase_public_word_intersection": sorted(end_intersection),
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_instruction_ids_read": 0,
        "acceptance_credit_delta": 0,
        "failures": failures[:100],
        "hard_nonclaims": [
            "THIS_RECEIPT_DISCHARGES_THE_PINNED_PUNKT_CONTEXT_REMAINDER_ONLY",
            "PROMOTION_REQUIRES_BINDING_WITH_THE_PARAMETRIC_NON_SENTENCE_REDUCTION",
            "NO_TERMINAL_ROWS_WERE_READ",
        ],
    }
    pathlib.Path("livebench_punkt_context_v1.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
