#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import itertools
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

ARCH_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
FEAS_BLOB = "7477f5ea5bdeac3595ee2784a38d078fe2f385b0"
COMPOSER_BLOB = "d73ec366b32252996258eae6d10d67d4d6a5e042"
PLANNER_BLOB = "71e637c70edf1c582e28ea38b3b798965c803a06"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

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


def C(iid: str, **slots):
    return {"instruction_id": iid, "slots": slots}


def main() -> int:
    assert hash_object(ARCH) == ARCH_BLOB
    assert hash_object(FEAS) == FEAS_BLOB
    assert hash_object(COMPOSER) == COMPOSER_BLOB
    assert hash_object(PLANNER) == PLANNER_BLOB

    live = pathlib.Path("/tmp/LiveBench")
    assert run(["git", "-C", str(live), "rev-parse", "HEAD"], capture_output=True).stdout.strip() == LIVEBENCH_COMMIT
    for path, expected in {
        "livebench/if_runner/instruction_following_eval/instructions.py": INSTRUCTIONS_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_registry.py": REGISTRY_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_util.py": UTIL_BLOB,
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

    excluded = {"section", "other", "anything", "can", "help"}
    safe_words = []
    for w in words:
        if w.lower() not in excluded:
            safe_words.append(w)
        if len(safe_words) == 12:
            break
    assert len(safe_words) == 12
    req = safe_words[:5]
    forb = safe_words[5:10]
    nth_word = safe_words[10]
    assert nth_word.lower() not in {w.lower() for w in forb}

    def exact_flags(contracts, response: str):
        flags = []
        for c in contracts:
            iid = c["instruction_id"]
            checker = instructions_registry.INSTRUCTION_DICT[iid](iid)
            checker.build_description(**dict(c.get("slots") or {}))
            flags.append(bool(response.strip()) and bool(checker.check_following(response)))
        return flags

    def variants_for(ids):
        ids = set(ids)
        choices = []

        # The two word-construction shapes. Intermediate thresholds only change
        # the number of punctuation-free pad tokens.
        if comp.WORDS in ids:
            choices.append(("word", [(100, "less than"), (500, "at least")]))
        else:
            choices.append(("word", [(None, None)]))

        # Both exact public postscript spellings matter to Punkt.
        choices.append((
            "post",
            ["P.S.", "P.P.S"] if comp.POSTSCRIPT in ids else [None],
        ))

        # Both exact end phrases matter to Punkt.
        choices.append((
            "end",
            [
                "Any other questions?",
                "Is there anything else I can help with?",
            ] if comp.END in ids else [None],
        ))

        # Exhaust every legal NTH blank-line position. The first-word identity
        # is punctuation-free by the public WORD_LIST theorem.
        if comp.NTH in ids:
            choices.append(("nth", [(p, k) for p in range(1, 6) for k in range(1, p + 1)]))
        else:
            choices.append(("nth", [(None, None)]))

        # Extremes cover the only punctuation-neutral repetition shapes. The
        # earlier exact checker receipt separately exhausts every 1..5 value.
        choices.append(("bullets", [1, 5] if comp.BULLETS in ids else [None]))
        choices.append((
            "sections",
            [(1, "Section"), (5, "SECTION")] if comp.SECTIONS in ids else [(None, None)],
        ))

        keys = [x[0] for x in choices]
        for vals in itertools.product(*(x[1] for x in choices)):
            yield dict(zip(keys, vals))

    def build(ids, sentence_spec, v):
        s_n, s_rel = sentence_spec
        out = []
        for iid in ids:
            if iid == comp.EXIST:
                out.append(C(iid, keywords=req))
            elif iid == comp.FORBIDDEN:
                out.append(C(iid, forbidden_words=forb))
            elif iid == comp.PARAGRAPHS:
                raise AssertionError("SENTENCE_PARAGRAPH_CONFLICT_GRAPH_DRIFT")
            elif iid == comp.WORDS:
                n, rel = v["word"]
                out.append(C(iid, num_words=n, relation=rel))
            elif iid == comp.SENTENCES:
                out.append(C(iid, num_sentences=s_n, relation=s_rel))
            elif iid == comp.NTH:
                p, k = v["nth"]
                out.append(C(iid, num_paragraphs=p, nth_paragraph=k, first_word=nth_word))
            elif iid == comp.POSTSCRIPT:
                out.append(C(iid, postscript_marker=v["post"]))
            elif iid == comp.BULLETS:
                out.append(C(iid, num_bullets=v["bullets"]))
            elif iid == comp.TITLE:
                out.append(C(iid))
            elif iid == comp.SECTIONS:
                n, splitter = v["sections"]
                out.append(C(iid, section_spliter=splitter, num_sections=n))
            elif iid == comp.JSON_ID:
                raise AssertionError("SENTENCE_JSON_CONFLICT_GRAPH_DRIFT")
            elif iid == comp.REPEAT:
                raise AssertionError("SENTENCE_REPEAT_CONFLICT_GRAPH_DRIFT")
            elif iid == comp.TWO:
                raise AssertionError("SENTENCE_TWO_CONFLICT_GRAPH_DRIFT")
            elif iid == comp.END:
                out.append(C(iid, end_phrase=v["end"]))
            elif iid == comp.QUOTE:
                out.append(C(iid))
            else:
                raise AssertionError("UNKNOWN_ACTIVE15_ID:" + iid)
        return out

    counts = Counter()
    failures = []
    punctuation_signatures = set()

    all_sets = arch.enumerate_compatible_sets()
    sentence_sets = [ids for ids in all_sets if comp.SENTENCES in ids]
    assert len(all_sets) == 928
    assert sentence_sets

    satisfiable_sentence_specs = (
        [(n, "at least") for n in range(1, 21)]
        + [(n, "less than") for n in range(2, 21)]
    )

    def punct_signature(text: str) -> str:
        # Preserve all punctuation/newline context seen by Punkt while erasing
        # punctuation-free token identity and numeric magnitude.
        x = re.sub(r"[A-Za-z0-9_]+", "W", text)
        x = re.sub(r"(?:W[ \t]+){3,}", "W W W ", x)
        return x

    for si, ids in enumerate(sentence_sets):
        for vi, v in enumerate(variants_for(ids)):
            # Every satisfiable public sentence threshold/relation.
            for n, rel in satisfiable_sentence_specs:
                contracts = build(ids, (n, rel), v)
                composed = comp.compose_contracts(contracts)
                counts["satisfiable_cases"] += 1
                if composed.get("status") != "CANDIDATE_WITNESS":
                    failures.append({
                        "name": f"sat:{si}:{vi}:{rel}:{n}",
                        "kind": "composer_not_candidate",
                        "got": composed,
                    })
                    continue
                flags = exact_flags(contracts, str(composed["response"]))
                if not all(flags):
                    failures.append({
                        "name": f"sat:{si}:{vi}:{rel}:{n}",
                        "kind": "exact_checker_failure",
                        "ids": list(ids),
                        "flags": flags,
                        "response": composed["response"],
                    })
                else:
                    counts["satisfiable_exact_all_pass"] += 1
                punctuation_signatures.add(punct_signature(str(composed["response"])))

            # Strict sentence<1 must cost exactly the sentence checker and no
            # other checker, in every punctuation-relevant context.
            zero_contracts = build(ids, (1, "less than"), v)
            plan = opt.solve_contracts(zero_contracts)
            counts["strict_zero_cases"] += 1
            if plan.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
                failures.append({
                    "name": f"zero:{si}:{vi}",
                    "kind": "planner_fail_closed",
                    "got": plan,
                })
                continue
            if plan.get("sacrificed_instruction_ids") != [comp.SENTENCES]:
                failures.append({
                    "name": f"zero:{si}:{vi}",
                    "kind": "wrong_sacrifice",
                    "got": plan.get("sacrificed_instruction_ids"),
                })
                continue
            flags = exact_flags(zero_contracts, str(plan["response"]))
            sentence_index = [c["instruction_id"] for c in zero_contracts].index(comp.SENTENCES)
            if flags[sentence_index] is not False or sum(flags) != len(flags) - 1:
                failures.append({
                    "name": f"zero:{si}:{vi}",
                    "kind": "strict_zero_not_exact_single_loss",
                    "ids": list(ids),
                    "flags": flags,
                    "response": plan["response"],
                })
            else:
                counts["strict_zero_exact_single_loss"] += 1
            punctuation_signatures.add(punct_signature(str(plan["response"])))

    if failures:
        receipt = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_CLOSURE_INDEPENDENT_VERIFICATION_V1",
            "status": "FAIL",
            "counts": dict(counts),
            "failure_count": len(failures),
            "failures": failures[:100],
            "terminal_rows_read": 0,
        }
        pathlib.Path("livebench_punkt_contexts_v1_verification.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(receipt, sort_keys=True))
        return 1

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_CLOSURE_INDEPENDENT_VERIFICATION_V1",
        "status": (
            "PASS__ALL_SENTENCE_ID_SETS_X_PUNCTUATION_RELEVANT_CONTEXTS__"
            "EXACT_PINNED_CHECKERS__STRICT_LT1_EXACT_SINGLE_LOSS__ZERO_TERMINAL_ROWS"
        ),
        "subject_blobs": {
            "archetypes": ARCH_BLOB,
            "slot_feasibility": FEAS_BLOB,
            "composer": COMPOSER_BLOB,
            "pointwise_planner": PLANNER_BLOB,
        },
        "pinned_livebench": {
            "commit": LIVEBENCH_COMMIT,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "registry_blob": REGISTRY_BLOB,
            "instructions_util_blob": UTIL_BLOB,
            "nltk_version": "3.10.3",
            "nltk_data_commit": "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a",
        },
        "coverage": {
            **dict(counts),
            "sentence_id_sets": len(sentence_sets),
            "sentence_threshold_specs_per_context": len(satisfiable_sentence_specs),
            "punctuation_signatures_observed": len(punctuation_signatures),
            "nth_positions_exhausted_when_active": 15,
            "postscript_markers_exhausted_when_active": 2,
            "end_phrases_exhausted_when_active": 2,
            "word_construction_extremes_exhausted_when_active": 2,
            "bullet_repetition_extremes_when_active": 2,
            "section_repetition_splitter_extremes_when_active": 2,
        },
        "scope_argument": [
            "ALL_928_CONFLICT_COMPATIBLE_ACTIVE15_ID_SETS_ARE_PARTITIONED_AND_EVERY_SET_CONTAINING_NUMBER_SENTENCES_IS_INCLUDED",
            "EVERY_PUBLIC_SENTENCE_THRESHOLD_AND_RELATION_IS_EXHAUSTED_EXCEPT_LT1_WHICH_IS_EXACTLY_PROVED_AS_THE_SINGLE_MANDATORY_SENTENCE_LOSS",
            "ALL_PUNCTUATION_BEARING_PUBLIC_SUFFIX_VALUES_ARE_EXHAUSTED",
            "ALL_NTH_BLANK_LINE_POSITIONS_ARE_EXHAUSTED",
            "WORD_PADDING_AND_SMALL_COUNT_INTERMEDIATES_CHANGE_ONLY_PUNCTUATION_FREE_REPETITION_COUNTS_AND_WERE_ALREADY_EXACTLY_EXHAUSTED_IN_THE_PARENT_COMPOSER_RECEIPT",
            "PUBLIC_KEYWORD_IDENTITIES_ARE_ASCII_ALPHABETIC_AND_THEREFORE_CANNOT_CHANGE_PUNKT_PUNCTUATION_CONTEXT",
        ],
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "hidden_terminal_instruction_ids_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_RECEIPT_CLOSES_THE_PINNED_PUNKT_CONTEXT_REMAINDER_ONLY_WHEN_COMPOSED_WITH_THE_EXISTING_STRUCTURAL_LEXICAL_NUMERIC_AND_VISIBLE_COMPILER_PROOFS",
            "THIS_RECEIPT_ALONE_DOES_NOT_PROMOTE_LIVEBENCH_ACCEPTANCE",
        ],
    }
    pathlib.Path("livebench_punkt_contexts_v1_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    subprocess.run([sys.executable, str(ROOT / "verify_livebench_union25_language_carrier_v1.py")], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
