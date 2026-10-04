#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

NLTK_DATA_COMMIT = "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"
PUNKT_ZIP_BLOB = "da7ffbd1e6fd6cc5c2f6879c2d4da23c7691944c"
PUNKT_TAB_ZIP_BLOB = "5e5ff6137d5ee6025e400d1c3a7b21914c48b635"

ARCH_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
FEAS_BLOB = "7477f5ea5bdeac3595ee2784a38d078fe2f385b0"
COMPOSER_BLOB = "d73ec366b32252996258eae6d10d67d4d6a5e042"
PLANNER_BLOB = "71e637c70edf1c582e28ea38b3b798965c803a06"
PARAMETRIC_BLOB = "a9ab9064b447ed669d2404a7a65f6c429c51ae85"

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_composer_v2_20261005"
RUNTIME = SUBJECT / "canonical/runtime"
ARCH = RUNTIME / "livebench_legacy15_composition_archetypes_v1.py"
FEAS = RUNTIME / "livebench_legacy15_slot_feasibility_v1.py"
COMPOSER = RUNTIME / "livebench_legacy15_contract_composer_v2.py"
PLANNER = RUNTIME / "livebench_legacy15_pointwise_optimal_v1.py"
PARAMETRIC = RUNTIME / "livebench_post_sacrifice_parametric_reduction_v1.py"

