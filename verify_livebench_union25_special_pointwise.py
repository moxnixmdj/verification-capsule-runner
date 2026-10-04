#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

EXPECTED_BLOBS = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py": "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py": "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_union25_archetypes_v1.py": "8c68e63bbc1e1b843f076dbcd8c4bfae11d4cc2a",
    "canonical/runtime/livebench_legacy25_prompt_contract_compiler_v1.py": "20421dfa016584b202b194afd3f82c9bd46a1f23",
    "canonical/runtime/livebench_legacy25_single_contract_witness_v1.py": "e927c05071bb4342b41fb9d5be07cc32ea82e820",
    "canonical/runtime/livebench_union25_special_pointwise_v1.py": "ef369554a93871bb34e9a2f6569bd3950b2b0f2a",
}

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT_ROOT = ROOT / "subject/livebench_union25_special_20261005"


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, text=True, **kwargs)


def c(iid, **slots):
    return {"instruction_id": iid, "slots": slots, "parameter_complete": True}


def build(u, ids, *, language="en", language_name="English", comma_repeat=False):
    out = []
    for iid in ids:
        if iid == u.EXIST:
            out.append(c(iid, keywords=["alpha", "beta"]))
        elif iid == u.FORBIDDEN:
            out.append(c(iid, forbidden_words=["gamma", "delta"]))
        elif iid == u.REPEAT:
            prefix = (
                "Write a compact note, please."
                if comma_repeat
                else "Write a compact note."
            )
            out.append(c(iid, prompt_to_repeat=prefix))
        elif iid == u.LANGUAGE:
            out.append(c(iid, language=language, language_name=language_name))
        else:
            out.append(c(iid))
    return out


def exact_flags(registry, response, rows):
    eligible = bool(str(response).strip())
    flags = []
    for row in rows:
        iid = str(row["instruction_id"])
        checker = registry[iid](iid)
        slots = {
            k: v
            for k, v in dict(row.get("slots") or {}).items()
            if k != "language_name"
        }
        checker.build_description(**slots)
        flags.append(eligible and bool(checker.check_following(str(response))))
    return flags


