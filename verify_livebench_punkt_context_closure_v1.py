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
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_composer_v2_20261005"

EXPECTED_SUBJECT_BLOBS = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py":
        "71e637c70edf1c582e28ea38b3b798965c803a06",
}
PRECOMMIT_COMMIT = "4c9201075e0b39a4cbcc978718205f0f3d1c4bc5"
PARAMETRIC_REDUCTION_BLOB = "a9ab9064b447ed669d2404a7a65f6c429c51ae85"
NUMERIC_QUOTIENT_BLOB = "72189bb8adb12ad36a52ee666a1f79fbb201b06b"
POINTWISE_MINCUT_BLOB = "0d4e563b618f8fd7f37396a88738cefb50979ff3"

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
NLTK_WHEEL_SHA256 = "ff9598a8e20518ee0d557745890cc4435b9578489e2dcbc69c4f81fa060caf7c"
NLTK_DATA_COMMIT = "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"
NLTK_DATA_BLOBS = {
    "packages/tokenizers/punkt.zip": "da7ffbd1e6fd6cc5c2f6879c2d4da23c7691944c",
    "packages/tokenizers/punkt_tab.zip": "5e5ff6137d5ee6025e400d1c3a7b21914c48b635",
}

EXIST_WORDS = ["apple", "bridge", "cloud", "dream", "energy"]
FORBIDDEN_WORDS = ["western", "sentence", "signal", "dump", "spot"]
NTH_WORD = "river"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def git_blob(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def C(iid: str, **slots):
    return {"instruction_id": iid, "slots": slots}


def verify_bindings():
    got = {
        rel: git_blob(SUBJECT / rel)
        for rel in EXPECTED_SUBJECT_BLOBS
    }
    assert got == EXPECTED_SUBJECT_BLOBS, (got, EXPECTED_SUBJECT_BLOBS)

    live = pathlib.Path("/tmp/LiveBench")
    head = run(["git", "-C", str(live), "rev-parse", "HEAD"], capture_output=True).stdout.strip()
    assert head == LIVEBENCH_COMMIT, head
    for rel, expected in LIVEBENCH_BLOBS.items():
        observed = run(
            ["git", "-C", str(live), "rev-parse", f"HEAD:{rel}"],
            capture_output=True,
        ).stdout.strip()
        assert observed == expected, (rel, observed, expected)

    data_repo = pathlib.Path("/tmp/nltk_data_repo")
    data_head = run(
        ["git", "-C", str(data_repo), "rev-parse", "HEAD"], capture_output=True
    ).stdout.strip()
    assert data_head == NLTK_DATA_COMMIT, data_head
    for rel, expected in NLTK_DATA_BLOBS.items():
        observed = run(
            ["git", "-C", str(data_repo), "rev-parse", f"HEAD:{rel}"],
            capture_output=True,
        ).stdout.strip()
        assert observed == expected, (rel, observed, expected)

    wheel = pathlib.Path(os.environ["PINNED_NLTK_WHEEL"])
    assert wheel.is_file(), wheel
    assert sha256(wheel) == NLTK_WHEEL_SHA256, sha256(wheel)
    assert importlib.metadata.version("nltk") == NLTK_VERSION

    return got


def slot_options(ids, comp):
    opts = []
    for iid in ids:
        if iid == comp.SENTENCES:
            continue
        if iid == comp.EXIST:
            vals = [C(iid, keywords=EXIST_WORDS)]
        elif iid == comp.FORBIDDEN:
            vals = [C(iid, forbidden_words=FORBIDDEN_WORDS)]
        elif iid == comp.WORDS:
            # Complete Punkt quotient: less-than emits no padding; every
            # at-least public threshold emits >=1 punctuation-free pad token.
            vals = [
                C(iid, num_words=100, relation="less than"),
                C(iid, num_words=100, relation="at least"),
                C(iid, num_words=500, relation="at least"),
            ]
        elif iid == comp.NTH:
            vals = [
                C(iid, num_paragraphs=p, nth_paragraph=k, first_word=NTH_WORD)
                for p in range(1, 6)
                for k in range(1, p + 1)
            ]
        elif iid == comp.POSTSCRIPT:
            vals = [
                C(iid, postscript_marker="P.S."),
                C(iid, postscript_marker="P.P.S"),
            ]
        elif iid == comp.BULLETS:
            vals = [C(iid, num_bullets=n) for n in range(1, 6)]
        elif iid == comp.TITLE:
            vals = [C(iid)]
        elif iid == comp.SECTIONS:
            vals = [
                C(iid, section_spliter=s, num_sections=n)
                for s in ("Section", "SECTION")
                for n in range(1, 6)
            ]
        elif iid == comp.END:
            vals = [
                C(iid, end_phrase="Any other questions?"),
                C(iid, end_phrase="Is there anything else I can help with?"),
            ]
        elif iid == comp.QUOTE:
            vals = [C(iid)]
        elif iid in {comp.PARAGRAPHS, comp.JSON_ID, comp.REPEAT, comp.TWO}:
            raise AssertionError("SENTENCE_CONFLICT_GRAPH_DRIFT:" + iid)
        else:
            raise AssertionError("UNKNOWN_ACTIVE_ID:" + iid)
        opts.append(vals)
    return opts


def main() -> int:
    subject_blobs = verify_bindings()

    live = pathlib.Path("/tmp/LiveBench")
    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))

    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from instruction_following_eval import instructions_registry, instructions_util

    # Force exact pinned Punkt data path.
    import nltk
    nltk.data.path[:] = ["/tmp/nltk_data"]
    tokenizer = instructions_util._get_sentence_tokenizer()
    assert tokenizer is not None

    sentence_sets = [
        ids for ids in arch.enumerate_compatible_sets()
        if comp.SENTENCES in ids
    ]
    assert len(arch.enumerate_compatible_sets()) == 928
    assert sentence_sets

    counts = Counter()
    failures = []
    sentence_cache = {}

    def count_sentences(text: str) -> int:
        if text not in sentence_cache:
            sentence_cache[text] = len(tokenizer.tokenize(text))
        return sentence_cache[text]

    def exact_sentence_checker(contract, response: str) -> bool:
        cls = instructions_registry.INSTRUCTION_DICT[comp.SENTENCES]
        checker = cls(comp.SENTENCES)
        checker.build_description(**dict(contract["slots"]))
        return bool(response.strip()) and bool(checker.check_following(response))

    for set_index, ids in enumerate(sentence_sets):
        opts = slot_options(ids, comp)
        products = itertools.product(*opts) if opts else [()]
        for profile_index, choice in enumerate(products):
            base = list(choice)

            # Threshold 1 is the already-proved mandatory-loss coordinate.
            lt1 = base + [C(comp.SENTENCES, num_sentences=1, relation="less than")]
            out1 = comp.compose_contracts(lt1)
            if out1.get("status") != "PROVED_UNSAT" or (
                "STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE"
                not in (out1.get("hard_unsat_reasons") or [])
            ):
                failures.append({
                    "kind": "lt1_not_proved_unsat",
                    "set_index": set_index,
                    "ids": list(ids),
                    "profile_index": profile_index,
                    "out": out1,
                })
                if len(failures) >= 50:
                    break
            counts["lt1_unsat_profiles"] += 1

            # Every public less-than threshold 2..20 produces the same response.
            # Prove the hardest threshold (<2); response identity with <20 binds
            # the threshold-irrelevance directly to the exact composer bytes.
            lt2c = C(comp.SENTENCES, num_sentences=2, relation="less than")
            lt20c = C(comp.SENTENCES, num_sentences=20, relation="less than")
            lt2 = comp.compose_contracts(base + [lt2c])
            lt20 = comp.compose_contracts(base + [lt20c])
            if lt2.get("status") != "CANDIDATE_WITNESS" or lt20.get("status") != "CANDIDATE_WITNESS":
                failures.append({
                    "kind": "lt_candidate_missing",
                    "set_index": set_index,
                    "ids": list(ids),
                    "profile_index": profile_index,
                    "lt2": lt2,
                    "lt20": lt20,
                })
            elif lt2["response"] != lt20["response"]:
                failures.append({
                    "kind": "lt_threshold_changed_response",
                    "set_index": set_index,
                    "ids": list(ids),
                    "profile_index": profile_index,
                })
            else:
                sc = count_sentences(lt2["response"])
                if not sc < 2 or not exact_sentence_checker(lt2c, lt2["response"]):
                    failures.append({
                        "kind": "lt2_punkt_failure",
                        "set_index": set_index,
                        "ids": list(ids),
                        "profile_index": profile_index,
                        "sentence_count": sc,
                        "response": lt2["response"],
                    })
                counts["lt2_contexts"] += 1

            # Lower-bound relation: exact public thresholds 1..20. Extra
            # question-mark sentence(s) are harmless; undercount is forbidden.
            for n in range(1, 21):
                sc_contract = C(comp.SENTENCES, num_sentences=n, relation="at least")
                out = comp.compose_contracts(base + [sc_contract])
                if out.get("status") != "CANDIDATE_WITNESS":
                    failures.append({
                        "kind": "atleast_candidate_missing",
                        "set_index": set_index,
                        "ids": list(ids),
                        "profile_index": profile_index,
                        "n": n,
                        "out": out,
                    })
                    continue
                sc = count_sentences(out["response"])
                if sc < n or not exact_sentence_checker(sc_contract, out["response"]):
                    failures.append({
                        "kind": "atleast_punkt_undercount",
                        "set_index": set_index,
                        "ids": list(ids),
                        "profile_index": profile_index,
                        "n": n,
                        "sentence_count": sc,
                        "response": out["response"],
                    })
                counts["atleast_contexts"] += 1

            if len(failures) >= 50:
                break
        if len(failures) >= 50:
            break

    # Source-bound quotient lemmas that justify deleting the raw 401-word-
    # threshold Cartesian factor from Punkt execution.
    composer_source = (
        SUBJECT / "canonical/runtime/livebench_legacy15_contract_composer_v2.py"
    ).read_text(encoding="utf-8")
    assert 'pad = " ".join(_SAFE + "x" + str(i)' in composer_source
    assert 'if relation == "at least":' in composer_source
    assert 'elif relation != "less than":' in composer_source
    assert re.search(r'_SAFE\s*=\s*"9000001"', composer_source)
    assert not any(ch in "9000001x0123456789" for ch in ".?!")

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_CLOSURE_INDEPENDENT_VERIFICATION_V1",
        "status": (
            "PASS__PINNED_PUNKT_CONTEXT_QUOTIENT_EXHAUSTED__"
            "POST_SACRIFICE_SENTENCE_CONSTRUCTION_CLOSED__ZERO_TERMINAL_ROWS"
            if not failures else "FAIL__PUNKT_CONTEXT_COUNTEREXAMPLE_FOUND"
        ),
        "precommit_commit": PRECOMMIT_COMMIT,
        "subject_blobs": subject_blobs,
        "parametric_reduction_blob": PARAMETRIC_REDUCTION_BLOB,
        "numeric_quotient_blob": NUMERIC_QUOTIENT_BLOB,
        "pointwise_mincut_blob": POINTWISE_MINCUT_BLOB,
        "pinned_livebench": {
            "commit": LIVEBENCH_COMMIT,
            "blobs": LIVEBENCH_BLOBS,
        },
        "pinned_nltk": {
            "version": NLTK_VERSION,
            "wheel_sha256": NLTK_WHEEL_SHA256,
            "data_commit": NLTK_DATA_COMMIT,
            "data_blobs": NLTK_DATA_BLOBS,
        },
        "coverage": {
            **dict(counts),
            "compatible_structural_id_sets": 928,
            "sentence_containing_structural_id_sets": len(sentence_sets),
            "unique_punkt_responses_executed": len(sentence_cache),
            "less_than_public_thresholds_covered_by_identity_and_monotonicity": 19,
            "at_least_public_thresholds_executed": 20,
            "word_threshold_domain": [100, 500],
            "word_punkt_classes_executed": [
                "LESS_THAN_NO_PADDING",
                "AT_LEAST_PADDING_MIN",
                "AT_LEAST_PADDING_MAX",
            ],
            "nth_positions_exhausted_when_active": 15,
            "bullet_counts_exhausted_when_active": 5,
            "section_splitter_x_count_exhausted_when_active": 10,
            "postscript_markers_exhausted_when_active": 2,
            "end_phrases_exhausted_when_active": 2,
        },
        "quotient_theorem": (
            "EXACT_COMPOSER_BYTES_SHOW_WORD_AT_LEAST_PADDING_ADDS_ONLY_SPACE_"
            "SEPARATED_ALPHANUMERIC_SAFE_X_INDEX_TOKENS_WITH_NO_SENTENCE_END_"
            "PUNCTUATION__LESS_THAN_2_IS_THE_STRONGEST_LT_THRESHOLD_AND_THE_"
            "EXACT_COMPOSER_RESPONSE_IS_IDENTICAL_FOR_LT_2_THROUGH_LT_20__"
            "AT_LEAST_1_THROUGH_20_ARE_EXECUTED_EXACTLY__ALL_DISCRETE_"
            "PUNCTUATION_RELEVANT_WRAPPERS_ARE_EXHAUSTED_OVER_EVERY_COMPATIBLE_"
            "SENTENCE_CONTAINING_STRUCTURAL_ID_SET"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_frequencies_read": 0,
        "comparator_responses_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_RECEIPT_DISCHARGES_ONLY_THE_POST_SACRIFICE_PUNKT_CONSTRUCTION_REMAINDER",
            "LIVEBENCH_THRESHOLD_ACCEPTANCE_REQUIRES_SEPARATE_CLEAN_SCOPE_BINDING",
            "NO_TERMINAL_GOAL_COMPLETION_CREDIT_FROM_THIS_RECEIPT_ALONE",
        ],
    }

    out_path = pathlib.Path("livebench_punkt_context_closure_v1.json")
    out_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))

    if failures:
        raise SystemExit("PUNKT_CONTEXT_FAILURES:" + str(len(failures)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
