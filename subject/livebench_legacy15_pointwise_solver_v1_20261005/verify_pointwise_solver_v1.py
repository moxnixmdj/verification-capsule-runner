#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from collections import Counter

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_exact_contract_checker_v1 as exact
from canonical.runtime import livebench_legacy15_pointwise_solver_v1 as solver
from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler

BRAIN_SNAPSHOT = "6bd4e7cd9e3f8e35ddf1246e70c78ccff765dd8d"
EXPECTED_BLOBS = {
    "livebench_frozen_active_legacy15_v1.py": "34440ee69322e9d519cbe656cb03c55683a8b9c6",
    "livebench_legacy15_composition_archetypes_v1.py": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "livebench_legacy15_composition_partition_v1.py": "b817b4f63f4e98c2705f221c7a4abd8e571f9d80",
    "livebench_legacy_visible_constraint_compiler_v1.py": "34f4df9f0bd265fc555686bd251a264e446d4c04",
    "livebench_legacy_visible_constraint_compiler_v4.py": "721207ba39d502e3f610289578e9d5bab78b1fcc",
    "livebench_legacy15_slot_feasibility_v1.py": "a0885303a9c7088c4eb6f0510963069e35750f02",
    "livebench_legacy15_joint_candidate_generator_v1.py": "b6ace46a0887321c4c8c8354d88169be1fdbf582",
    "livebench_legacy15_relaxed_candidate_search_v1.py": "9c712ee221021fabe2467cadc241312f50f6c712",
    "livebench_pointwise_optimality_certificate_v1.py": "f0e1faae5b5d1a90a1184fe6cca409591acbbb27",
    "livebench_legacy15_pointwise_certificate_v1.py": "b8f9d0c9a0b0c9f78769cb9534ee4e2c61481fd8",
    "livebench_legacy15_pointwise_search_v1.py": "360d2c24b786ebb98c805e8d54e645a08939f201",
    "livebench_legacy15_exact_contract_checker_v1.py": "d9fdc2f1faa629cea99eb8e51b82bae8f71f6672",
    "livebench_legacy15_pointwise_solver_v1.py": "5b111625d88562247ea20dd11f136b7e14b75ba9",
}
REPEAT_MARKER = (
    "First repeat the request word for word without change,"
    " then give your answer (1. do not say any words or characters"
    " before repeating the request; 2. the request you need to repeat"
    " does not include this sentence)"
)
BASE_PREFIX = (
    "The following are the beginning sentences of a news article from the Guardian.\n"
    "-------\n"
    "A public synthetic article body deliberately contains ordinary prose only.\n"
    "-------\n"
    "Please summarize based on the sentences provided."
)
PROFILE = {
    "existence": ["rock", "section", "signal", "world", "brain"],
    "forbidden": ["rock", "section", "can", "other", "help"],
    "paragraphs": 2,
    "words": (100, "less than"),
    "sentences": (1, "less than"),
    "nth": (2, 1, "rock"),
    "postscript": "P.S.",
    "bullets": 3,
    "sections": ("Section", 3),
    "end": "Is there anything else I can help with?",
}


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def kwargs_for(iid: str, p: dict) -> dict:
    if iid == "keywords:existence":
        return {"keywords": list(p["existence"])}
    if iid == "keywords:forbidden_words":
        return {"forbidden_words": list(p["forbidden"])}
    if iid == "length_constraints:number_paragraphs":
        return {"num_paragraphs": int(p["paragraphs"])}
    if iid == "length_constraints:number_words":
        n, relation = p["words"]
        return {"num_words": int(n), "relation": str(relation)}
    if iid == "length_constraints:number_sentences":
        n, relation = p["sentences"]
        return {"num_sentences": int(n), "relation": str(relation)}
    if iid == "length_constraints:nth_paragraph_first_word":
        n, nth, first = p["nth"]
        return {
            "num_paragraphs": int(n),
            "nth_paragraph": int(nth),
            "first_word": str(first),
        }
    if iid == "detectable_content:postscript":
        return {"postscript_marker": str(p["postscript"])}
    if iid == "detectable_format:number_bullet_lists":
        return {"num_bullets": int(p["bullets"])}
    if iid == "detectable_format:multiple_sections":
        splitter, n = p["sections"]
        return {"section_spliter": str(splitter), "num_sections": int(n)}
    if iid == "startend:end_checker":
        return {"end_phrase": str(p["end"])}
    if iid in {
        "detectable_format:title",
        "detectable_format:json_format",
        "combination:two_responses",
        "combination:repeat_prompt",
        "startend:quotation",
    }:
        return {}
    raise KeyError(iid)


def render_prompt(ids, registry, p=PROFILE):
    descriptions = []
    oracle = []
    for iid in ids:
        inst = registry.INSTRUCTION_DICT[iid](iid)
        kw = kwargs_for(iid, p)
        if iid == "combination:repeat_prompt":
            desc = inst.build_description()
        else:
            desc = inst.build_description(**kw)
        descriptions.append(desc)
        oracle.append({"instruction_id": iid, "slots": dict(kw)})

    prompt = BASE_PREFIX + " " + " ".join(descriptions)
    if "combination:repeat_prompt" in ids:
        prefix = prompt.split(REPEAT_MARKER, 1)[0].strip()
        for row in oracle:
            if row["instruction_id"] == "combination:repeat_prompt":
                row["slots"]["prompt_to_repeat"] = prefix
    return prompt, oracle


