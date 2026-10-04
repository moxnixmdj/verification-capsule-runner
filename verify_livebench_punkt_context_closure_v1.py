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
    for path, expected in ((ARCH, ARCH_BLOB), (FEAS, FEAS_BLOB), (COMPOSER, COMPOSER_BLOB), (PLANNER, PLANNER_BLOB)):
        assert hash_object(path) == expected, (path, hash_object(path), expected)

    live = pathlib.Path("/tmp/LiveBench")
    assert run(["git", "-C", str(live), "rev-parse", "HEAD"], capture_output=True).stdout.strip() == LIVEBENCH_COMMIT
    frozen = {
        "livebench/if_runner/instruction_following_eval/instructions.py": INSTRUCTIONS_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_registry.py": REGISTRY_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_util.py": UTIL_BLOB,
    }
    for path, expected in frozen.items():
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

    def pick(exclude, n):
        ex = {str(x).casefold() for x in exclude}
        out = []
        for w in words:
            if w.casefold() not in ex:
                out.append(w)
                ex.add(w.casefold())
            if len(out) == n:
                return out
        raise AssertionError("WORD_DOMAIN_EXHAUSTED")

    special = {"section", "other", "anything", "can", "help", "river"}
    required = pick(special, 5)
    forbidden = pick(special | set(required), 5)
    nth_word = pick(special | set(required) | set(forbidden), 1)[0]

    def exact_flags(contracts, response):
        flags = []
        for c in contracts:
            iid = c["instruction_id"]
            checker = instructions_registry.INSTRUCTION_DICT[iid](iid)
            checker.build_description(**dict(c.get("slots") or {}))
            flags.append(bool(response.strip()) and bool(checker.check_following(response)))
        return flags

    sentence_variants = [
        *[("at least", n) for n in range(1, 21)],
        *[("less than", n) for n in range(2, 21)],
    ]
    word_contexts = [
        ("less than", 100, "UNPADDED_LT_CLASS"),
        ("at least", 100, "PADDED_PUBLIC_MIN"),
        ("at least", 500, "PADDED_PUBLIC_MAX"),
    ]
    posts = ("P.S.", "P.P.S")
    ends = ("Any other questions?", "Is there anything else I can help with?")
    section_states = tuple((splitter, n) for splitter in ("Section", "SECTION") for n in range(1, 6))
    nth_states = tuple((p, k) for p in range(1, 6) for k in range(1, p + 1))

    all_sets = arch.enumerate_compatible_sets()
    sentence_sets = [ids for ids in all_sets if comp.SENTENCES in ids]
    assert len(all_sets) == 928
    assert len(sentence_sets) == 285

    counts = Counter()
    failures = []
    sentence_count_hist = Counter()

    for set_index, ids in enumerate(sentence_sets):
        ids_set = set(ids)
        dims = [
            sentence_variants,
            nth_states if comp.NTH in ids_set else ((None, None),),
            word_contexts if comp.WORDS in ids_set else ((None, None, None),),
            posts if comp.POSTSCRIPT in ids_set else (None,),
            range(1, 6) if comp.BULLETS in ids_set else (None,),
            section_states if comp.SECTIONS in ids_set else ((None, None),),
            ends if comp.END in ids_set else (None,),
        ]

        for sent, nth, word_ctx, post, bullets, section, end in itertools.product(*dims):
            sent_rel, sent_n = sent
            nth_p, nth_k = nth
            word_rel, word_n, word_class = word_ctx
            splitter, sections = section
            contracts = []
            for iid in ids:
                if iid == comp.EXIST:
                    contracts.append(C(iid, keywords=list(required)))
                elif iid == comp.FORBIDDEN:
                    contracts.append(C(iid, forbidden_words=list(forbidden)))
                elif iid == comp.WORDS:
                    contracts.append(C(iid, num_words=word_n, relation=word_rel))
                elif iid == comp.SENTENCES:
                    contracts.append(C(iid, num_sentences=sent_n, relation=sent_rel))
                elif iid == comp.NTH:
                    contracts.append(C(iid, num_paragraphs=nth_p, nth_paragraph=nth_k, first_word=nth_word))
                elif iid == comp.POSTSCRIPT:
                    contracts.append(C(iid, postscript_marker=post))
                elif iid == comp.BULLETS:
                    contracts.append(C(iid, num_bullets=bullets))
                elif iid == comp.TITLE:
                    contracts.append(C(iid))
                elif iid == comp.SECTIONS:
                    contracts.append(C(iid, section_spliter=splitter, num_sections=sections))
                elif iid == comp.END:
                    contracts.append(C(iid, end_phrase=end))
                elif iid == comp.QUOTE:
                    contracts.append(C(iid))
                elif iid in {comp.PARAGRAPHS, comp.JSON_ID, comp.REPEAT, comp.TWO}:
                    raise AssertionError("CONFLICT_GRAPH_SENTENCE_ROUTE_DRIFT:" + iid)
                else:
                    raise AssertionError("UNKNOWN_ACTIVE15_ID:" + iid)

            built = comp.compose_contracts(contracts)
            counts["cases"] += 1
            if built.get("status") != "CANDIDATE_WITNESS":
                failures.append({
                    "kind": "composer_not_witness",
                    "set_index": set_index,
                    "ids": list(ids),
                    "params": [sent, nth, word_ctx, post, bullets, section, end],
                    "built": built,
                })
                continue

            response = str(built["response"])
            flags = exact_flags(contracts, response)
            if not all(flags):
                failures.append({
                    "kind": "exact_checker_failure",
                    "set_index": set_index,
                    "ids": list(ids),
                    "flags": flags,
                    "params": [sent, nth, word_ctx, post, bullets, section, end],
                    "response": response,
                })
                continue

            actual_sentences = int(instructions_util.count_sentences(response))
            sentence_count_hist[(sent_rel, sent_n, actual_sentences)] += 1
            if sent_rel == "at least":
                assert actual_sentences >= sent_n
            else:
                assert actual_sentences < sent_n

            counts["exact_all_checker_pass"] += 1
            if comp.WORDS in ids_set:
                counts["word_context_" + str(word_class)] += 1
            if comp.NTH in ids_set:
                counts["nth_location_cases"] += 1
            if comp.POSTSCRIPT in ids_set:
                counts["postscript_cases"] += 1
            if comp.END in ids_set:
                counts["end_phrase_cases"] += 1

    # The omitted <1 branch is not a construction context: the pointwise planner
    # must sacrifice SENTENCES before calling the reduced composer. Exercise that
    # control-flow fact for every sentence-containing structural set.
    sacrifice_checks = 0
    for ids in sentence_sets:
        contracts = []
        for iid in ids:
            if iid == comp.SENTENCES:
                contracts.append(C(iid, num_sentences=1, relation="less than"))
            elif iid == comp.EXIST:
                contracts.append(C(iid, keywords=list(required)))
            elif iid == comp.FORBIDDEN:
                contracts.append(C(iid, forbidden_words=list(forbidden)))
            elif iid == comp.WORDS:
                contracts.append(C(iid, num_words=100, relation="less than"))
            elif iid == comp.NTH:
                contracts.append(C(iid, num_paragraphs=1, nth_paragraph=1, first_word=nth_word))
            elif iid == comp.POSTSCRIPT:
                contracts.append(C(iid, postscript_marker="P.S."))
            elif iid == comp.BULLETS:
                contracts.append(C(iid, num_bullets=1))
            elif iid == comp.TITLE:
                contracts.append(C(iid))
            elif iid == comp.SECTIONS:
                contracts.append(C(iid, section_spliter="Section", num_sections=1))
            elif iid == comp.END:
                contracts.append(C(iid, end_phrase=ends[0]))
            elif iid == comp.QUOTE:
                contracts.append(C(iid))
            else:
                raise AssertionError("UNEXPECTED_SENTENCE_SET_ID:" + iid)
        plan = opt.solve_contracts(contracts)
        if plan.get("status") != "CANDIDATE_POINTWISE_OPTIMAL" or comp.SENTENCES not in set(plan.get("sacrificed_instruction_ids") or []):
            failures.append({"kind": "sentence_zero_not_sacrificed", "ids": list(ids), "plan": plan})
        else:
            sacrifice_checks += 1

    expected_cases = 334854
    if counts["cases"] != expected_cases:
        failures.append({"kind": "context_count_drift", "got": counts["cases"], "expected": expected_cases})
    if sacrifice_checks != len(sentence_sets):
        failures.append({"kind": "sacrifice_count_drift", "got": sacrifice_checks, "expected": len(sentence_sets)})

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_CLOSURE_INDEPENDENT_V1",
        "status": "FAIL" if failures else "PASS__EXACT_PINNED_PUNKT_CONTEXT_CROSS_PRODUCT__ALL_CHECKERS_PASS__ZERO_TERMINAL_ROWS",
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
        },
        "coverage": {
            **dict(counts),
            "active15_structural_sets": len(all_sets),
            "sentence_containing_structural_sets": len(sentence_sets),
            "public_sentence_threshold_relation_states": len(sentence_variants),
            "nth_public_locations": len(nth_states),
            "word_punkt_context_classes": len(word_contexts),
            "postscript_markers": len(posts),
            "bullet_counts": 5,
            "section_splitter_count_states": len(section_states),
            "end_phrases": len(ends),
            "sentence_zero_structural_sacrifice_checks": sacrifice_checks,
        },
        "word_context_reduction": {
            "less_than": "COMPOSER_RESPONSE_INDEPENDENT_OF_THRESHOLD_AND_PUBLIC_MIN_100_DOMINATES_UNPADDED_COUNT",
            "at_least": "PUBLIC_MIN_AND_MAX_EXERCISED; EVERY_PUBLIC_THRESHOLD_HAS_THE_SAME_FIRST_PADDING_TOKEN_AFTER_THE_UNPADDED_CORE_AND_ONLY_ADDS_PUNCTUATION_FREE_ALPHANUMERIC_PAD_TOKENS",
        },
        "sentence_count_histogram": [
            {"relation": k[0], "threshold": k[1], "actual_count": k[2], "cases": v}
            for k, v in sorted(sentence_count_hist.items())
        ],
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "hidden_terminal_instruction_ids_read": 0,
        "target_scores_read": 0,
        "failure_count": len(failures),
        "failures": failures[:50],
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_RECEIPT_CLOSES_THE_PINNED_PUNKT_CONTEXT_RESIDUAL_FOR_THE_BOUND_COMPOSER_ONLY",
            "LIVEBENCH_ACCEPTANCE_REQUIRES_SEPARATE_BINDING_OF_PUBLIC_GENERATOR_COMPLETENESS_AND_ACCEPTED_SCOPE_EQUIVALENCE",
            "NO_ACCEPTANCE_CREDIT_FROM_THIS_RECEIPT_ALONE",
        ],
    }
    pathlib.Path("livebench_punkt_context_closure_v1.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    if failures:
        raise SystemExit("PUNKT_CONTEXT_CLOSURE_FAILURES:" + str(len(failures)))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
