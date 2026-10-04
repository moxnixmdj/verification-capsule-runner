#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter
from itertools import product

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_semantic_factorization_v1_20261005"


def contract(iid: str, **slots):
    return {"instruction_id": iid, "slots": slots}


def main() -> int:
    sys.path.insert(0, str(SUBJECT))
    live = pathlib.Path("/tmp/LiveBench")
    sys.path.insert(0, str(live / "livebench/if_runner"))

    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as opt
    from canonical.runtime import livebench_legacy15_semantic_factorization_v1 as proof
    from instruction_following_eval import instructions_registry, instructions_util

    cert = proof.verify(live)
    assert cert["status"].startswith("PASS__SOURCE_BOUND_SEMANTIC_FACTORIZATION")
    assert cert["word_channel"]["conservative_unpadded_general_word_upper_bound"] == 63
    assert cert["projection_counts"] == {
        "structural_identity_sets": 928,
        "lexical_collision_signatures": 192,
        "word_threshold_relation_states": 802,
        "sentence_threshold_relation_states": 40,
        "paragraph_bullet_section_states": 250,
        "nth_postscript_end_states": 60,
    }

    words = list(instructions_util.WORD_LIST)
    assert len(words) == 1525 and len(set(words)) == 1525
    wordset = {w.lower() for w in words}
    assert wordset & {"p", "s"} == set()
    assert wordset & {
        x.lower()
        for phrase in ("Any other questions?", "Is there anything else I can help with?")
        for x in re.findall(r"[A-Za-z]+", phrase)
    } == {"other", "anything", "can", "help"}

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

    safe = fillers({"section", "other", "anything", "can", "help"}, 1)[0]
    required = fillers({"section", "other", "anything", "can", "help", safe}, 5)
    forbidden = fillers(set(required) | {"section", "other", "anything", "can", "help", safe}, 5)

    def exact_follow(c, response: str) -> bool:
        iid = c["instruction_id"]
        checker = instructions_registry.INSTRUCTION_DICT[iid](iid)
        checker.build_description(**dict(c.get("slots") or {}))
        return bool(response.strip()) and bool(checker.check_following(response))

    def exact_all(contracts, response: str):
        return [exact_follow(c, response) for c in contracts]

    carriers = [("plain", [])]
    for p in range(1, 6):
        for k in range(1, p + 1):
            carriers.append((
                f"nth:{p}:{k}",
                [contract(comp.NTH, num_paragraphs=p, nth_paragraph=k, first_word=safe)],
            ))
    carriers += [
        ("bullet_section",
         [contract(comp.BULLETS, num_bullets=5),
          contract(comp.SECTIONS, section_spliter="SECTION", num_sections=5)]),
        ("word_pad_max", [contract(comp.WORDS, num_words=500, relation="at least")]),
        ("word_no_pad", [contract(comp.WORDS, num_words=100, relation="less than")]),
        ("title", [contract(comp.TITLE)]),
        ("lexical_shield",
         [contract(comp.EXIST, keywords=required),
          contract(comp.FORBIDDEN, forbidden_words=forbidden)]),
    ]

    posts = [None, "P.S.", "P.P.S"]
    endings = [None, "Any other questions?", "Is there anything else I can help with?"]
    quotes = [False, True]

    counts = Counter()
    failures = []

    for n in range(1, 21):
        for relation in ("less than", "at least"):
            for carrier_name, carrier in carriers:
                for post, end, quote in product(posts, endings, quotes):
                    contracts = [contract(comp.SENTENCES, num_sentences=n, relation=relation)]
                    contracts.extend(carrier)
                    if post is not None:
                        contracts.append(contract(comp.POSTSCRIPT, postscript_marker=post))
                    if end is not None:
                        contracts.append(contract(comp.END, end_phrase=end))
                    if quote:
                        contracts.append(contract(comp.QUOTE))

                    ids = [c["instruction_id"] for c in contracts]
                    if len(ids) > arch.MAX_GENERATED_INSTRUCTIONS or not arch.compatible(ids):
                        continue

                    counts["sentence_kernel_cases"] += 1
                    name = f"{relation}:{n}:{carrier_name}:{post}:{end}:{quote}"
                    plan = opt.solve_contracts(contracts)
                    if plan.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
                        failures.append({"name": name, "stage": "planner", "got": plan})
                        continue

                    flags = exact_all(contracts, str(plan["response"]))
                    passed = sum(flags)
                    theoretical = int(plan["theoretical_max_pass_count"])
                    if passed != theoretical:
                        failures.append({
                            "name": name,
                            "stage": "exact_max",
                            "ids": ids,
                            "flags": flags,
                            "passed": passed,
                            "theoretical": theoretical,
                            "plan": plan,
                        })
                        continue

                    if not (relation == "less than" and n == 1):
                        built = comp.compose_contracts(contracts)
                        if built.get("status") != "CANDIDATE_WITNESS":
                            failures.append({"name": name, "stage": "compose", "got": built})
                            continue
                        all_flags = exact_all(contracts, str(built["response"]))
                        if not all(all_flags):
                            failures.append({
                                "name": name,
                                "stage": "all_checker_witness",
                                "flags": all_flags,
                                "response": built["response"],
                            })
                            continue
                        counts["sentence_kernel_full_witness"] += 1
                    else:
                        if comp.SENTENCES not in set(plan["sacrificed_instruction_ids"]):
                            failures.append({"name": name, "stage": "lt1_not_sacrificed", "plan": plan})
                            continue
                        counts["sentence_lt1_pointwise"] += 1

                    counts["sentence_kernel_exact_optimum"] += 1

    end1 = "Any other questions?"
    end2 = "Is there anything else I can help with?"
    collision_cases = [
        [
            contract(comp.SENTENCES, num_sentences=1, relation="less than"),
            contract(comp.NTH, num_paragraphs=2, nth_paragraph=1, first_word=safe),
            contract(comp.FORBIDDEN, forbidden_words=[safe] + fillers({safe}, 4)),
        ],
        [
            contract(comp.SENTENCES, num_sentences=1, relation="less than"),
            contract(comp.END, end_phrase=end1),
            contract(comp.FORBIDDEN, forbidden_words=["other"] + fillers({"other"}, 4)),
        ],
        [
            contract(comp.SENTENCES, num_sentences=1, relation="less than"),
            contract(comp.NTH, num_paragraphs=2, nth_paragraph=2, first_word=safe),
            contract(comp.END, end_phrase=end2),
            contract(
                comp.FORBIDDEN,
                forbidden_words=[safe, "anything", "can", "help"]
                + fillers({safe, "anything", "can", "help"}, 1),
            ),
        ],
    ]
    for idx, contracts in enumerate(collision_cases):
        plan = opt.solve_contracts(contracts)
        assert plan["status"] == "CANDIDATE_POINTWISE_OPTIMAL", plan
        sacrificed = set(plan["sacrificed_instruction_ids"])
        assert sacrificed == {comp.SENTENCES, comp.FORBIDDEN}, plan
        flags = exact_all(contracts, str(plan["response"]))
        assert sum(flags) == len(contracts) - 2, (idx, flags, plan)
        counts["combined_unsat_cluster_cases"] += 1
        counts["combined_unsat_cluster_exact_optimum"] += 1

    if failures:
        receipt = {
            "schema": "LIVEBENCH_SEMANTIC_FACTORIZATION_INDEPENDENT_VERIFICATION_V1",
            "status": "FAIL",
            "counts": dict(counts),
            "failure_count": len(failures),
            "failures": failures[:50],
        }
        pathlib.Path("livebench_semantic_factorization_v1_verification.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        )
        raise SystemExit("SEMANTIC_FACTORIZATION_FAILURES:" + str(len(failures)))

    receipt = {
        "schema": "LIVEBENCH_SEMANTIC_FACTORIZATION_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__SEMANTIC_FACTORIZATION_SENTENCE_KERNEL_AND_COMBINED_UNSAT_CLOSED",
        "subject_certificate_status": cert["status"],
        "projection_counts": cert["projection_counts"],
        "word_upper_bound": cert["word_channel"],
        "counts": dict(counts),
        "combined_unsat_mechanisms": [
            "STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE",
            "NTH_OR_END_FORBIDDEN_COLLISION_SHARED_FORBIDDEN_CHECKER",
        ],
        "theorem_supported": (
            "THE_PREVIOUS_12489_STATE_POINTWISE_ENVELOPE_IS_A_COMPLETE_SEMANTIC_"
            "FACTORIZATION_OF_THE_PUBLIC_GENERATOR_ADMITTED_ACTIVE15_SLOT_DOMAIN_"
            "SUBJECT_TO_THE_SOURCE_BOUND_LEMMAS_IN_THE_CERTIFICATE"
        ),
        "pinned_livebench": {
            "commit": LIVEBENCH_COMMIT,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "registry_blob": REGISTRY_BLOB,
            "util_blob": UTIL_BLOB,
            "generator_blob": GENERATOR_BLOB,
        },
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
    }
    pathlib.Path("livebench_semantic_factorization_v1_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
