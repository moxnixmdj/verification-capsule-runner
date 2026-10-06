#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "livebench_language_decorator_20261005"
OUT = ROOT / "livebench_language_decorator_neutrality_receipt.json"

EXPECTED = {
    "canonical/governance/LIVEBENCH_LANGUAGE_DECORATOR_NEUTRALITY_PRECOMMIT_20261005_V1.json":
        "6b0a8a3a3e2ddb5ded0c5e2b63c9273c038755ab",
    "canonical/runtime/livebench_union25_semantic_kernel_reduction_v1.py":
        "c08812986e1224bcbb910dfff3bc112f57453996",
    "canonical/runtime/livebench_union25_archetypes_v1.py":
        "8c68e63bbc1e1b843f076dbcd8c4bfae11d4cc2a",
    "canonical/runtime/livebench_legacy25_single_contract_witness_v1.py":
        "e927c05071bb4342b41fb9d5be07cc32ea82e820",
}
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
DECORATORS = ("[]", "*-*")
REPETITIONS = (1, 4)
SEEDS = tuple(range(256))


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def literal_assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError("ASSIGNMENT_NOT_FOUND:" + name)


def infix(base: str, decoration: str) -> str:
    words = base.split()
    if len(words) < 2:
        return base + " " + decoration
    cut = len(words) // 2
    return " ".join(words[:cut] + [decoration] + words[cut:])


def decorated(base: str, kind: str, repetition: int, placement: str) -> str:
    if kind == "BOTH":
        unit = " ".join(DECORATORS)
    else:
        unit = kind
    decoration = " ".join([unit] * repetition)
    if placement == "PREFIX":
        return decoration + " " + base
    if placement == "INFIX":
        return infix(base, decoration)
    if placement == "SUFFIX":
        return base + " " + decoration
    raise AssertionError("UNKNOWN_PLACEMENT")


def bind_livebench():
    root = Path("/tmp/livebench")
    import subprocess
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    assert head == LIVEBENCH_COMMIT, head
    ipath = root / "livebench/if_runner/instruction_following_eval/instructions.py"
    upath = root / "livebench/if_runner/instruction_following_eval/instructions_util.py"
    assert blob_sha(ipath) == INSTRUCTIONS_BLOB
    assert blob_sha(upath) == UTIL_BLOB
    sys.path.insert(0, str(root / "livebench/if_runner"))
    from instruction_following_eval import instructions
    return instructions


def checker_pass(instructions, code: str, text: str) -> bool:
    c = instructions.ResponseLanguageChecker("language:response_language")
    c.build_description(language=code)
    return bool(c.check_following(text))