def main() -> int:
    for rel, expected in EXPECTED_BLOBS.items():
        path = SUBJECT_ROOT / rel
        got = run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()
        assert got == expected, (rel, got, expected)

    sys.path.insert(0, str(SUBJECT_ROOT))
    from canonical.runtime import livebench_union25_archetypes_v1 as u
    from canonical.runtime import livebench_union25_special_pointwise_v1 as special

    structural = special.verify_structural_closure()
    assert structural["special_delta_structure_count"] == 17
    assert structural["route_counts"] == {
        "CONSTRAINED_SINGLETON": 1,
        "REPEAT_PROMPT": 4,
        "TWO_RESPONSES": 12,
    }
    assert structural["language_two_structure_count"] == 4

    with tempfile.TemporaryDirectory(prefix="livebench-union25-special-") as td:
        checkout = pathlib.Path(td) / "LiveBench"
        run([
            "git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
            "https://github.com/LiveBench/LiveBench.git", str(checkout),
        ])
        run([
            "git", "-C", str(checkout), "fetch", "--quiet", "--depth=1",
            "origin", LIVEBENCH_COMMIT,
        ])
        run([
            "git", "-C", str(checkout), "checkout", "--quiet", "--detach",
            LIVEBENCH_COMMIT,
        ])

        registry_path = "livebench/if_runner/instruction_following_eval/instructions_registry.py"
        instructions_path = "livebench/if_runner/instruction_following_eval/instructions.py"
        got_registry = run(
            ["git", "-C", str(checkout), "rev-parse", f"HEAD:{registry_path}"],
            capture_output=True,
        ).stdout.strip()
        got_instructions = run(
            ["git", "-C", str(checkout), "rev-parse", f"HEAD:{instructions_path}"],
            capture_output=True,
        ).stdout.strip()
        assert got_registry == REGISTRY_BLOB
        assert got_instructions == INSTRUCTIONS_BLOB

        sys.path.insert(0, str(checkout / "livebench/if_runner"))
        from instruction_following_eval import instructions_registry, instructions_util

        registry = instructions_registry.INSTRUCTION_DICT
        assert len(registry) == 25
        assert set(registry) == set(u.ALL_IDS)
        assert len(instructions_util.LANGUAGE_CODES) == 30

        structures = special.enumerate_extra_special_structures()
        assert len(structures) == 17

        nonlanguage_full = []
        repeat_collision = []
        language_cases = []

        for ids in structures:
            if u.LANGUAGE in ids:
                continue
            rows = build(u, ids)
            plan = special.solve_special(rows)
            assert plan["status"] == "CANDIDATE_POINTWISE_OPTIMAL_SPECIAL_DELTA", (ids, plan)
            flags = exact_flags(registry, plan["response"], rows)
            assert sum(flags) == len(ids), (ids, plan, flags)
            nonlanguage_full.append({
                "ids": list(ids),
                "pass_count": sum(flags),
                "checker_count": len(flags),
            })

            if u.REPEAT in ids:
                rows = build(u, ids, comma_repeat=True)
                plan = special.solve_special(rows)
                assert plan["status"] == "CANDIDATE_POINTWISE_OPTIMAL_SPECIAL_DELTA"
                flags = exact_flags(registry, plan["response"], rows)
                assert sum(flags) == len(ids) - 1, (ids, plan, flags)
                row_ids = [r["instruction_id"] for r in rows]
                assert flags[row_ids.index(u.REPEAT)] is False
                assert flags[row_ids.index(u.NO_COMMA)] is True
                repeat_collision.append({
                    "ids": list(ids),
                    "pass_count": sum(flags),
                    "checker_count": len(flags),
                    "proved_upper_bound": len(ids) - 1,
                })

        language_structures = [
            ids for ids in structures if u.TWO in ids and u.LANGUAGE in ids
        ]
        assert len(language_structures) == 4

        for code, name in instructions_util.LANGUAGE_CODES.items():
            for ids in language_structures:
                rows = build(u, ids, language=code, language_name=name)
                plan = special.solve_special(rows)
                assert plan["status"] == "CANDIDATE_POINTWISE_OPTIMAL_SPECIAL_DELTA", (
                    ids, code, plan
                )
                flags = exact_flags(registry, plan["response"], rows)
                assert sum(flags) == len(ids), (ids, code, plan, flags)
                language_cases.append({
                    "code": code,
                    "name": name,
                    "ids": list(ids),
                    "pass_count": sum(flags),
                    "checker_count": len(flags),
                    "comma_free": "," not in plan["response"],
                })

        assert len(nonlanguage_full) == 13
        assert len(repeat_collision) == 4
        assert len(language_cases) == 120

        receipt = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_UNION25_SPECIAL_POINTWISE_INDEPENDENT_VERIFICATION_V1",
            "status": "PASS__17_OF_17_EXTRA_SPECIAL_STRUCTURES_POINTWISE_CLOSED__120_OF_120_LANGUAGE_TWO_CASES_EXACT",
            "pinned_livebench_commit": LIVEBENCH_COMMIT,
            "registry_blob": REGISTRY_BLOB,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "subject_blobs": EXPECTED_BLOBS,
            "verified": {
                "union25_extra_bearing_structures": 13631,
                "special_delta_structure_count": 17,
                "nonlanguage_special_full_score_structures": len(nonlanguage_full),
                "repeat_no_comma_comma_prefix_exact_one_loss_structures": len(repeat_collision),
                "language_two_structures": len(language_structures),
                "language_codes": len(instructions_util.LANGUAGE_CODES),
                "language_two_exact_cases": len(language_cases),
                "language_two_exact_full_score_cases": sum(
                    1 for x in language_cases if x["pass_count"] == x["checker_count"]
                ),
                "remaining_general_extra_structures": 13614,
            },
            "proof_notes": [
                "CONSTRAINED_RESPONSE_IS_CONFLICT_GRAPH_SINGLETON",
                "REPEAT_PLUS_NO_COMMA_HAS_EXACT_ONE_LOSS_IFF_VISIBLE_MANDATORY_REPEAT_PREFIX_CONTAINS_COMMA",
                "ACTIVE15_TWO_RESPONSE_CONSTRUCTOR_PRESERVES_NO_COMMA",
                "TWO_PLUS_LANGUAGE_OPTIONALLY_TITLE_AND_NO_COMMA_PASSES_EXACT_FROZEN_CHECKERS_FOR_ALL_30_PINNED_LANGUAGE_CODES",
            ],
            "hard_nonclaims": [
                "GENERAL_ROUTE_EXTRA10_POINTWISE_OPTIMALITY_NOT_YET_PROVED",
                "UNION25_POINTWISE_OPTIMALITY_NOT_YET_PROVED",
                "NO_LIVEBENCH_ACCEPTANCE_OR_OWNERSHIP_CREDIT_FROM_THIS_RECEIPT_ALONE",
            ],
            "terminal_rows_read": 0,
            "hidden_instruction_id_lists_read": 0,
            "hidden_kwargs_read": 0,
            "target_scores_read": 0,
            "semantic_capability_credit": False,
            "acceptance_credit_delta": 0,
            "nonlanguage_receipts": nonlanguage_full,
            "repeat_collision_receipts": repeat_collision,
            "language_receipts": language_cases,
        }
        pathlib.Path("livebench_union25_special_pointwise_verification.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "status": receipt["status"],
            **receipt["verified"],
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
