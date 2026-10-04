#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
EVALUATION_MAIN_BLOB = "4a341984936c4d609644a3b77f8c030ac5aa7269"
GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"
COMPOSER_ENVELOPE_VERIFIER_BLOB = "d3fbe4ce359326f8199d3fcfd9ad158510de5d3a"

FROZEN_RUNTIME_BLOBS = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py":
        "71e637c70edf1c582e28ea38b3b798965c803a06",
    "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py":
        "5803c31e3972c6d40415f319e808c48420bc0388",
    "canonical/runtime/livebench_legacy15_numeric_quotient_v1.py":
        "72189bb8adb12ad36a52ee666a1f79fbb201b06b",
    "canonical/runtime/livebench_pointwise_minimum_cut_v1.py":
        "0d4e563b618f8fd7f37396a88738cefb50979ff3",
    "canonical/runtime/livebench_legacy_visible_constraint_compiler_v4.py":
        "721207ba39d502e3f610289578e9d5bab78b1fcc",
}
VISIBLE_RECEIPT_PATH = (
    "canonical/verification/"
    "LIVEBENCH_VISIBLE_COMPILER_V4_PUBLIC_GRAMMAR_AUDIT_20261005_V1.json"
)
VISIBLE_RECEIPT_BLOB = "ec0de861f6dfcdf083099c3632bdd20db65991b4"
PRECOMMIT_PATH = (
    "canonical/governance/"
    "LIVEBENCH_UNIVERSAL_POINTWISE_CLOSURE_PRECOMMIT_20261005_V1.json"
)
PRECOMMIT_BLOB = "4541ed86be4b7a132d6930eb7f71e1748e26bea8"

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_universal_construction_20261005"
OUT = ROOT / "livebench_universal_construction_verification.json"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def blob(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()


def exact_source_blob(repo: pathlib.Path, path: str) -> str:
    return run(
        ["git", "-C", str(repo), "rev-parse", f"HEAD:{path}"],
        capture_output=True,
    ).stdout.strip()


def contract(iid: str, **slots):
    return {"instruction_id": iid, "slots": slots}


def main() -> int:
    # 1) Bind every frozen subject byte from the outcome-blind precommit.
    observed = {}
    for rel, expected in FROZEN_RUNTIME_BLOBS.items():
        got = blob(SUBJECT / rel)
        assert got == expected, (rel, got, expected)
        observed[rel] = got

    assert blob(SUBJECT / VISIBLE_RECEIPT_PATH) == VISIBLE_RECEIPT_BLOB
    assert blob(SUBJECT / PRECOMMIT_PATH) == PRECOMMIT_BLOB
    assert blob(ROOT / "verify_livebench_composer_v2.py") == COMPOSER_ENVELOPE_VERIFIER_BLOB

    precommit = json.loads((SUBJECT / PRECOMMIT_PATH).read_text(encoding="utf-8"))
    assert precommit["status"].startswith("FROZEN_OUTCOME_BLIND")
    assert precommit["target_predicate"] == "LIVEBENCH_IF_GE_65_7"
    frozen = precommit["frozen_subjects"]
    assert frozen == {
        "archetypes": FROZEN_RUNTIME_BLOBS[
            "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py"
        ],
        "composer_v2": FROZEN_RUNTIME_BLOBS[
            "canonical/runtime/livebench_legacy15_contract_composer_v2.py"
        ],
        "slot_feasibility": FROZEN_RUNTIME_BLOBS[
            "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py"
        ],
        "pointwise_planner": FROZEN_RUNTIME_BLOBS[
            "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py"
        ],
        "lexical_quotient": FROZEN_RUNTIME_BLOBS[
            "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py"
        ],
        "numeric_quotient": FROZEN_RUNTIME_BLOBS[
            "canonical/runtime/livebench_legacy15_numeric_quotient_v1.py"
        ],
        "pointwise_minimum_cut": FROZEN_RUNTIME_BLOBS[
            "canonical/runtime/livebench_pointwise_minimum_cut_v1.py"
        ],
        "visible_compiler_v4": FROZEN_RUNTIME_BLOBS[
            "canonical/runtime/livebench_legacy_visible_constraint_compiler_v4.py"
        ],
    }

    # 2) Bind public source and exact runtime.
    live = pathlib.Path("/tmp/LiveBench")
    generator = pathlib.Path("/tmp/LiveBenchGenerator")
    assert run(
        ["git", "-C", str(live), "rev-parse", "HEAD"], capture_output=True
    ).stdout.strip() == LIVEBENCH_COMMIT
    assert run(
        ["git", "-C", str(generator), "rev-parse", "HEAD"], capture_output=True
    ).stdout.strip() == GENERATOR_COMMIT

    assert exact_source_blob(
        live, "livebench/if_runner/instruction_following_eval/instructions.py"
    ) == INSTRUCTIONS_BLOB
    assert exact_source_blob(
        live, "livebench/if_runner/instruction_following_eval/instructions_registry.py"
    ) == REGISTRY_BLOB
    assert exact_source_blob(
        live, "livebench/if_runner/instruction_following_eval/instructions_util.py"
    ) == UTIL_BLOB
    assert exact_source_blob(
        live, "livebench/if_runner/instruction_following_eval/evaluation_main.py"
    ) == EVALUATION_MAIN_BLOB
    assert exact_source_blob(
        generator, "livebench/if_runner/live_data.py"
    ) == GENERATOR_BLOB

    import nltk
    assert nltk.__version__ == "3.10.3"

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))

    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_lexical_slot_quotient_v1 as lex
    from canonical.runtime import livebench_legacy15_numeric_quotient_v1 as numeric
    from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as opt
    from canonical.runtime import livebench_pointwise_minimum_cut_v1 as mincut
    from instruction_following_eval import instructions_registry, instructions_util

    words = list(instructions_util.WORD_LIST)
    assert len(words) == 1525
    assert len(set(words)) == 1525
    assert all(w.isascii() and w.isalpha() for w in words)
    lower_words = {w.lower() for w in words}

    def exact_follow(c, response: str) -> bool:
        iid = str(c["instruction_id"])
        checker = instructions_registry.INSTRUCTION_DICT[iid](iid)
        checker.build_description(**dict(c.get("slots") or {}))
        return bool(response.strip()) and bool(checker.check_following(response))

    # Cache exact checker calls. This does not reduce the 356,352-state proof:
    # it only deduplicates byte-identical checker inputs shared by quotient states.
    exact_cache = {}

    def exact_follow_cached(c, response: str) -> bool:
        key = (
            str(c["instruction_id"]),
            json.dumps(dict(c.get("slots") or {}), sort_keys=True, ensure_ascii=False),
            response,
        )
        if key not in exact_cache:
            exact_cache[key] = exact_follow(c, response)
        return exact_cache[key]

    def exact_all(contracts, response: str):
        return [exact_follow_cached(c, response) for c in contracts]

    def five_with(w: str, offset: int = 0):
        out = [w]
        n = len(words)
        for j in range(n):
            x = words[(offset + j) % n]
            if x not in out:
                out.append(x)
            if len(out) == 5:
                return out
        raise AssertionError("FIVE_DISTINCT_WORDS_UNAVAILABLE")

    # 3) Exact public-word and fixed-scaffold facts.
    fixed_scaffold = (
        "Section SECTION Any other questions? "
        "Is there anything else I can help with? P.S. P.P.S"
    )
    fixed_public_intersection = sorted(
        {w.lower() for w in re.findall(r"[A-Za-z]+", fixed_scaffold)}
        & lower_words
    )
    assert fixed_public_intersection == [
        "anything", "can", "help", "other", "section"
    ]

    # 4) Exhaust the carrier theorem for every public word identity.
    carrier_cases = 0
    for i, w in enumerate(words):
        five = five_with(w, i + 1)
        cs = [
            contract(comp.EXIST, keywords=five),
            contract(comp.FORBIDDEN, forbidden_words=five),
        ]
        out = comp.compose_contracts(cs)
        assert out["status"] == "CANDIDATE_WITNESS", (w, out)
        flags = exact_all(cs, str(out["response"]))
        assert flags == [True, True], (w, flags, out["response"])
        carrier_cases += 1
    assert carrier_cases == 1525

    # 5) Exhaust the Section whole-word shield over every public section count
    # and both public splitter spellings.
    section_word = next(w for w in words if w.lower() == "section")
    section_forbidden = five_with(section_word, words.index(section_word) + 1)
    section_shield_cases = 0
    for splitter in ("Section", "SECTION"):
        for n in range(1, 6):
            cs = [
                contract(comp.SECTIONS, section_spliter=splitter, num_sections=n),
                contract(comp.FORBIDDEN, forbidden_words=section_forbidden),
            ]
            out = comp.compose_contracts(cs)
            assert out["status"] == "CANDIDATE_WITNESS", (splitter, n, out)
            assert exact_all(cs, str(out["response"])) == [True, True]
            section_shield_cases += 1
    assert section_shield_cases == 10

    # 6) Exact quotient proofs.
    a = arch.verify()
    l = lex.verify()
    n = numeric.verify()
    cut = mincut.verify()

    assert a["compatible_set_count"] == 928
    assert l["exact_reachable_signature_count"] == 192
    assert n["status"] == "PASS__PARAMETRIC_NUMERIC_REDUCTION"
    assert n["word_upper_bound"]["analytic_constructor_ceiling"] == 48
    assert n["word_upper_bound"]["minimum_safety_margin"] == 52
    assert set(n["sentence_partition"]) == {
        "less_than_1", "less_than_2_to_20", "at_least_1_to_20"
    }
    assert cut["exact_classification_cases"] == 356352
    assert cut["maximum_mandatory_sacrifices_per_case"] == 2
    assert {
        row["minimum_sacrifice"] for row in cut["mandatory_loss_coordinates"]
    } == {comp.SENTENCES, comp.FORBIDDEN}

    # 7) The frozen universal gate: exact-postvalidate every one of the
    # 928 x 192 x 2 representatives against the pinned strict checkers.
    exact_states = 0
    exact_optimum_matches = 0
    sacrifice_histogram = Counter()
    archetype_histogram = Counter()
    plan_cache = {}
    failures = []

    signatures = lex.enumerate_signatures()
    id_sets = arch.enumerate_compatible_sets()
    assert len(signatures) == 192
    assert len(id_sets) == 928

    for ids_tuple in id_sets:
        archetype_histogram[arch.archetype(ids_tuple)] += 192 * 2
        for sig in signatures:
            for sentence_zero in (False, True):
                cs = mincut._skeleton(
                    ids_tuple, sig, sentence_zero=sentence_zero
                )
                plan_key = json.dumps(cs, sort_keys=True, ensure_ascii=False)
                plan = plan_cache.get(plan_key)
                if plan is None:
                    plan = opt.solve_contracts(cs)
                    plan_cache[plan_key] = plan

                exact_states += 1
                if plan.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
                    failures.append({
                        "kind": "planner_status",
                        "ids": list(ids_tuple),
                        "signature": repr(sig),
                        "sentence_zero": sentence_zero,
                        "plan": plan,
                    })
                    break

                response = str(plan["response"])
                flags = exact_all(cs, response)
                exact_pass = sum(flags)
                theoretical = int(plan["theoretical_max_pass_count"])
                if exact_pass != theoretical:
                    failures.append({
                        "kind": "pointwise_exact_mismatch",
                        "ids": list(ids_tuple),
                        "signature": repr(sig),
                        "sentence_zero": sentence_zero,
                        "flags": flags,
                        "exact_pass": exact_pass,
                        "theoretical": theoretical,
                        "sacrificed": plan.get("sacrificed_instruction_ids"),
                        "response": response,
                    })
                    break

                sacrificed = tuple(sorted(plan.get("sacrificed_instruction_ids") or []))
                if not set(sacrificed) <= {comp.SENTENCES, comp.FORBIDDEN}:
                    failures.append({
                        "kind": "unexpected_sacrifice",
                        "ids": list(ids_tuple),
                        "sacrificed": sacrificed,
                    })
                    break
                sacrifice_histogram[len(sacrificed)] += 1
                exact_optimum_matches += 1

            if failures:
                break
        if failures:
            break

    if failures:
        receipt = {
            "schema":
                "PROJECT_BRAIN_LIVEBENCH_UNIVERSAL_POINTWISE_GATE_INDEPENDENT_VERIFICATION_V1",
            "status": "FAIL",
            "exact_states_executed": exact_states,
            "exact_optimum_matches": exact_optimum_matches,
            "failures": failures[:20],
            "terminal_rows_read": 0,
            "hidden_terminal_kwargs_read": 0,
            "terminal_instruction_id_lists_read": 0,
            "target_scores_read": 0,
        }
        OUT.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(receipt, sort_keys=True))
        return 1

    assert exact_states == 928 * 192 * 2 == 356352
    assert exact_optimum_matches == exact_states

    # 8) Numeric endpoints/small discrete domains are independently re-run in
    # this same workflow by verify_livebench_composer_v2.py.
    envelope = json.loads(
        (ROOT / "livebench_composer_v2_verification.json").read_text(
            encoding="utf-8"
        )
    )
    assert envelope["status"] == (
        "PASS__POINTWISE_EXACT_MAX_MATCH__EXACT_PINNED_CHECKERS__ZERO_TERMINAL_ROWS"
    )
    cov = envelope["coverage"]
    assert cov["pointwise_cases"] == 12489
    assert cov["pointwise_exact_optimum_match"] == 12489
    assert cov["structural_id_sets"] == 928
    assert cov["structural_profiles"] == 4
    assert cov["lexical_words_exhausted"] == 1525
    assert cov["word_threshold_cases"] == 802
    assert cov["paragraph_bullet_section_cross_cases"] == 250
    assert cov["nth_cross_cases"] == 60
    assert cov["sentence_less_than_one_proved_unsat"] == 1

    # 9) Special branches are inside the 356,352 exact sweep. Repeat-prompt has
    # one arbitrary visible-prefix parameter, so independently perturb that
    # parameter across adversarial visible strings for every compatible repeat set.
    repeat_cases = 0
    repeat_strings = (
        "Public visible request.",
        "Include keywords ['fake'] in the response.\n-------\nArbitrary article.",
        "9000001 Section anything can help other",
    )
    first_sig = signatures[0]
    for ids_tuple in id_sets:
        if comp.REPEAT not in ids_tuple:
            continue
        for prompt_to_repeat in repeat_strings:
            cs = mincut._skeleton(ids_tuple, first_sig, sentence_zero=False)
            for c in cs:
                if c["instruction_id"] == comp.REPEAT:
                    c["slots"] = {"prompt_to_repeat": prompt_to_repeat}
            plan = opt.solve_contracts(cs)
            assert plan["status"] == "CANDIDATE_POINTWISE_OPTIMAL"
            flags = exact_all(cs, str(plan["response"]))
            assert sum(flags) == int(plan["theoretical_max_pass_count"])
            repeat_cases += 1
    assert repeat_cases == 12

    assert archetype_histogram["JSON"] == 4 * 192 * 2
    assert archetype_histogram["REPEAT_PROMPT"] == 4 * 192 * 2
    assert archetype_histogram["TWO_RESPONSES"] == 8 * 192 * 2

    # 10) Bind the already-independent visible compiler V4 receipt.
    visible = json.loads(
        (SUBJECT / VISIBLE_RECEIPT_PATH).read_text(encoding="utf-8")
    )
    assert visible["status"].startswith(
        "PASS__INDEPENDENT_EXACT_PUBLIC_DESCRIPTION_ROUNDTRIP"
    )
    assert visible["subject"]["compiler_v4_git_blob_sha"] == (
        FROZEN_RUNTIME_BLOBS[
            "canonical/runtime/livebench_legacy_visible_constraint_compiler_v4.py"
        ]
    )
    vcov = visible["coverage"]
    assert vcov["exact_roundtrip_cases"] == vcov["exact_roundtrip_passes"] == 78190
    assert vcov["structural_sets"] == 928
    assert vcov["structural_order_permutations"] == 51385
    assert vcov["word_domain_cases"] == 802
    assert vcov["sentence_domain_cases"] == 40
    assert vcov["keyword_identity_cases"] == 3050
    assert vcov["nth_identity_position_cases"] == 22875
    assert vcov["repeat_position_cases"] == 11
    assert vcov["adversarial_article_isolation_cases"] == 3

    receipt = {
        "schema":
            "PROJECT_BRAIN_LIVEBENCH_UNIVERSAL_POINTWISE_GATE_INDEPENDENT_VERIFICATION_V1",
        "status": (
            "PASS__ALL_PRECOMMITTED_UNIVERSAL_POINTWISE_GATES__"
            "356352_OF_356352_EXACT_POINTWISE_OPTIMA__ZERO_TERMINAL_ROWS"
        ),
        "precommit_blob": PRECOMMIT_BLOB,
        "frozen_runtime_blobs": observed,
        "pinned_public_source": {
            "livebench_commit": LIVEBENCH_COMMIT,
            "historical_generator_commit": GENERATOR_COMMIT,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "registry_blob": REGISTRY_BLOB,
            "instructions_util_blob": UTIL_BLOB,
            "evaluation_main_blob": EVALUATION_MAIN_BLOB,
            "generator_blob": GENERATOR_BLOB,
            "nltk_version": nltk.__version__,
        },
        "public_word_domain": {
            "count": len(words),
            "unique": len(set(words)),
            "all_ascii_alpha": True,
            "fixed_scaffold_public_word_intersection": fixed_public_intersection,
            "carrier_identity_cases": carrier_cases,
            "section_shield_cases": section_shield_cases,
        },
        "quotients": {
            "structural_id_sets": a["compatible_set_count"],
            "lexical_signatures": l["exact_reachable_signature_count"],
            "numeric_status": n["status"],
            "word_constructor_ceiling": n["word_upper_bound"][
                "analytic_constructor_ceiling"
            ],
            "public_min_word_threshold": n["word_upper_bound"][
                "public_threshold_domain"
            ][0],
            "sentence_classes": sorted(n["sentence_partition"]),
            "minimum_cut_classification_cases": cut["exact_classification_cases"],
        },
        "universal_exact_postvalidation": {
            "states": exact_states,
            "exact_pointwise_optimum_matches": exact_optimum_matches,
            "sacrifice_histogram": dict(sorted(sacrifice_histogram.items())),
            "archetype_state_histogram": dict(sorted(archetype_histogram.items())),
            "unique_planner_inputs_after_exact_dedup": len(plan_cache),
            "unique_exact_checker_inputs_after_exact_dedup": len(exact_cache),
        },
        "numeric_and_discrete_crosscheck": {
            "independent_envelope_status": envelope["status"],
            "pointwise_cases": cov["pointwise_cases"],
            "word_threshold_cases": cov["word_threshold_cases"],
            "paragraph_bullet_section_cross_cases":
                cov["paragraph_bullet_section_cross_cases"],
            "nth_cross_cases": cov["nth_cross_cases"],
            "sentence_less_than_one_proved_unsat":
                cov["sentence_less_than_one_proved_unsat"],
        },
        "special_routes": {
            "json_exact_states": archetype_histogram["JSON"],
            "repeat_exact_states": archetype_histogram["REPEAT_PROMPT"],
            "two_response_exact_states": archetype_histogram["TWO_RESPONSES"],
            "repeat_adversarial_parameter_cases": repeat_cases,
        },
        "visible_compiler_v4": {
            "receipt_blob": VISIBLE_RECEIPT_BLOB,
            "workflow_run_id": visible["independent_runner"]["workflow_run_id"],
            "exact_roundtrip_cases": vcov["exact_roundtrip_cases"],
            "structural_order_permutations": vcov[
                "structural_order_permutations"
            ],
        },
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "target_responses_read": 0,
        "target_scores_read": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "conclusion": (
            "THE_FROZEN_OUTCOME_BLIND_PRECOMMIT_SUCCESS_GATE_IS_SATISFIED__"
            "THIS_RECEIPT_MAY_BE_COMBINED_WITH_THE_PREEXISTING_DISTRIBUTION_FREE_"
            "DOMINANCE_THEOREM_AND_VISIBLE_COMPILER_SCOPE_BINDING_FOR_A_SEPARATE_"
            "LIVEBENCH_ACCEPTANCE_PROMOTION"
        ),
        "hard_nonclaims": [
            "THIS_RECEIPT_DOES_NOT_ITSELF_MUTATE_THE_BRAIN_ACCEPTANCE_LEDGER",
            "THIS_RECEIPT_DOES_NOT_BY_ITSELF_COMPLETE_THE_TERMINAL_GOAL",
        ],
    }
    OUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