def main() -> int:
    observed = {}
    for rel, expected in EXPECTED.items():
        got = blob_sha(SUBJECT / rel)
        assert got == expected, (rel, got, expected)
        observed[rel] = got

    import langdetect
    from langdetect.detector_factory import DetectorFactory
    try:
        from importlib.metadata import version
        assert version("langdetect") == "1.0.9"
    except Exception:
        raise

    witness_path = SUBJECT / "canonical/runtime/livebench_legacy25_single_contract_witness_v1.py"
    samples = literal_assignment(witness_path, "LANGUAGE_SAMPLES")
    assert isinstance(samples, dict) and len(samples) == 30
    assert len(set(samples)) == 30

    sys.path.insert(0, str(SUBJECT))
    from canonical.runtime import livebench_union25_semantic_kernel_reduction_v1 as reduction
    reduced = reduction.verify()
    assert reduced["proven_reduction_without_language_assumption"]["semantic_kernel_count"] == 64
    assert reduced["conditional_reduction_after_language_neutrality_gate"]["semantic_kernel_count"] == 41
    assert reduced["conditional_reduction_after_language_neutrality_gate"]["hard_kernel_count"] == 39

    instructions = bind_livebench()

    failures = []
    default_cases = 0
    # Frozen precommit gate on the runtime's ordinary default behavior.
    DetectorFactory.seed = None
    for code, base in sorted(samples.items()):
        if not checker_pass(instructions, code, base):
            failures.append({"kind":"BASE_DEFAULT","code":code})
        for rep in REPETITIONS:
            for kind in (*DECORATORS, "BOTH"):
                for placement in ("PREFIX","INFIX","SUFFIX"):
                    text = decorated(base, kind, rep, placement)
                    default_cases += 1
                    if not checker_pass(instructions, code, text):
                        failures.append({
                            "kind":"DECORATED_DEFAULT","code":code,
                            "decorator":kind,"repetition":rep,"placement":placement,
                        })

    # Stronger falsifier than the precommit requires: sweep 256 deterministic
    # detector seeds. This does not claim mathematical exhaustion of Python RNG
    # seed space; it is explicitly a robustness attack against hidden stochasticity.
    seed_cases = 0
    seed_failures = []
    for seed in SEEDS:
        DetectorFactory.seed = seed
        for code, base in sorted(samples.items()):
            if not checker_pass(instructions, code, base):
                seed_failures.append({"seed":seed,"code":code,"kind":"BASE"})
            for rep in REPETITIONS:
                for kind in (*DECORATORS, "BOTH"):
                    for placement in ("PREFIX","INFIX","SUFFIX"):
                        seed_cases += 1
                        text = decorated(base, kind, rep, placement)
                        if not checker_pass(instructions, code, text):
                            seed_failures.append({
                                "seed":seed,"code":code,"kind":"DECORATED",
                                "decorator":kind,"repetition":rep,"placement":placement,
                            })
                            if len(seed_failures) >= 100:
                                break
                    if len(seed_failures) >= 100: break
                if len(seed_failures) >= 100: break
            if len(seed_failures) >= 100: break
        if len(seed_failures) >= 100: break

    precommit_pass = not failures
    stress_pass = not seed_failures
    status = (
        "PASS__FROZEN_LANGUAGE_DECORATOR_GATE__256_SEED_STRESS_PASS__41_KERNEL_REDUCTION_ADMISSIBLE_UNDER_FROZEN_GATE"
        if precommit_pass and stress_pass
        else "FAIL_CLOSED__LANGUAGE_DECORATOR_COUNTEREXAMPLE"
    )

    receipt = {
        "schema":"PROJECT_BRAIN_LIVEBENCH_LANGUAGE_DECORATOR_NEUTRALITY_INDEPENDENT_VERIFICATION_V1",
        "status":status,
        "subject_blobs":observed,
        "pinned_livebench_commit":LIVEBENCH_COMMIT,
        "langdetect_version":"1.0.9",
        "language_count":len(samples),
        "frozen_default_gate":{
            "decorated_cases":default_cases,
            "failures":failures[:100],
            "pass":precommit_pass,
        },
        "stronger_rng_robustness_falsifier":{
            "seed_count":len(SEEDS),
            "configured_seeds":[SEEDS[0],SEEDS[-1]],
            "decorated_cases_attempted":seed_cases,
            "failures":seed_failures[:100],
            "pass":stress_pass,
            "hard_nonclaim":"256_SEEDS_IS_A_STRONG_FINITE_FALSIFIER_NOT_A_PROOF_OVER_ALL_POSSIBLE_RANDOM_STATES",
        },
        "semantic_reduction_if_frozen_gate_passes":{
            "before":64,
            "after":41,
            "hard_kernels_after":39,
        },
        "terminal_rows_read":0,
        "hidden_kwargs_read":0,
        "target_responses_read":0,
        "target_scores_read":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
    }
    OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":status,
        "default_cases":default_cases,
        "seed_cases":seed_cases,
        "default_failures":len(failures),
        "seed_failures":len(seed_failures),
    },sort_keys=True))
    return 0 if status.startswith("PASS__") else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        failure={
            "schema":"PROJECT_BRAIN_LIVEBENCH_LANGUAGE_DECORATOR_NEUTRALITY_INDEPENDENT_VERIFICATION_V1",
            "status":"FAIL_CLOSED__VERIFIER_EXCEPTION",
            "exception_type":type(exc).__name__,
            "exception":str(exc),
            "traceback":traceback.format_exc(),
            "acceptance_credit_delta":0,
        }
        OUT.write_text(json.dumps(failure,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps(failure,sort_keys=True))
        raise