def canonical_contracts(rows):
    return sorted(
        [
            {
                "instruction_id": str(x["instruction_id"]),
                "slots": dict(x.get("slots") or {}),
            }
            for x in rows
        ],
        key=lambda x: x["instruction_id"],
    )


def run(livebench_root: Path) -> dict:
    here = Path(__file__).resolve().parent / "canonical" / "runtime"
    source_mismatches = {}
    for name, expected in EXPECTED_BLOBS.items():
        actual = blob_sha(here / name)
        if actual != expected:
            source_mismatches[name] = {"expected": expected, "actual": actual}
    if source_mismatches:
        return {
            "status": "FAIL_CLOSED__BRAIN_SUBJECT_BLOB_DRIFT",
            "brain_snapshot": BRAIN_SNAPSHOT,
            "source_mismatches": source_mismatches,
        }

    binding = exact.verify_pinned_source(livebench_root)
    registry = exact.load_pinned_registry(livebench_root)
    sets = archetypes.enumerate_compatible_sets()
    assert len(sets) == 928

    counters = Counter()
    by_archetype = {}
    failures = []
    for ids in sets:
        prompt, oracle = render_prompt(ids, registry)
        compiled = compiler.compile_visible_constraints(prompt)
        got = canonical_contracts(compiled.get("constraints") or [])
        want = canonical_contracts(oracle)
        if compiled.get("status") != "PASS" or got != want:
            counters["compiler_mismatch"] += 1
            if len(failures) < 80:
                failures.append({
                    "ids": list(ids),
                    "stage": "compiler",
                    "compiler_status": compiled.get("status"),
                    "got": got,
                    "want": want,
                })
            continue

        out = solver.solve_prompt(
            prompt,
            livebench_root,
            max_per_subset=4,
            max_total=128,
        )
        if out.get("status") != "PASS__POINTWISE_OPTIMAL_RESPONSE_CERTIFIED":
            counters["solver_fail"] += 1
            if len(failures) < 80:
                failures.append({
                    "ids": list(ids),
                    "stage": "solver",
                    "error": out.get("error"),
                    "search_status": (out.get("search") or {}).get("status"),
                    "unresolved": ((out.get("search") or {}).get("certificate") or {}).get("unresolved_subset_indices"),
                })
            continue

        response = str(out["response"])
        flags = exact.evaluate_exact(response, compiled["constraints"], livebench_root)
        recorded = tuple(bool(x) for x in out["search"]["best_candidate"]["checker_results"])
        if flags != recorded:
            counters["checker_vector_mismatch"] += 1
            if len(failures) < 80:
                failures.append({
                    "ids": list(ids),
                    "stage": "checker_vector",
                    "exact": list(flags),
                    "recorded": list(recorded),
                })
            continue
        if out.get("pointwise_optimal") is not True:
            counters["uncertified"] += 1
            continue

        counters["pass"] += 1
        counters["full_score" if all(flags) else "certified_partial_optimum"] += 1
        arch = archetypes.archetype(ids)
        by_archetype.setdefault(arch, Counter())
        by_archetype[arch]["pass"] += 1
        by_archetype[arch]["full_score" if all(flags) else "certified_partial_optimum"] += 1

    total = len(sets)
    passed = counters["pass"]
    status = (
        "PASS__ALL_928_ADVERSARIAL_PUBLIC_DOMAIN_SHAPES_POINTWISE_CERTIFIED"
        if passed == total
        else "FAIL_CLOSED__POINTWISE_REPAIR_LEDGER_EMITTED"
    )
    return {
        "schema": "PROJECT_BRAIN_LIVEBENCH_POINTWISE_SOLVER_PUBLIC_AUDIT_V1",
        "status": status,
        "brain_snapshot": BRAIN_SNAPSHOT,
        "pinned_source_binding": binding,
        "scope": {
            "compatible_identity_sets": total,
            "parameter_profile_count": 1,
            "profile": PROFILE,
            "terminal_rows_read": 0,
            "terminal_prompts_read": 0,
            "terminal_scores_read": 0,
        },
        "counters": dict(counters),
        "by_archetype": {k: dict(v) for k, v in sorted(by_archetype.items())},
        "failures": failures,
        "hard_nonclaims": [
            "SYNTHETIC_PUBLIC_DOMAIN_EVIDENCE_ONLY",
            "NO_ACTIVE_TERMINAL_ROW_CONTENT_READ",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()
    result = run(Path(ns.livebench_root).resolve())
    Path(ns.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": result["status"],
        "counters": result.get("counters"),
        "failure_count": len(result.get("failures") or []),
    }, sort_keys=True))
    return 0 if result["status"].startswith("PASS__") else 1


if __name__ == "__main__":
    raise SystemExit(main())
