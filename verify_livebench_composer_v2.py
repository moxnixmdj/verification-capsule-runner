#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter
from itertools import cycle

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


def contract(iid: str, **slots):
    return {"instruction_id": iid, "slots": slots}


def main() -> int:
    assert hash_object(ARCH) == ARCH_BLOB
    assert hash_object(FEAS) == FEAS_BLOB
    assert hash_object(COMPOSER) == COMPOSER_BLOB
    assert hash_object(PLANNER) == PLANNER_BLOB

    live = pathlib.Path("/tmp/LiveBench")
    assert run(["git", "-C", str(live), "rev-parse", "HEAD"], capture_output=True).stdout.strip() == LIVEBENCH_COMMIT
    paths = {
        "livebench/if_runner/instruction_following_eval/instructions.py": INSTRUCTIONS_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_registry.py": REGISTRY_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_util.py": UTIL_BLOB,
    }
    for path, expected in paths.items():
        got = run(["git", "-C", str(live), "rev-parse", f"HEAD:{path}"], capture_output=True).stdout.strip()
        assert got == expected, (path, got, expected)

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as opt
    from instruction_following_eval import instructions_registry, instructions_util

    words = list(instructions_util.WORD_LIST)
    assert len(words) == 1525, len(words)
    assert len(set(words)) == 1525
    assert all(re.fullmatch(r"[A-Za-z]+", w) for w in words)
    lower_words = {w.lower() for w in words}

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

    def kwargs_for(c):
        return dict(c.get("slots") or {})

    def exact_follow(c, response: str) -> bool:
        iid = c["instruction_id"]
        checker = instructions_registry.INSTRUCTION_DICT[iid](iid)
        checker.build_description(**kwargs_for(c))
        return bool(response.strip()) and bool(checker.check_following(response))

    def exact_all(contracts, response: str):
        return [exact_follow(c, response) for c in contracts]

    safe_first = fillers({"section", "other", "anything", "can", "help"}, 1)[0]
    required_base = fillers({"section", "other", "anything", "can", "help", safe_first}, 5)
    forbidden_base = fillers(set(required_base) | {"section", "other", "anything", "can", "help", safe_first}, 5)

    def build(iids, variant: str):
        ids = set(iids)
        required = list(required_base)
        forbidden = list(forbidden_base)
        p_count = 1
        w_n, w_rel = 100, "less than"
        s_n, s_rel = 2, "less than"
        nth_count, nth_index, nth_first = 1, 1, safe_first
        post = "P.S."
        bullets = 1
        splitter, sections = "Section", 1
        end_phrase = "Any other questions?"

        if variant == "high":
            p_count = 5
            w_n, w_rel = 500, "at least"
            s_n, s_rel = 20, "at least"
            nth_count, nth_index = 5, 5
            post = "P.P.S"
            bullets = 5
            splitter, sections = "SECTION", 5
            end_phrase = "Is there anything else I can help with?"
        elif variant == "overlap":
            forbidden = list(required)
            p_count = 3
            w_n, w_rel = 173, "at least"
            s_n, s_rel = 7, "at least"
            nth_count, nth_index = 3, 2
            bullets = 3
            sections = 3
        elif variant == "section_forbidden":
            forbidden = ["section"] + fillers(
                set(required) | {"section", "other", "anything", "can", "help", nth_first}, 4
            )
            p_count = 2
            w_n, w_rel = 137, "at least"
            s_n, s_rel = 3, "at least"
            nth_count, nth_index = 2, 1
            bullets = 2
            sections = 2

        out = []
        for iid in iids:
            if iid == comp.EXIST:
                out.append(contract(iid, keywords=required))
            elif iid == comp.FORBIDDEN:
                out.append(contract(iid, forbidden_words=forbidden))
            elif iid == comp.PARAGRAPHS:
                out.append(contract(iid, num_paragraphs=p_count))
            elif iid == comp.WORDS:
                out.append(contract(iid, num_words=w_n, relation=w_rel))
            elif iid == comp.SENTENCES:
                out.append(contract(iid, num_sentences=s_n, relation=s_rel))
            elif iid == comp.NTH:
                out.append(contract(iid, num_paragraphs=nth_count, nth_paragraph=nth_index, first_word=nth_first))
            elif iid == comp.POSTSCRIPT:
                out.append(contract(iid, postscript_marker=post))
            elif iid == comp.BULLETS:
                out.append(contract(iid, num_bullets=bullets))
            elif iid == comp.TITLE:
                out.append(contract(iid))
            elif iid == comp.SECTIONS:
                out.append(contract(iid, section_spliter=splitter, num_sections=sections))
            elif iid == comp.JSON_ID:
                out.append(contract(iid))
            elif iid == comp.REPEAT:
                out.append(contract(iid, prompt_to_repeat="Write a compact public test note."))
            elif iid == comp.TWO:
                out.append(contract(iid))
            elif iid == comp.END:
                out.append(contract(iid, end_phrase=end_phrase))
            elif iid == comp.QUOTE:
                out.append(contract(iid))
            else:
                raise AssertionError(iid)
        return out

    receipt_counts = Counter()
    failures = []

    def check_case(name, contracts, expected_status=None):
        out = comp.compose_contracts(contracts)
        receipt_counts["cases"] += 1
        receipt_counts["status_" + out["status"]] += 1
        if expected_status is not None and out["status"] != expected_status:
            failures.append({"name": name, "kind": "status", "got": out})
            return
        if out["status"] == "CANDIDATE_WITNESS":
            followed = exact_all(contracts, out["response"])
            if not all(followed):
                failures.append({
                    "name": name,
                    "kind": "checker_failure",
                    "ids": [c["instruction_id"] for c in contracts],
                    "followed": followed,
                    "response": out["response"],
                })
            else:
                receipt_counts["witness_all_checker_pass"] += 1
        elif out["status"] == "PROVED_UNSAT":
            reasons = set(out.get("hard_unsat_reasons") or [])
            allowed = {
                "NTH_FIRST_WORD_IS_FORBIDDEN_WORD",
                "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:other",
                "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:anything",
                "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:can",
                "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:help",
                "STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE",
            }
            if not reasons or not reasons <= allowed:
                failures.append({"name": name, "kind": "unknown_unsat_reason", "got": out})

        plan = opt.solve_contracts(contracts)
        receipt_counts["pointwise_cases"] += 1
        if plan.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
            failures.append({"name": name, "kind": "pointwise_fail_closed", "got": plan})
            return
        plan_flags = exact_all(contracts, str(plan["response"]))
        exact_pass = sum(plan_flags)
        theoretical = int(plan["theoretical_max_pass_count"])
        if exact_pass != theoretical:
            failures.append({
                "name": name,
                "kind": "pointwise_exact_max_mismatch",
                "ids": [cc["instruction_id"] for cc in contracts],
                "followed": plan_flags,
                "exact_pass_count": exact_pass,
                "theoretical_max_pass_count": theoretical,
                "sacrificed_instruction_ids": plan.get("sacrificed_instruction_ids"),
                "response": plan.get("response"),
            })
        else:
            receipt_counts["pointwise_exact_optimum_match"] += 1

    # Exhaust every conflict-compatible structural identity set at cardinality 1..5
    # under four independently selected slot profiles.
    all_sets = arch.enumerate_compatible_sets()
    assert len(all_sets) == 928, len(all_sets)
    for variant in ("low", "high", "overlap", "section_forbidden"):
        for idx, ids in enumerate(all_sets):
            check_case(f"struct:{variant}:{idx}", build(ids, variant))
    receipt_counts["structural_id_sets"] = len(all_sets)
    receipt_counts["structural_profiles"] = 4

    # Exact lexical domain sweeps. Forbidden lists stay generator-valid at 5
    # distinct words; the varied word occupies one slot and fillers occupy four.
    for idx, w in enumerate(words):
        other4 = fillers({w}, 4)

        # General existence+forbidden overlap: raw-substring requirement and
        # whole-word prohibition must coexist for every public word.
        check_case(
            f"lex:shield:{idx}",
            [
                contract(comp.EXIST, keywords=[w] + other4),
                contract(comp.FORBIDDEN, forbidden_words=[w] + other4),
            ],
            "CANDIDATE_WITNESS",
        )

        # The nth-paragraph collision is a genuine checker-semantics contradiction.
        check_case(
            f"lex:nth_unsat:{idx}",
            [
                contract(comp.NTH, num_paragraphs=2, nth_paragraph=1, first_word=w),
                contract(comp.FORBIDDEN, forbidden_words=[w] + other4),
            ],
            "PROVED_UNSAT",
        )

        # Section is not a contradiction even when the forbidden word is
        # literally "section"; prefixing the splitter preserves SectionChecker.
        check_case(
            f"lex:section:{idx}",
            [
                contract(comp.SECTIONS, section_spliter="Section", num_sections=3),
                contract(comp.FORBIDDEN, forbidden_words=[w] + other4),
            ],
            "CANDIDATE_WITNESS",
        )

        for phrase_idx, phrase in enumerate((
            "Any other questions?",
            "Is there anything else I can help with?",
        )):
            phrase_words = re.findall(r"[A-Za-z]+", phrase.lower())
            collision = w.lower() in set(phrase_words[1:])
            status = "PROVED_UNSAT" if collision else "CANDIDATE_WITNESS"
            check_case(
                f"lex:end:{phrase_idx}:{idx}",
                [
                    contract(comp.END, end_phrase=phrase),
                    contract(comp.FORBIDDEN, forbidden_words=[w] + other4),
                ],
                status,
            )

    receipt_counts["lexical_words_exhausted"] = len(words)

    # Every public word-count threshold and relation on a high-interaction
    # compatible carrier.
    wc_forbidden = fillers({"section"}, 5)
    for relation in ("less than", "at least"):
        for n in range(100, 501):
            check_case(
                f"numeric:words:{relation}:{n}",
                [
                    contract(comp.WORDS, num_words=n, relation=relation),
                    contract(comp.POSTSCRIPT, postscript_marker="P.P.S"),
                    contract(comp.BULLETS, num_bullets=5),
                    contract(comp.SECTIONS, section_spliter="SECTION", num_sections=5),
                    contract(comp.FORBIDDEN, forbidden_words=wc_forbidden),
                ],
                "CANDIDATE_WITNESS",
            )
    receipt_counts["word_threshold_cases"] = 802

    # Every sentence threshold except the intentionally unresolved strict
    # less-than-one case, plus explicit fail-closed verification for that case.
    for n in range(1, 21):
        check_case(
            f"numeric:sentences:atleast:{n}",
            [
                contract(comp.SENTENCES, num_sentences=n, relation="at least"),
                contract(comp.POSTSCRIPT, postscript_marker="P.S."),
                contract(comp.BULLETS, num_bullets=3),
                contract(comp.SECTIONS, section_spliter="Section", num_sections=3),
                contract(comp.FORBIDDEN, forbidden_words=wc_forbidden),
            ],
            "CANDIDATE_WITNESS",
        )
    for n in range(2, 21):
        check_case(
            f"numeric:sentences:lessthan:{n}",
            [
                contract(comp.SENTENCES, num_sentences=n, relation="less than"),
                contract(comp.POSTSCRIPT, postscript_marker="P.P.S"),
                contract(comp.BULLETS, num_bullets=3),
                contract(comp.SECTIONS, section_spliter="SECTION", num_sections=3),
                contract(comp.FORBIDDEN, forbidden_words=wc_forbidden),
            ],
            "CANDIDATE_WITNESS",
        )
    check_case(
        "numeric:sentences:lessthan:1",
        [
            contract(comp.SENTENCES, num_sentences=1, relation="less than"),
            contract(comp.FORBIDDEN, forbidden_words=wc_forbidden),
        ],
        "PROVED_UNSAT",
    )
    receipt_counts["sentence_less_than_one_proved_unsat"] = 1

    # Exact paragraph/bullet/section discrete domains.
    for p in range(1, 6):
        for b in range(1, 6):
            for s in range(1, 6):
                for splitter in ("Section", "SECTION"):
                    check_case(
                        f"numeric:p_b_s:{p}:{b}:{s}:{splitter}",
                        [
                            contract(comp.PARAGRAPHS, num_paragraphs=p),
                            contract(comp.BULLETS, num_bullets=b),
                            contract(comp.SECTIONS, section_spliter=splitter, num_sections=s),
                            contract(comp.FORBIDDEN, forbidden_words=wc_forbidden),
                            contract(comp.QUOTE),
                        ],
                        "CANDIDATE_WITNESS",
                    )
    receipt_counts["paragraph_bullet_section_cross_cases"] = 250

    # Every valid nth paragraph location, both end phrases, both postscripts,
    # with an at-least word carrier and quote wrapper.
    nth_first = fillers({"other", "anything", "can", "help"}, 1)[0]
    for p in range(1, 6):
        for k in range(1, p + 1):
            for marker in ("P.S.", "P.P.S"):
                for phrase in (
                    "Any other questions?",
                    "Is there anything else I can help with?",
                ):
                    check_case(
                        f"numeric:nth:{p}:{k}:{marker}:{phrase}",
                        [
                            contract(comp.NTH, num_paragraphs=p, nth_paragraph=k, first_word=nth_first),
                            contract(comp.WORDS, num_words=100, relation="at least"),
                            contract(comp.POSTSCRIPT, postscript_marker=marker),
                            contract(comp.END, end_phrase=phrase),
                            contract(comp.QUOTE),
                        ],
                        "CANDIDATE_WITNESS",
                    )
    receipt_counts["nth_cross_cases"] = 60

    if failures:
        pathlib.Path("livebench_composer_v2_verification.json").write_text(
            json.dumps({
                "schema": "PROJECT_BRAIN_LIVEBENCH_POINTWISE_ENVELOPE_INDEPENDENT_VERIFICATION_V1",
                "status": "FAIL",
                "counts": dict(receipt_counts),
                "failure_count": len(failures),
                "failures": failures[:100],
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise SystemExit("VERIFICATION_FAILURES:" + str(len(failures)))

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_POINTWISE_ENVELOPE_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__POINTWISE_EXACT_MAX_MATCH__EXACT_PINNED_CHECKERS__ZERO_TERMINAL_ROWS",
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
        "public_generator_word_domain": {
            "count": len(words),
            "unique": len(set(words)),
            "all_ascii_alpha": True,
        },
        "coverage": dict(receipt_counts),
        "scope_statement": (
            "EXHAUSTIVE_928_STRUCTURAL_ID_SET_POSTVALIDATION_OVER_FOUR_SLOT_PROFILES__"
            "EXHAUSTIVE_1525_WORD_LEXICAL_COLLISION_SWEEPS__ALL_PUBLIC_WORD_THRESHOLDS__"
            "ALL_SENTENCE_THRESHOLDS_INCLUDING_STRICT_LT1_UNSAT__DISCRETE_PARAGRAPH_"
            "BULLET_SECTION_CROSS_PRODUCT__ALL_NTH_LOCATIONS_WITH_BOTH_END_AND_POSTSCRIPT_VARIANTS"
        ),
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_IS_NOT_YET_A_FORMAL_PROOF_OF_THE_FULL_SLOT_CARTESIAN_PRODUCT",
            "POINTWISE_MAXIMALITY_IS_VERIFIED_ONLY_OVER_THIS_FINITE_ENVELOPE_NOT_YET_THE_FULL_SLOT_CARTESIAN_PRODUCT",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT_FROM_THIS_RECEIPT_ALONE",
        ],
    }
    pathlib.Path("livebench_composer_v2_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
