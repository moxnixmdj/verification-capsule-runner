#!/usr/bin/env python3
"""Fail-closed postprocessor for formal constraints around a real semantic seed.

A PASS has one mechanically checkable preservation invariant: the original
semantic seed occurs verbatim as one contiguous substring of the emitted
response. The postprocessor may add explicitly requested literal wrappers, but
it never rewrites, deletes, truncates, case-folds, or substitutes seed bytes.
Any constraint that requires such a mutation fails closed.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from canonical.runtime import instruction_constraint_compiler_v1 as compiler

SCHEMA = "PROJECT_BRAIN_SEED_PRESERVING_INSTRUCTION_POSTPROCESSOR_V1"
PRESERVATION_CONTRACT = (
    "ANY_PASS_RESPONSE_CONTAINS_THE_ORIGINAL_SEMANTIC_SEED_VERBATIM_"
    "AS_ONE_CONTIGUOUS_SUBSTRING"
)


def _result(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "model_dependency_count": 0,
        "network_used": False,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "seed_preservation_contract": PRESERVATION_CONTRACT,
        **extra,
    }


def transform(seed: str, instruction: str) -> dict[str, Any]:
    seed = str(seed or "")
    instruction = str(instruction or "").strip()
    if not seed:
        return _result("FAIL_CLOSED", error="SEMANTIC_SEED_REQUIRED")
    if not instruction:
        return _result("FAIL_CLOSED", error="INSTRUCTION_REQUIRED")

    try:
        constraints = compiler.compile_constraints(instruction)
    except Exception as exc:
        return _result(
            "FAIL_CLOSED",
            error="CONSTRAINT_COMPILE_FAILED:" + type(exc).__name__,
        )

    if constraints.exact_response is not None and constraints.exact_response != seed:
        return _result(
            "FAIL_CLOSED",
            error="EXACT_RESPONSE_CONFLICTS_WITH_SEED_PRESERVATION",
            constraints=asdict(constraints),
            response=None,
            seed_verbatim_preserved=False,
        )

    candidate = seed
    applied: list[str] = []

    if constraints.prefix is not None and not candidate.startswith(constraints.prefix):
        candidate = constraints.prefix + candidate
        applied.append("PREFIX")
    if constraints.suffix is not None and not candidate.endswith(constraints.suffix):
        candidate = candidate + constraints.suffix
        applied.append("SUFFIX")

    ok, errors = compiler.validate_response(candidate, constraints)
    if not ok:
        return _result(
            "FAIL_CLOSED",
            error="SEED_MUTATION_OR_UNSUPPORTED_TRANSFORMATION_REQUIRED",
            validation_errors=errors,
            applied_transforms=applied,
            constraints=asdict(constraints),
            response=None,
            seed_verbatim_preserved=(seed in candidate),
        )

    if seed not in candidate:
        return _result(
            "FAIL_CLOSED",
            error="INTERNAL_SEED_PRESERVATION_INVARIANT_BROKEN",
            applied_transforms=applied,
            constraints=asdict(constraints),
            response=None,
            seed_verbatim_preserved=False,
        )

    return _result(
        "PASS",
        response=candidate,
        applied_transforms=applied,
        constraints=asdict(constraints),
        seed_verbatim_preserved=True,
        exact_postvalidation=True,
        hard_nonclaim=(
            "PASS_PROVES_ONLY_THE_EXISTING_COMPILER_CONSTRAINTS_AND_VERBATIM_SEED_"
            "PRESERVATION; IT_DOES_NOT_PROVE_GENERAL_NATURAL_LANGUAGE_INSTRUCTION_"
            "FOLLOWING_OR_SEMANTIC_EQUIVALENCE_BEYOND_THAT_BYTE_LEVEL_INVARIANT"
        ),
    )


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return transform(
        str(args.get("seed") or args.get("semantic_seed") or ""),
        str(args.get("instruction") or ""),
    )


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("seed")
    ap.add_argument("instruction")
    ns = ap.parse_args()
    print(json.dumps(transform(ns.seed, ns.instruction), indent=2, sort_keys=True))
