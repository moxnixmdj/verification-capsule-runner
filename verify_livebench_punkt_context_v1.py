#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
from itertools import product

ARCH_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
FEAS_BLOB = "7477f5ea5bdeac3595ee2784a38d078fe2f385b0"
COMPOSER_BLOB = "d73ec366b32252996258eae6d10d67d4d6a5e042"
PLANNER_BLOB = "71e637c70edf1c582e28ea38b3b798965c803a06"
LEX_BLOB = "5803c31e3972c6d40415f319e808c48420bc0388"
REDUCTION_BLOB = "a9ab9064b447ed669d2404a7a65f6c429c51ae85"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
NLTK_DATA_COMMIT = "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"
EXPECTED_SENTENCE_ID_SETS = 285
EXPECTED_CONTEXTS = 394992

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_composer_v2_20261005"
RUNTIME = SUBJECT / "canonical/runtime"
PATHS = {
    "archetypes": (RUNTIME / "livebench_legacy15_composition_archetypes_v1.py", ARCH_BLOB),
    "feasibility": (RUNTIME / "livebench_legacy15_slot_feasibility_v1.py", FEAS_BLOB),
    "composer": (RUNTIME / "livebench_legacy15_contract_composer_v2.py", COMPOSER_BLOB),
    "planner": (RUNTIME / "livebench_legacy15_pointwise_optimal_v1.py", PLANNER_BLOB),
    "lexical_quotient": (RUNTIME / "livebench_legacy15_lexical_slot_quotient_v1.py", LEX_BLOB),
    "parametric_reduction": (RUNTIME / "livebench_post_sacrifice_parametric_reduction_v1.py", REDUCTION_BLOB),
}


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def hash_object(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()


def contract(iid: str, **slots):
    return {"instruction_id": iid, "slots": slots}


def main() -> int:
    subject_hashes = {}
    for name, (path, expected) in PATHS.items():
        got = hash_object(path)
        assert got == expected, (name, got, expected)
        subject_hashes[name] = got

    live = pathlib.Path("/tmp/LiveBench")
    live_head = run(["git", "-C", str(live), "rev-parse", "HEAD"], capture_output=True).stdout.strip()
    assert live_head == LIVEBENCH_COMMIT, (live_head, LIVEBENCH_COMMIT)
    for path, expected in {
        "livebench/if_runner/instruction_following_eval/instructions.py": INSTRUCTIONS_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_registry.py": REGISTRY_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_util.py": UTIL_BLOB,
    }.items():
        got = run(["git", "-C", str(live), "rev-parse", f"HEAD:{path}"], capture_output=True).stdout.strip()
        assert got == expected, (path, got, expected)

    nltk_repo = pathlib.Path("/tmp/nltk_data_repo")
    nltk_head = run(["git", "-C", str(nltk_repo), "rev-parse", "HEAD"], capture_output=True).stdout.strip()
    assert nltk_head == NLTK_DATA_COMMIT, (nltk_head, NLTK_DATA_COMMIT)

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))

    import nltk
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_lexical_slot_quotient_v1 as lex
    from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as opt
    from canonical.runtime import livebench_post_sacrifice_parametric_reduction_v1 as reduction
    from instruction_following_eval import instructions_registry, instructions_util

    red = reduction.verify()
    assert red["status"] == (
        "PASS__NON_SENTENCE_POST_SACRIFICE_CONSTRUCTION_REDUCED_"
        "PARAMETRICALLY__ONLY_PINNED_PUNKT_CONTEXT_REMAINS"
    )
    assert red["sentence_context_id_sets"] == EXPECTED_SENTENCE_ID_SETS
    lex_out = lex.verify()
    assert lex_out["exact_reachable_signature_count"] == 192

    words = list(instructions_util.WORD_LIST)
    assert len(words) == 1525 and len(set(words)) == 1525
    assert all(re.fullmatch(r"[A-Za-z]+", w) for w in words)

    forced_literals = set(
        re.findall(
            r"[A-Za-z]+",
            "Section SECTION P S Any other questions Is there anything else I can help with",
        )
    )
    forced_literals = {x.casefold() for x in forced_literals}

    def fillers(exclude=(), n=5):
        ex = {str(x).casefold() for x in exclude} | forced_literals
        out = []
        for w in words:
            if w.casefold() not in ex:
                out.append(w)
                ex.add(w.casefold())
            if len(out) == n:
                return out
        raise AssertionError("NOT_ENOUGH_FILLERS")

    nth_word = fillers((), 1)[0]
    required = fillers({nth_word}, 5)
    forbidden = fillers(set(required) | {nth_word}, 5)

    def values(iid: str):
        if iid == comp.EXIST:
            return [contract(iid, keywords=required)]
        if iid == comp.FORBIDDEN:
            return [contract(iid, forbidden_words=forbidden)]
        if iid == comp.WORDS:
            # Exact Punkt quotient: less-than emits no padding for all public N
            # because the bound is <100. At-least always emits the same
            # punctuation-free alphanumeric pad-token class; endpoints exercise
            # the minimum and maximum pad lengths.
            return [
                contract(iid, num_words=100, relation="less than"),
                contract(iid, num_words=500, relation="less than"),
                contract(iid, num_words=100, relation="at least"),
                contract(iid, num_words=500, relation="at least"),
            ]
        if iid == comp.SENTENCES:
            return (
                [contract(iid, num_sentences=n, relation="at least") for n in range(1, 21)]
                + [contract(iid, num_sentences=n, relation="less than") for n in range(1, 21)]
            )
        if iid == comp.NTH:
            return [
                contract(iid, num_paragraphs=n, nth_paragraph=k, first_word=nth_word)
                for n in range(1, 6)
                for k in range(1, n + 1)
            ]
        if iid == comp.POSTSCRIPT:
            return [
                contract(iid, postscript_marker="P.S."),
                contract(iid, postscript_marker="P.P.S"),
            ]
        if iid == comp.BULLETS:
            return [contract(iid, num_bullets=n) for n in range(1, 6)]
        if iid == comp.TITLE:
            return [contract(iid)]
        if iid == comp.SECTIONS:
            return [
                contract(iid, section_spliter=s, num_sections=n)
                for s in ("Section", "SECTION")
                for n in range(1, 6)
            ]
        if iid == comp.END:
            return [
                contract(iid, end_phrase="Any other questions?"),
                contract(iid, end_phrase="Is there anything else I can help with?"),
            ]
        if iid == comp.QUOTE:
            return [contract(iid)]
        raise AssertionError("UNEXPECTED_SENTENCE_CONTEXT_ID:" + iid)

    sentence_sets = [
        ids for ids in arch.enumerate_compatible_sets()
        if comp.SENTENCES in ids
    ]
    assert len(sentence_sets) == EXPECTED_SENTENCE_ID_SETS
    for ids in sentence_sets:
        assert comp.PARAGRAPHS not in ids
        assert comp.JSON_ID not in ids
        assert comp.REPEAT not in ids
        assert comp.TWO not in ids

    contexts = 0
    strict_lt1_contexts = 0
    satisfiable_contexts = 0
    sentence_checker_passes = 0
    sentence_checker_expected_failures = 0
    count_min = None
    count_max = None
    failures = []

    def exact_sentence_pass(sentence_contract, response: str) -> bool:
        checker = instructions_registry.INSTRUCTION_DICT[comp.SENTENCES](comp.SENTENCES)
        checker.build_description(**dict(sentence_contract["slots"]))
        return bool(response.strip()) and bool(checker.check_following(response))

    for ids in sentence_sets:
        pools = [values(iid) for iid in ids]
        for choices in product(*pools):
            contracts = list(choices)
            contexts += 1
            s = next(c for c in contracts if c["instruction_id"] == comp.SENTENCES)
            relation = str(s["slots"]["relation"])
            threshold = int(s["slots"]["num_sentences"])

            plan = opt.solve_contracts(contracts)
            if plan.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
                failures.append({
                    "kind": "PLANNER_FAIL_CLOSED",
                    "ids": list(ids),
                    "sentence": s["slots"],
                    "plan": plan,
                })
                break

            response = str(plan["response"])
            sacrificed = set(plan.get("sacrificed_instruction_ids") or [])
            punkt_count = len(nltk.sent_tokenize(response))
            passed = exact_sentence_pass(s, response)
            count_min = punkt_count if count_min is None else min(count_min, punkt_count)
            count_max = punkt_count if count_max is None else max(count_max, punkt_count)

            is_lt1 = relation == "less than" and threshold == 1
            if is_lt1:
                strict_lt1_contexts += 1
                ok = comp.SENTENCES in sacrificed and (not passed) and punkt_count >= 1
                if passed:
                    sentence_checker_passes += 1
                else:
                    sentence_checker_expected_failures += 1
            else:
                satisfiable_contexts += 1
                if passed:
                    sentence_checker_passes += 1
                ok = comp.SENTENCES not in sacrificed and passed
                if relation == "at least":
                    ok = ok and punkt_count >= threshold
                elif relation == "less than":
                    ok = ok and punkt_count < threshold
                else:
                    ok = False

            if not ok:
                failures.append({
                    "kind": "PUNKT_CONTEXT_MISMATCH",
                    "ids": list(ids),
                    "sentence": s["slots"],
                    "sacrificed": sorted(sacrificed),
                    "punkt_count": punkt_count,
                    "checker_pass": passed,
                    "response": response[:1000],
                })
                break
        if failures:
            break

    assert contexts == EXPECTED_CONTEXTS, (contexts, EXPECTED_CONTEXTS)
    assert not failures, failures[:1]
    assert strict_lt1_contexts > 0
    assert satisfiable_contexts + strict_lt1_contexts == contexts
    assert sentence_checker_expected_failures == strict_lt1_contexts
    assert sentence_checker_passes == satisfiable_contexts

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_INDEPENDENT_VERIFICATION_V1",
        "status": (
            "PASS__EXACT_PINNED_PUNKT_CONTEXT_QUOTIENT_EXHAUSTED__"
            "POST_SACRIFICE_SENTENCE_CONSTRUCTION_CLOSED__ZERO_TERMINAL_ROWS__ZERO_CREDIT"
        ),
        "subject_blobs": subject_hashes,
        "livebench_commit": LIVEBENCH_COMMIT,
        "livebench_blobs": {
            "instructions": INSTRUCTIONS_BLOB,
            "registry": REGISTRY_BLOB,
            "instructions_util": UTIL_BLOB,
        },
        "nltk": {
            "version": nltk.__version__,
            "data_commit": NLTK_DATA_COMMIT,
        },
        "coverage": {
            "compatible_active15_sets": 928,
            "sentence_bearing_id_sets": len(sentence_sets),
            "lexical_signatures_bound_by_exact_quotient": 192,
            "punkt_contexts_executed": contexts,
            "sentence_threshold_values_exhausted": 20,
            "sentence_relations_exhausted": ["at least", "less than"],
            "nth_positions_exhausted": 15,
            "postscript_markers_exhausted": ["P.S.", "P.P.S"],
            "bullet_counts_exhausted": [1, 2, 3, 4, 5],
            "section_splitter_count_pairs_exhausted": 10,
            "end_phrases_exhausted": 2,
            "word_punkt_equivalence_profiles": 4,
            "strict_less_than_one_contexts": strict_lt1_contexts,
            "satisfiable_sentence_contexts": satisfiable_contexts,
            "sentence_checker_passes": sentence_checker_passes,
            "expected_sentence_checker_failures": sentence_checker_expected_failures,
            "observed_punkt_sentence_count_min": count_min,
            "observed_punkt_sentence_count_max": count_max,
        },
        "deduction": {
            "non_sentence_post_sacrifice_construction": "BOUND_PARAMETRIC_PROOF",
            "pinned_punkt_context_remainder": "CLOSED_BY_INDEPENDENT_EXHAUSTIVE_QUOTIENT",
            "universal_post_sacrifice_construction_obligation": "SATISFIED_FOR_FROZEN_ACTIVE15_PUBLIC_GENERATOR_SCOPE",
            "terminal_frequency_required": False,
            "terminal_rows_read": 0,
            "hidden_terminal_kwargs_read": 0,
            "hidden_terminal_instruction_ids_read": 0,
            "target_scores_read": 0,
        },
        "hard_nonclaims": [
            "NO_ACCEPTANCE_PROMOTION_FROM_THIS_VERIFIER_BY_ITSELF",
            "NO_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "NO_SEMANTIC_IF_CAPABILITY_CREDIT_FROM_SCORE_OPTIMALITY",
            "NO_CLAIM_BEYOND_THE_FROZEN_ACTIVE15_PUBLIC_GENERATOR_AND_PINNED_CHECKER_SCOPE",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "production_or_terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }
    pathlib.Path("livebench_punkt_context_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