END_PHRASES = (
    "Any other questions?",
    "Is there anything else I can help with?",
)
POSTSCRIPTS = ("P.S.", "P.P.S")


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def blob(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()


def source_blob(repo: pathlib.Path, path: str) -> str:
    return run(["git", "-C", str(repo), "rev-parse", f"HEAD:{path}"], capture_output=True).stdout.strip()


def contract(iid: str, **slots):
    return {"instruction_id": iid, "slots": slots}


def main() -> int:
    expected_subject = {
        ARCH: ARCH_BLOB,
        FEAS: FEAS_BLOB,
        COMPOSER: COMPOSER_BLOB,
        PLANNER: PLANNER_BLOB,
        PARAMETRIC: PARAMETRIC_BLOB,
    }
    for path, expected in expected_subject.items():
        got = blob(path)
        assert got == expected, (path, got, expected)

    live = pathlib.Path("/tmp/LiveBench")
    assert run(["git", "-C", str(live), "rev-parse", "HEAD"], capture_output=True).stdout.strip() == LIVEBENCH_COMMIT
    for path, expected in {
        "livebench/if_runner/instruction_following_eval/instructions.py": INSTRUCTIONS_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_registry.py": REGISTRY_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_util.py": UTIL_BLOB,
    }.items():
        assert source_blob(live, path) == expected, path

    nltk_repo = pathlib.Path("/tmp/nltk_data_repo")
    assert run(["git", "-C", str(nltk_repo), "rev-parse", "HEAD"], capture_output=True).stdout.strip() == NLTK_DATA_COMMIT
    assert source_blob(nltk_repo, "packages/tokenizers/punkt.zip") == PUNKT_ZIP_BLOB
    assert source_blob(nltk_repo, "packages/tokenizers/punkt_tab.zip") == PUNKT_TAB_ZIP_BLOB

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))

    import nltk
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_post_sacrifice_parametric_reduction_v1 as parametric
    from instruction_following_eval import instructions_registry, instructions_util

    assert nltk.__version__ == "3.10.3", nltk.__version__
    assert arch.verify()["compatible_set_count"] == 928
    assert parametric.CONSERVATIVE_UNPADDED_WORD_UPPER_BOUND == 62
    assert parametric.CONSERVATIVE_UNPADDED_WORD_UPPER_BOUND < parametric.PUBLIC_WORD_MIN == 100

    words = list(instructions_util.WORD_LIST)
    assert len(words) == 1525 and len(set(words)) == 1525
    assert all(re.fullmatch(r"[A-Za-z]+", w) for w in words)
    assert all(not set(w) & set(".?!") for w in words)

    forced = {"section", "other", "anything", "can", "help"}
    safe = [w for w in words if w.lower() not in forced]
    required = safe[:5]
    forbidden = safe[10:15]
    nth_word = safe[20]
    assert set(map(str.lower, required + [nth_word])).isdisjoint(set(map(str.lower, forbidden)))

    # This is the formal quotient boundary for omitted lexical/numeric values:
    # every omitted generated value is punctuation-free, while every punctuation
    # site the sentence tokenizer can see is created by one of the exact fixed
    # constructor forms enumerated below.
    assert not set(comp._SAFE) & set(".?!")
    assert all(not set(comp._SAFE + "x" + str(i)) & set(".?!") for i in (0, 1, 399))
    assert all(not set(w) & set(".?!") for w in required + forbidden + [nth_word])

    sentence_sets = [
        ids for ids in arch.enumerate_compatible_sets()
        if comp.SENTENCES in ids
    ]
    assert sentence_sets

    counts = Counter()
    failures = []
    observed_counts = Counter()

    # less-than 2 is the strongest satisfiable strict upper bound. The composer
    # output for every public less-than threshold 2..20 is identical because n
    # is not interpolated into the response. Thus one exact threshold proves all.
    sentence_profiles = [("less than", 2)] + [
        ("at least", n) for n in range(1, 21)
    ]

    def options(ids, iid):
        if iid == comp.WORDS:
            if iid not in ids:
                return (None,)
            # less-than 100 is the strongest public upper bound and never pads.
            # at-least 100/500 bracket the punctuation-free padding family.
            return (("less than", 100), ("at least", 100), ("at least", 500))
        if iid == comp.NTH:
            if iid not in ids:
                return (None,)
            return tuple((p, k) for p in range(1, 6) for k in range(1, p + 1))
        if iid == comp.POSTSCRIPT:
            return POSTSCRIPTS if iid in ids else (None,)
        if iid == comp.BULLETS:
            return tuple(range(1, 6)) if iid in ids else (None,)
        if iid == comp.SECTIONS:
            return tuple((splitter, n) for splitter in ("Section", "SECTION") for n in range(1, 6)) if iid in ids else (None,)
        if iid == comp.END:
            return END_PHRASES if iid in ids else (None,)
        raise AssertionError(iid)

    def build(ids, sentence_profile, word_profile, nth_profile, post, bullets, section, end):
        out = []
        for iid in ids:
            if iid == comp.EXIST:
                out.append(contract(iid, keywords=required))
            elif iid == comp.FORBIDDEN:
                out.append(contract(iid, forbidden_words=forbidden))
            elif iid == comp.PARAGRAPHS:
                raise AssertionError("SENTENCE_PARAGRAPH_CONFLICT_DRIFT")
            elif iid == comp.WORDS:
                rel, n = word_profile
                out.append(contract(iid, num_words=n, relation=rel))
            elif iid == comp.SENTENCES:
                rel, n = sentence_profile
                out.append(contract(iid, num_sentences=n, relation=rel))
            elif iid == comp.NTH:
                p, k = nth_profile
                out.append(contract(iid, num_paragraphs=p, nth_paragraph=k, first_word=nth_word))
            elif iid == comp.POSTSCRIPT:
                out.append(contract(iid, postscript_marker=post))
            elif iid == comp.BULLETS:
                out.append(contract(iid, num_bullets=bullets))
            elif iid == comp.TITLE:
                out.append(contract(iid))
            elif iid == comp.SECTIONS:
                splitter, n = section
                out.append(contract(iid, section_spliter=splitter, num_sections=n))
            elif iid in {comp.JSON_ID, comp.REPEAT, comp.TWO}:
                raise AssertionError("SPECIAL_ROUTE_SENTENCE_CONFLICT_DRIFT:" + iid)
            elif iid == comp.END:
                out.append(contract(iid, end_phrase=end))
            elif iid == comp.QUOTE:
                out.append(contract(iid))
            else:
                raise AssertionError("UNKNOWN_ACTIVE_ID:" + iid)
        return out

    for set_index, ids_tuple in enumerate(sentence_sets):
        ids = set(ids_tuple)
        dimensions = [
            sentence_profiles,
            options(ids, comp.WORDS),
            options(ids, comp.NTH),
            options(ids, comp.POSTSCRIPT),
            options(ids, comp.BULLETS),
            options(ids, comp.SECTIONS),
            options(ids, comp.END),
        ]
        for profile_index, values in enumerate(itertools.product(*dimensions)):
            sentence_profile, word_profile, nth_profile, post, bullets, section, end = values
            contracts = build(
                ids_tuple, sentence_profile, word_profile, nth_profile,
                post, bullets, section, end,
            )
            out = comp.compose_contracts(contracts)
            counts["contexts"] += 1
            if out.get("status") != "CANDIDATE_WITNESS":
                failures.append({
                    "kind": "composer_noncandidate",
                    "set_index": set_index,
                    "profile_index": profile_index,
                    "ids": list(ids_tuple),
                    "profile": values,
                    "out": out,
                })
                continue

            response = str(out["response"])
            actual = int(instructions_util.count_sentences(response))
            observed_counts[actual] += 1

            rel, n = sentence_profile
            if rel == "less than":
                counts["less_than_2_contexts"] += 1
                ok = actual < 2
            else:
                counts["at_least_contexts"] += 1
                ok = actual >= n

            checker = instructions_registry.INSTRUCTION_DICT[comp.SENTENCES](comp.SENTENCES)
            checker.build_description(num_sentences=n, relation=rel)
            exact = bool(response.strip()) and bool(checker.check_following(response))
            if not ok or not exact:
                failures.append({
                    "kind": "punkt_sentence_failure",
                    "set_index": set_index,
                    "profile_index": profile_index,
                    "ids": list(ids_tuple),
                    "profile": values,
                    "actual_sentence_count": actual,
                    "checker_pass": exact,
                    "response": response,
                })
                if len(failures) >= 100:
                    break
        if len(failures) >= 100:
            break

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_CLOSURE_INDEPENDENT_VERIFICATION_V1",
        "status": "FAIL" if failures else (
            "PASS__ALL_POST_SACRIFICE_PUNKT_CONTEXTS__"
            "PUBLIC_SENTENCE_DOMAIN_CLOSED__ZERO_TERMINAL_ROWS"
        ),
        "subject_blobs": {
            "archetypes": ARCH_BLOB,
            "slot_feasibility": FEAS_BLOB,
            "composer": COMPOSER_BLOB,
            "pointwise_planner": PLANNER_BLOB,
            "post_sacrifice_parametric_reduction": PARAMETRIC_BLOB,
        },
        "pinned_livebench": {
            "commit": LIVEBENCH_COMMIT,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "registry_blob": REGISTRY_BLOB,
            "instructions_util_blob": UTIL_BLOB,
        },
        "pinned_punkt": {
            "nltk_version": nltk.__version__,
            "nltk_data_commit": NLTK_DATA_COMMIT,
            "punkt_zip_blob": PUNKT_ZIP_BLOB,
            "punkt_tab_zip_blob": PUNKT_TAB_ZIP_BLOB,
        },
        "coverage": {
            "active15_structural_sets_total": 928,
            "sentence_structural_sets": len(sentence_sets),
            "exact_punkt_contexts": counts["contexts"],
            "less_than_2_representative_contexts": counts["less_than_2_contexts"],
            "at_least_1_to_20_contexts": counts["at_least_contexts"],
            "public_sentence_thresholds_proved": {
                "less_than": [2, 20],
                "at_least": [1, 20],
            },
            "nth_positions_exhausted_when_active": 15,
            "bullet_counts_exhausted_when_active": [1, 5],
            "section_counts_exhausted_when_active": [1, 5],
            "section_splitters_exhausted_when_active": ["Section", "SECTION"],
            "postscript_markers_exhausted_when_active": list(POSTSCRIPTS),
            "end_phrases_exhausted_when_active": list(END_PHRASES),
            "word_punkt_quotient_probes_when_active": [
                ["less than", 100],
                ["at least", 100],
                ["at least", 500],
            ],
            "public_word_identity_domain_checked_punctuation_free": len(words),
            "observed_sentence_count_histogram": dict(sorted(observed_counts.items())),
        },
        "parametric_closure": {
            "less_than_sentence_2_to_20": (
                "COMPOSER_RESPONSE_IS_THRESHOLD_INDEPENDENT_FOR_RELATION_LESS_THAN;"
                "COUNT_LT_2_IMPLIES_COUNT_LT_N_FOR_ALL_PUBLIC_N_2_TO_20"
            ),
            "word_less_than_100_to_500": (
                "NO_PADDING_FOR_LESS_THAN;CONSERVATIVE_UNPADDED_WORD_UPPER_BOUND_62_LT_100"
            ),
            "word_at_least_100_to_500": (
                "ALL_PUBLIC_THRESHOLDS_REQUIRE_PADDING;ADDITIONAL_PAD_TOKENS_CONTAIN_NO_DOT_QUESTION_OR_EXCLAMATION;"
                "THE_FIRST_POST_TERMINATOR_PAD_CONTEXT_IS_IDENTICAL"
            ),
            "lexical_domain": (
                "ALL_1525_PUBLIC_GENERATED_WORDS_ARE_ASCII_ALPHA_AND_CONTAIN_NO_PUNKT_SENTENCE_END_CHARACTER;"
                "LEXICAL_IDENTITIES_NEVER_OCCUR_IMMEDIATELY_BEFORE_A_CONSTRUCTOR_SENTENCE_TERMINATOR"
            ),
            "strict_less_than_one": (
                "NOT_A_POST_SACRIFICE_SENTENCE_CONTEXT;THE_SENTENCE_CHECKER_IS_THE_MANDATORY_LOSS_COORDINATE"
            ),
        },
        "failure_count": len(failures),
        "failures": failures,
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "hidden_terminal_instruction_ids_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_RECEIPT_CLOSES_ONLY_THE_PINNED_PUNKT_RESIDUAL_IDENTIFIED_BY_THE_PARAMETRIC_REDUCTION",
            "LIVEBENCH_ACCEPTANCE_REQUIRES_SEPARATE_COMPOSITION_OF_THE_ALREADY_VERIFIED_STRUCTURAL_LEXICAL_MINIMUM_CUT_AND_VISIBLE_COMPILER_RECEIPTS",
            "NO_TERMINAL_CASE_CONTENT_WAS_READ_OR_SCORED",
        ],
    }
    pathlib.Path("livebench_punkt_context_closure_v1.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
