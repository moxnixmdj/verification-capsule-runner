#!/usr/bin/env python3
# verification trigger after PR creation; no subject semantics
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter
from itertools import product

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

SPECIAL = ("other", "anything", "can", "help")
END_PHRASES = (
    "Any other questions?",
    "Is there anything else I can help with?",
)

PROFILES = {
    "low": {
        "paragraphs": 1,
        "word_n": 100,
        "word_rel": "less than",
        "sent_n": 2,
        "sent_rel": "less than",
        "nth_n": 1,
        "nth_k": 1,
        "post": "P.S.",
        "bullets": 1,
        "splitter": "Section",
        "sections": 1,
    },
    "high": {
        "paragraphs": 5,
        "word_n": 500,
        "word_rel": "at least",
        "sent_n": 20,
        "sent_rel": "at least",
        "nth_n": 5,
        "nth_k": 5,
        "post": "P.P.S",
        "bullets": 5,
        "splitter": "SECTION",
        "sections": 5,
    },
    "mixed": {
        "paragraphs": 3,
        "word_n": 100,
        "word_rel": "less than",
        "sent_n": 20,
        "sent_rel": "at least",
        "nth_n": 3,
        "nth_k": 2,
        "post": "P.S.",
        "bullets": 3,
        "splitter": "Section",
        "sections": 3,
    },
    "sentence_zero": {
        "paragraphs": 3,
        "word_n": 100,
        "word_rel": "at least",
        "sent_n": 1,
        "sent_rel": "less than",
        "nth_n": 3,
        "nth_k": 2,
        "post": "P.P.S",
        "bullets": 3,
        "splitter": "SECTION",
        "sections": 3,
    },
}


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def hash_object(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()


def contract(iid: str, **slots):
    return {"instruction_id": iid, "slots": slots}


def main() -> int:
    for path, expected in (
        (ARCH, ARCH_BLOB),
        (FEAS, FEAS_BLOB),
        (COMPOSER, COMPOSER_BLOB),
        (PLANNER, PLANNER_BLOB),
    ):
        assert hash_object(path) == expected, (path, hash_object(path), expected)

    live = pathlib.Path("/tmp/LiveBench")
    assert run(["git", "-C", str(live), "rev-parse", "HEAD"], capture_output=True).stdout.strip() == LIVEBENCH_COMMIT
    public_paths = {
        "livebench/if_runner/instruction_following_eval/instructions.py": INSTRUCTIONS_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_registry.py": REGISTRY_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_util.py": UTIL_BLOB,
    }
    for path, expected in public_paths.items():
        got = run(["git", "-C", str(live), "rev-parse", f"HEAD:{path}"], capture_output=True).stdout.strip()
        assert got == expected, (path, got, expected)

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as opt
    from instruction_following_eval import instructions_registry, instructions_util

    words = tuple(instructions_util.WORD_LIST)
    assert len(words) == 1525
    assert len(set(words)) == 1525
    assert all(re.fullmatch(r"[A-Za-z]+", w) for w in words)
    lower = {w.lower(): w for w in words}
    assert all(w in lower for w in SPECIAL)

    generic = next(w for w in words if w.lower() not in set(SPECIAL))
    existence = []
    excluded_for_existence = set(SPECIAL) | {generic.lower(), "section"}
    for w in words:
        if w.lower() not in excluded_for_existence:
            existence.append(w)
        if len(existence) == 5:
            break
    assert len(existence) == 5

    def fillers(exclude, n):
        ex = {str(x).lower() for x in exclude}
        out = []
        for w in words:
            if w.lower() not in ex:
                out.append(w)
                ex.add(w.lower())
            if len(out) == n:
                return out
        raise AssertionError("INSUFFICIENT_FILLERS")

    signatures = []
    for phrase_idx, phrase in enumerate(END_PHRASES):
        for nth_category in (*SPECIAL, "__generic__"):
            nth_word = generic if nth_category == "__generic__" else lower[nth_category]
            for bits in product((False, True), repeat=4):
                memberships = dict(zip(SPECIAL, bits))
                nth_values = (memberships[nth_category],) if nth_category in memberships else (False, True)
                for nth_forbidden in nth_values:
                    required = [lower[w] for w in SPECIAL if memberships[w]]
                    if nth_forbidden and nth_word.lower() not in {x.lower() for x in required}:
                        required.append(nth_word)
                    if len(required) > 5:
                        raise AssertionError("LEXICAL_SIGNATURE_CARDINALITY_OVERFLOW")
                    forbidden = list(required)
                    forbidden += fillers(
                        set(forbidden) | {nth_word} if not nth_forbidden else set(forbidden),
                        5 - len(forbidden),
                    )
                    assert len(forbidden) == 5 and len({x.lower() for x in forbidden}) == 5
                    for w in SPECIAL:
                        assert ((lower[w].lower() in {x.lower() for x in forbidden}) == memberships[w])
                    assert ((nth_word.lower() in {x.lower() for x in forbidden}) == nth_forbidden)
                    signatures.append({
                        "phrase_idx": phrase_idx,
                        "end_phrase": phrase,
                        "nth_category": nth_category,
                        "nth_word": nth_word,
                        "forbidden": forbidden,
                        "bits": memberships,
                        "nth_forbidden": nth_forbidden,
                    })
    assert len(signatures) == 192

    def build(ids, sig, profile):
        p = PROFILES[profile]
        out = []
        for iid in ids:
            if iid == comp.EXIST:
                out.append(contract(iid, keywords=list(existence)))
            elif iid == comp.FORBIDDEN:
                out.append(contract(iid, forbidden_words=list(sig["forbidden"])))
            elif iid == comp.PARAGRAPHS:
                out.append(contract(iid, num_paragraphs=p["paragraphs"]))
            elif iid == comp.WORDS:
                out.append(contract(iid, num_words=p["word_n"], relation=p["word_rel"]))
            elif iid == comp.SENTENCES:
                out.append(contract(iid, num_sentences=p["sent_n"], relation=p["sent_rel"]))
            elif iid == comp.NTH:
                out.append(contract(
                    iid,
                    num_paragraphs=p["nth_n"],
                    nth_paragraph=p["nth_k"],
                    first_word=sig["nth_word"],
                ))
            elif iid == comp.POSTSCRIPT:
                out.append(contract(iid, postscript_marker=p["post"]))
            elif iid == comp.BULLETS:
                out.append(contract(iid, num_bullets=p["bullets"]))
            elif iid == comp.TITLE:
                out.append(contract(iid))
            elif iid == comp.SECTIONS:
                out.append(contract(
                    iid,
                    section_spliter=p["splitter"],
                    num_sections=p["sections"],
                ))
            elif iid == comp.JSON_ID:
                out.append(contract(iid))
            elif iid == comp.REPEAT:
                out.append(contract(
                    iid,
                    prompt_to_repeat="Public generated request with arbitrary article payload.",
                ))
            elif iid == comp.TWO:
                out.append(contract(iid))
            elif iid == comp.END:
                out.append(contract(iid, end_phrase=sig["end_phrase"]))
            elif iid == comp.QUOTE:
                out.append(contract(iid))
            else:
                raise AssertionError("UNKNOWN_ACTIVE15_ID:" + iid)
        return out

    def exact_follow(c, response):
        iid = c["instruction_id"]
        checker = instructions_registry.INSTRUCTION_DICT[iid](iid)
        checker.build_description(**dict(c.get("slots") or {}))
        return bool(response.strip()) and bool(checker.check_following(response))

    all_sets = arch.enumerate_compatible_sets()
    assert len(all_sets) == 928

    counts = Counter()
    score_hist = Counter()
    sacrifice_hist = Counter()
    failures = []

    for profile in PROFILES:
        for set_index, ids in enumerate(all_sets):
            for sig_index, sig in enumerate(signatures):
                contracts = build(ids, sig, profile)
                plan = opt.solve_contracts(contracts)
                counts["cases"] += 1
                counts["profile_" + profile] += 1
                if plan.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
                    failures.append({
                        "profile": profile,
                        "set_index": set_index,
                        "sig_index": sig_index,
                        "kind": "planner_fail_closed",
                        "ids": list(ids),
                        "plan": plan,
                    })
                    if len(failures) >= 20:
                        break
                    continue

                response = str(plan["response"])
                flags = [exact_follow(c, response) for c in contracts]
                exact_pass = sum(flags)
                theoretical = int(plan["theoretical_max_pass_count"])
                if exact_pass != theoretical:
                    failures.append({
                        "profile": profile,
                        "set_index": set_index,
                        "sig_index": sig_index,
                        "kind": "exact_pointwise_mismatch",
                        "ids": list(ids),
                        "flags": flags,
                        "exact_pass_count": exact_pass,
                        "theoretical_max_pass_count": theoretical,
                        "sacrificed_instruction_ids": plan.get("sacrificed_instruction_ids"),
                        "hard_unsat_reasons": plan.get("hard_unsat_reasons"),
                        "response": response,
                    })
                    if len(failures) >= 20:
                        break
                else:
                    counts["exact_pointwise_match"] += 1
                    score_hist[f"{exact_pass}/{len(contracts)}"] += 1
                    sacrifice_hist[len(plan.get("sacrificed_instruction_ids") or [])] += 1
            if len(failures) >= 20:
                break
        if len(failures) >= 20:
            break

    expected_cases = len(PROFILES) * 928 * 192
    receipt_path = pathlib.Path("livebench_full_cross_v1_verification.json")
    if failures:
        receipt = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_FULL_CROSS_V1_INDEPENDENT_VERIFICATION",
            "status": "FAIL__EXACT_PINNED_CHECKER_COUNTEREXAMPLE_FOUND",
            "expected_cases": expected_cases,
            "coverage": dict(counts),
            "failure_count_capped": len(failures),
            "failures": failures,
            "terminal_rows_read": 0,
            "terminal_kwargs_read": 0,
            "target_scores_read": 0,
            "acceptance_credit_delta": 0,
        }
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        print(json.dumps(receipt, sort_keys=True))
        return 1

    assert counts["cases"] == expected_cases
    assert counts["exact_pointwise_match"] == expected_cases
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_FULL_CROSS_V1_INDEPENDENT_VERIFICATION",
        "status": "PASS__712704_STRUCTURAL_X_EXACT_LEXICAL_X_BOUNDARY_PROFILE_POINTWISE_MATCHES__ZERO_TERMINAL_ROWS",
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
            "structural_id_sets": 928,
            "exact_reachable_lexical_signatures": 192,
            "boundary_profiles": list(PROFILES),
        },
        "sacrifice_count_histogram": dict(sorted(sacrifice_hist.items())),
        "exact_checker_pass_histogram": dict(sorted(score_hist.items())),
        "meaning": [
            "EVERY_928_CONFLICT_COMPATIBLE_ACTIVE15_ID_SET_WAS_CROSSED_WITH_EVERY_192_REACHABLE_LEXICAL_COLLISION_SIGNATURE",
            "FOUR_NUMERIC_STRUCTURAL_BOUNDARY_PROFILES_INCLUDE_WORD_LT100__WORD_GE500__SENTENCE_LT2__SENTENCE_GE20__AND_INTRINSIC_SENTENCE_LT1",
            "EVERY_RESULT_WAS_POSTVALIDATED_WITH_THE_EXACT_PINNED_LIVEBENCH_CHECKERS",
            "THE_POINTWISE_PLANNER_ATTAINED_ITS_THEORETICAL_MAXIMUM_ON_EVERY_CROSS_CASE",
        ],
        "hard_nonclaims": [
            "THIS_RECEIPT_DOES_NOT_BY_ITSELF_PROVE_PARAMETRIC_EQUIVALENCE_OF_EVERY_INTERMEDIATE_NUMERIC_THRESHOLD",
            "THIS_RECEIPT_DOES_NOT_BY_ITSELF_BIND_THE_ACCEPTED_LIVEBENCH_PREDICATE_SCOPE_TO_ACTIVE15",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_RECEIPT_ALONE",
        ],
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
