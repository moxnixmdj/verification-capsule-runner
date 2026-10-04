#!/usr/bin/env python3
from __future__ import annotations

import inspect
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

THEOREM_BLOB = "7916b03fbb2fe6e3fd3c9777a436e70174b51111"
ARCH_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
COMPOSER_BLOB = "d73ec366b32252996258eae6d10d67d4d6a5e042"
FEAS_BLOB = "7477f5ea5bdeac3595ee2784a38d078fe2f385b0"
PLANNER_BLOB = "71e637c70edf1c582e28ea38b3b798965c803a06"
LEXICAL_BLOB = "4144a0e4375fffc414d20d012797736dc52be4ac"
PREDECESSOR_RECEIPT_BLOB = "2284e57b4d8bdd8e7344bdab8f9a6fff221a6526"
PREDECESSOR_VERIFIER_BLOB = "d3fbe4ce359326f8199d3fcfd9ad158510de5d3a"

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
EVAL_MAIN_BLOB = "4a341984936c4d609644a3b77f8c030ac5aa7269"

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_semantic_quotient_v1_20261005"
RUNTIME = SUBJECT / "canonical/runtime"
THEOREM = RUNTIME / "livebench_legacy15_semantic_quotient_completeness_v1.py"
ARCH = RUNTIME / "livebench_legacy15_composition_archetypes_v1.py"
COMPOSER = RUNTIME / "livebench_legacy15_contract_composer_v2.py"
FEAS = RUNTIME / "livebench_legacy15_slot_feasibility_v1.py"
PLANNER = RUNTIME / "livebench_legacy15_pointwise_optimal_v1.py"
LEXICAL = RUNTIME / "livebench_legacy15_lexical_collision_signatures_v2.py"
PREDECESSOR_RECEIPT = SUBJECT / "evidence/LIVEBENCH_POINTWISE_ENVELOPE_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json"
PREDECESSOR_VERIFIER = ROOT / "verify_livebench_composer_v2.py"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def hash_object(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()


def contract(iid: str, **slots):
    return {"instruction_id": iid, "slots": slots}


def main() -> int:
    expected_subject = {
        THEOREM: THEOREM_BLOB,
        ARCH: ARCH_BLOB,
        COMPOSER: COMPOSER_BLOB,
        FEAS: FEAS_BLOB,
        PLANNER: PLANNER_BLOB,
        LEXICAL: LEXICAL_BLOB,
        PREDECESSOR_RECEIPT: PREDECESSOR_RECEIPT_BLOB,
        PREDECESSOR_VERIFIER: PREDECESSOR_VERIFIER_BLOB,
    }
    for path, expected in expected_subject.items():
        actual = hash_object(path)
        assert actual == expected, (path, actual, expected)

    predecessor = json.loads(PREDECESSOR_RECEIPT.read_text(encoding="utf-8"))
    assert predecessor["exact_result"]["total_cases"] == 12489
    assert predecessor["exact_result"]["pointwise_exact_optimum_match"] == 12489
    assert predecessor["zero_terminal_boundary"] == {
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "target_scores_read": 0,
    }

    live = pathlib.Path("/tmp/LiveBench")
    assert run(["git", "-C", str(live), "rev-parse", "HEAD"], capture_output=True).stdout.strip() == LIVEBENCH_COMMIT
    source_blobs = {
        "livebench/if_runner/instruction_following_eval/instructions.py": INSTRUCTIONS_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_registry.py": REGISTRY_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_util.py": UTIL_BLOB,
        "livebench/if_runner/instruction_following_eval/evaluation_main.py": EVAL_MAIN_BLOB,
    }
    for path, expected in source_blobs.items():
        actual = run(
            ["git", "-C", str(live), "rev-parse", f"HEAD:{path}"],
            capture_output=True,
        ).stdout.strip()
        assert actual == expected, (path, actual, expected)

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))

    from canonical.runtime import livebench_legacy15_semantic_quotient_completeness_v1 as theorem
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as opt
    from canonical.runtime import livebench_legacy15_lexical_collision_signatures_v2 as lex
    from instruction_following_eval import instructions
    from instruction_following_eval import instructions_registry
    from instruction_following_eval import instructions_util

    # Exact public source domains.
    assert instructions._NUM_WORDS_LOWER_LIMIT == 100
    assert instructions._NUM_WORDS_UPPER_LIMIT == 500
    assert instructions._MAX_NUM_SENTENCES == 20
    assert instructions._NUM_PARAGRAPHS == 5
    assert instructions._NUM_BULLETS == 5
    assert instructions._NUM_SECTIONS == 5
    assert tuple(instructions._POSTSCRIPT_MARKER) == ("P.S.", "P.P.S")
    assert tuple(instructions._SECTION_SPLITER) == ("Section", "SECTION")
    assert tuple(instructions._ENDING_OPTIONS) == (
        "Any other questions?",
        "Is there anything else I can help with?",
    )

    words = lex.load_pinned_word_list(live)
    cert = theorem.verify(words)
    assert cert["status"] == "PASS__FULL_PUBLIC_GENERATOR_ACTIVE15_SEMANTIC_QUOTIENT_COMPLETE"
    assert cert["lexical_basis"]["word_count"] == 1525
    assert cert["lexical_basis"]["end_collisions"] == ["anything", "can", "help", "other"]
    assert cert["lexical_basis"]["section_collisions"] == ["section"]
    assert cert["lexical_basis"]["postscript_collisions"] == []
    assert cert["factors"]["structural_identity_factor"]["compatible_set_count"] == 928
    assert cert["acceptance_credit"] is False

    # Universal repeat-prompt lemma. The exact pinned source blob is already
    # bound above. Its checker is literally a stripped case-insensitive prefix
    # predicate; the exact pinned composer literally places stripped prompt text
    # first. Therefore the prompt payload itself does not need finite sampling.
    repeat_checker_source = " ".join(
        inspect.getsource(instructions.RepeatPromptThenAnswer.check_following).split()
    )
    assert (
        "value.strip().lower().startswith(self._prompt_to_repeat.strip().lower())"
        in repeat_checker_source
    )
    repeat_builder_source = " ".join(inspect.getsource(comp._special_repeat).split())
    assert "pieces = [base]" in repeat_builder_source
    assert 'return "\\n".join(pieces)' in repeat_builder_source

    # Derive exact special connected components from the frozen conflict graph.
    special = theorem.verify_special_component_isolation()
    assert special[comp.JSON_ID] == sorted([comp.EXIST, comp.FORBIDDEN])
    assert special[comp.REPEAT] == sorted([comp.EXIST, comp.TITLE])
    assert special[comp.TWO] == sorted([comp.EXIST, comp.FORBIDDEN, comp.TITLE])

    def fillers(exclude=(), n=5):
        ex = {str(x).lower() for x in exclude}
        out = []
        for w in words:
            if w.lower() not in ex:
                out.append(w)
                ex.add(w.lower())
            if len(out) == n:
                return out
        raise AssertionError("not enough fillers")

    safe_first = fillers({"section", "other", "anything", "can", "help"}, 1)[0]
    required_base = fillers(
        {"section", "other", "anything", "can", "help", safe_first}, 5
    )
    forbidden_base = fillers(
        set(required_base)
        | {"section", "other", "anything", "can", "help", safe_first},
        5,
    )

    def exact_follow(c, response: str) -> bool:
        iid = c["instruction_id"]
        checker = instructions_registry.INSTRUCTION_DICT[iid](iid)
        checker.build_description(**dict(c.get("slots") or {}))
        return bool(response.strip()) and bool(checker.check_following(response))

    def exact_all(contracts, response: str):
        return [exact_follow(c, response) for c in contracts]

    adversarial_repeat = (
        "  Mixed CASE request.\n"
        "<<already-title-like>>\n"
        "******\n"
        "Section 9 P.S. Any other questions?\n"
        "Unicode: Ω عربى 日本語  "
    )

    def build(iids, mode: str, sig=None):
        required = list(sig["existence_keywords"]) if sig is not None else list(required_base)
        forbidden = list(sig["forbidden_words"]) if sig is not None else list(forbidden_base)
        end_phrase = (
            str(sig["end_phrase"])
            if sig is not None
            else "Is there anything else I can help with?"
        )
        nth_first = str(sig["nth_word"]) if sig is not None else safe_first

        if mode == "word_floor":
            w_n, w_rel = 100, "less than"
            s_n, s_rel = 20, "at least"
        elif mode == "sentence_floor":
            w_n, w_rel = 500, "at least"
            s_n, s_rel = 2, "less than"
        elif mode in {"upper", "lexical"}:
            w_n, w_rel = 500, "at least"
            s_n, s_rel = 20, "at least"
        else:
            raise AssertionError(mode)

        out = []
        for iid in iids:
            if iid == comp.EXIST:
                out.append(contract(iid, keywords=required))
            elif iid == comp.FORBIDDEN:
                out.append(contract(iid, forbidden_words=forbidden))
            elif iid == comp.PARAGRAPHS:
                out.append(contract(iid, num_paragraphs=5))
            elif iid == comp.WORDS:
                out.append(contract(iid, num_words=w_n, relation=w_rel))
            elif iid == comp.SENTENCES:
                out.append(contract(iid, num_sentences=s_n, relation=s_rel))
            elif iid == comp.NTH:
                out.append(
                    contract(
                        iid,
                        num_paragraphs=5,
                        nth_paragraph=5,
                        first_word=nth_first,
                    )
                )
            elif iid == comp.POSTSCRIPT:
                out.append(contract(iid, postscript_marker="P.P.S"))
            elif iid == comp.BULLETS:
                out.append(contract(iid, num_bullets=5))
            elif iid == comp.TITLE:
                out.append(contract(iid))
            elif iid == comp.SECTIONS:
                out.append(
                    contract(iid, section_spliter="SECTION", num_sections=5)
                )
            elif iid == comp.JSON_ID:
                out.append(contract(iid))
            elif iid == comp.REPEAT:
                out.append(contract(iid, prompt_to_repeat=adversarial_repeat))
            elif iid == comp.TWO:
                out.append(contract(iid))
            elif iid == comp.END:
                out.append(contract(iid, end_phrase=end_phrase))
            elif iid == comp.QUOTE:
                out.append(contract(iid))
            else:
                raise AssertionError(iid)
        return out

    counts = Counter()
    failures = []

    def check_pointwise(name: str, contracts, expect_all=False):
        plan = opt.solve_contracts(contracts)
        counts["pointwise_cases"] += 1
        if plan.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
            failures.append({"name": name, "kind": "planner", "plan": plan})
            return None
        flags = exact_all(contracts, str(plan["response"]))
        exact_pass = sum(flags)
        theoretical = int(plan["theoretical_max_pass_count"])
        if exact_pass != theoretical:
            failures.append(
                {
                    "name": name,
                    "kind": "max_mismatch",
                    "ids": [c["instruction_id"] for c in contracts],
                    "flags": flags,
                    "exact_pass": exact_pass,
                    "theoretical": theoretical,
                    "sacrificed": plan.get("sacrificed_instruction_ids"),
                    "response": plan.get("response"),
                }
            )
        elif expect_all and exact_pass != len(contracts):
            failures.append(
                {
                    "name": name,
                    "kind": "unexpected_loss",
                    "ids": [c["instruction_id"] for c in contracts],
                    "sacrificed": plan.get("sacrificed_instruction_ids"),
                }
            )
        else:
            counts["pointwise_exact_max_match"] += 1
        return plan

    all_sets = arch.enumerate_compatible_sets()
    assert len(all_sets) == 928

    # Cross-factor stress that the predecessor envelope did not enumerate:
    # every structural set at the three extremal numeric interactions.
    max_word_count_under_lt100 = 0
    max_sentence_count_under_lt2 = 0
    for idx, ids in enumerate(all_sets):
        c1 = build(ids, "word_floor")
        p1 = check_pointwise(f"cross:word_floor:{idx}", c1, expect_all=True)
        if p1 is not None and comp.WORDS in ids:
            made = comp.compose_contracts(c1)
            if made.get("status") != "CANDIDATE_WITNESS":
                failures.append({"name": f"cross:word_floor:{idx}", "kind": "compose", "made": made})
            else:
                wc = instructions_util.count_words(str(made["response"]))
                max_word_count_under_lt100 = max(max_word_count_under_lt100, wc)
                if wc >= 100:
                    failures.append({"name": f"cross:word_floor:{idx}", "kind": "word_floor", "count": wc})

        c2 = build(ids, "sentence_floor")
        p2 = check_pointwise(f"cross:sentence_floor:{idx}", c2, expect_all=True)
        if p2 is not None and comp.SENTENCES in ids:
            made = comp.compose_contracts(c2)
            if made.get("status") != "CANDIDATE_WITNESS":
                failures.append({"name": f"cross:sentence_floor:{idx}", "kind": "compose", "made": made})
            else:
                sc = instructions_util.count_sentences(str(made["response"]))
                max_sentence_count_under_lt2 = max(max_sentence_count_under_lt2, sc)
                if sc >= 2:
                    failures.append({"name": f"cross:sentence_floor:{idx}", "kind": "sentence_floor", "count": sc})

        c3 = build(ids, "upper")
        check_pointwise(f"cross:upper:{idx}", c3, expect_all=True)

    counts["cross_structural_sets"] = len(all_sets)
    counts["cross_numeric_profiles"] = 3

    # Exact combined lexical quotient, not merely one-word-at-a-time sweeps.
    # This is the missing higher-order test: every reachable simultaneous nth
    # + end forbidden-membership signature is checked on every structural set
    # for which such a collision can matter.
    signatures = lex.enumerate_signatures(words)
    assert len(signatures) == 192
    relevant_sets = [
        ids
        for ids in all_sets
        if comp.FORBIDDEN in ids and (comp.NTH in ids or comp.END in ids)
    ]
    counts["lexical_reachable_signatures"] = len(signatures)
    counts["lexical_relevant_structural_sets"] = len(relevant_sets)

    def expected_lexical_collision(ids, sig):
        if comp.NTH in ids and bool(sig["nth_in_forbidden"]):
            return True
        if comp.END in ids:
            members = sig["special_forbidden_membership"]
            phrase = sig["end_phrase"]
            if phrase == "Any other questions?" and members["other"]:
                return True
            if phrase == "Is there anything else I can help with?" and (
                members["anything"] or members["can"] or members["help"]
            ):
                return True
        return False

    for sig_idx, sig in enumerate(signatures):
        for set_idx, ids in enumerate(relevant_sets):
            contracts = build(ids, "lexical", sig)
            plan = check_pointwise(f"lexq:{sig_idx}:{set_idx}", contracts)
            if plan is None:
                continue
            expected_collision = expected_lexical_collision(ids, sig)
            sacrificed = set(plan.get("sacrificed_instruction_ids") or [])
            expected_sacrifice = {comp.FORBIDDEN} if expected_collision else set()
            if sacrificed != expected_sacrifice:
                failures.append(
                    {
                        "name": f"lexq:{sig_idx}:{set_idx}",
                        "kind": "lexical_sacrifice",
                        "expected": sorted(expected_sacrifice),
                        "got": sorted(sacrificed),
                        "sig": sig,
                        "ids": list(ids),
                    }
                )

    counts["lexical_cross_cases"] = len(signatures) * len(relevant_sets)

    # Directly postvalidate the entire special repeat component with an
    # adversarial visible payload. The source-level prefix proof above makes
    # this representative check supplemental rather than a finite-domain claim.
    for ids in all_sets:
        if comp.REPEAT not in ids:
            continue
        contracts = build(ids, "upper")
        check_pointwise("repeat:" + ",".join(ids), contracts, expect_all=True)
        counts["repeat_structural_sets"] += 1

    if failures:
        receipt = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY15_SEMANTIC_QUOTIENT_INDEPENDENT_VERIFICATION_V1",
            "status": "FAIL",
            "counts": dict(counts),
            "max_word_count_under_lt100": max_word_count_under_lt100,
            "max_sentence_count_under_lt2": max_sentence_count_under_lt2,
            "failure_count": len(failures),
            "failures": failures[:100],
        }
        pathlib.Path("livebench_semantic_quotient_v1_verification.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise SystemExit("SEMANTIC_QUOTIENT_VERIFICATION_FAILURES:" + str(len(failures)))

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY15_SEMANTIC_QUOTIENT_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__FULL_ACTIVE15_SEMANTIC_QUOTIENT__EXACT_PINNED_CHECKERS__ZERO_TERMINAL_ROWS",
        "subject_blobs": {
            "semantic_quotient_theorem": THEOREM_BLOB,
            "archetypes": ARCH_BLOB,
            "composer_v2": COMPOSER_BLOB,
            "slot_feasibility": FEAS_BLOB,
            "pointwise_planner": PLANNER_BLOB,
            "lexical_signatures_v2": LEXICAL_BLOB,
            "predecessor_receipt": PREDECESSOR_RECEIPT_BLOB,
            "predecessor_verifier": PREDECESSOR_VERIFIER_BLOB,
        },
        "pinned_livebench": {
            "commit": LIVEBENCH_COMMIT,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "registry_blob": REGISTRY_BLOB,
            "instructions_util_blob": UTIL_BLOB,
            "evaluation_main_blob": EVAL_MAIN_BLOB,
        },
        "proof": {
            "structural_identity_sets": 928,
            "exact_lexical_word_domain": 1525,
            "reachable_combined_lexical_signatures": 192,
            "unbounded_repeat_payload_finitely_enumerated": False,
            "unbounded_repeat_payload_closed_by_exact_source_prefix_theorem": True,
            "word_relation_threshold_pairs_predecessor_exhausted": 802,
            "sentence_relation_threshold_pairs_predecessor_exhausted": 40,
            "cross_numeric_extrema_postvalidated_over_every_structural_set": True,
            "combined_lexical_signatures_postvalidated_over_every_relevant_structural_set": True,
            "max_observed_word_count_in_worst_less_than_100_cross_profile": max_word_count_under_lt100,
            "max_observed_sentence_count_in_worst_less_than_2_cross_profile": max_sentence_count_under_lt2,
        },
        "coverage": dict(counts),
        "theorem": (
            "THE_PREDECESSOR_12489_CASE_POINTWISE_ENVELOPE_PLUS_THIS_SOURCE_BOUND_"
            "FACTORIZATION_COVERS_EVERY_PUBLIC_GENERATOR_ADMITTED_ACTIVE15_VISIBLE_CONTRACT_TUPLE"
        ),
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "terminal_frequencies_read": 0,
        "target_scores_read": 0,
        "distribution_dependence": False,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_RECEIPT_CLOSES_ACTIVE15_SEMANTIC_QUOTIENT_COMPLETENESS_BUT_DOES_NOT_BY_ITSELF_RESOLVE_THE_PUBLIC_PAPER_16_VS_15_SCOPE_INCONSISTENCY",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT_UNTIL_ACCEPTED_PREDICATE_SCOPE_IS_BOUND_TO_ACTIVE15",
        ],
    }
    pathlib.Path("livebench_semantic_quotient_v1_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
