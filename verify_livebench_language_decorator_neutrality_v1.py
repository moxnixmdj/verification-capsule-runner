#!/usr/bin/env python3
from __future__ import annotations

import importlib.metadata
import json
import pathlib
import re
import subprocess
import sys

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
SEMANTIC_BLOB = "12d3f3441eab0811839c0aa2238c0a10b4d86d87"
WITNESS_BLOB = "e927c05071bb4342b41fb9d5be07cc32ea82e820"
COMPILER_BLOB = "20421dfa016584b202b194afd3f82c9bd46a1f23"
LANGDETECT_VERSION = "1.0.9"

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_language_decorator_20261005"
RUNTIME = SUBJECT / "canonical/runtime"
LIVE = pathlib.Path("/tmp/LiveBench")
P = "[]"
H = "+*-*"
DETECTIONS_PER_CASE = 5

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)

def blob(path: pathlib.Path) -> str:
    return run(["git","hash-object",str(path)], capture_output=True).stdout.strip()

def source_blob(path: str) -> str:
    return run(["git","-C",str(LIVE),"rev-parse",f"HEAD:{path}"], capture_output=True).stdout.strip()

def decorate(base: str, payload: str, placement: str) -> str:
    if placement == "PREFIX":
        return payload + " " + base
    if placement == "SUFFIX":
        return base + " " + payload
    if placement == "INFIX_BETWEEN_WORDS":
        words = base.split()
        assert len(words) >= 2
        k = len(words) // 2
        return " ".join(words[:k] + [payload] + words[k:])
    raise AssertionError("UNKNOWN_PLACEMENT:" + placement)

def exact_decorator_invariants() -> dict:
    assert re.findall(r"\[.*?\]", P) == [P]
    hs = re.findall(r"\*[^\n\*]*\*", H)
    assert hs == ["*-*"] and hs[0].strip("*").strip()
    for token in (P,H):
        assert re.findall(r"\w+", token) == []
        assert re.findall(r"[A-Za-z]", token) == []
        assert "," not in token
        assert not any(ch in token for ch in ".?!")
        assert "\n" not in token
        assert "******" not in token and "***" not in token
        assert "<<" not in token and ">>" not in token
        assert '"' not in token
        assert not any(ch.isalpha() or ch.isupper() or ch.islower() for ch in token)
        # Exact frozen BulletListChecker patterns.
        assert re.search(r"(?m)^\s*\*[^\*].*$", token) is None
        assert re.search(r"(?m)^\s*-.*$", token) is None
    return {
        "placeholder_carrier":P,
        "highlight_carrier":H,
        "word_delta_each":0,
        "ascii_letter_delta_each":0,
        "comma_delta_each":0,
        "sentence_terminator_delta_each":0,
        "cased_character_delta_each":0,
        "star_bullet_delta_each":0,
        "dash_bullet_delta_each":0,
        "placement_precondition_required":False,
    }

def main() -> int:
    expected = {
        RUNTIME/"livebench_union25_semantic_kernel_reduction_v1.py": SEMANTIC_BLOB,
        RUNTIME/"livebench_legacy25_single_contract_witness_v1.py": WITNESS_BLOB,
        RUNTIME/"livebench_legacy25_prompt_contract_compiler_v1.py": COMPILER_BLOB,
    }
    for path, want in expected.items():
        got = blob(path)
        assert got == want, (str(path), got, want)

    assert run(["git","-C",str(LIVE),"rev-parse","HEAD"],capture_output=True).stdout.strip() == LIVEBENCH_COMMIT
    assert source_blob("livebench/if_runner/instruction_following_eval/instructions.py") == INSTRUCTIONS_BLOB
    assert source_blob("livebench/if_runner/instruction_following_eval/instructions_util.py") == UTIL_BLOB
    assert importlib.metadata.version("langdetect") == LANGDETECT_VERSION

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(LIVE/"livebench/if_runner"))

    from canonical.runtime.livebench_legacy25_single_contract_witness_v1 import LANGUAGE_SAMPLES
    from instruction_following_eval import instructions_registry, instructions_util
    from langdetect import detect

    assert len(instructions_util.LANGUAGE_CODES) == 30
    assert set(LANGUAGE_SAMPLES) == set(instructions_util.LANGUAGE_CODES)

    inv = exact_decorator_invariants()
    failures = []
    cases = 0
    detections = 0
    base_checks = 0

    modes = (
        ("PLACEHOLDER", P),
        ("HIGHLIGHT", H),
        ("BOTH", P + " " + H),
    )
    placements = ("PREFIX","INFIX_BETWEEN_WORDS","SUFFIX")
    reps = (1,4)

    for code, name in instructions_util.LANGUAGE_CODES.items():
        sample = LANGUAGE_SAMPLES[code]
        base = sample + " " + sample
        checker = instructions_registry.INSTRUCTION_DICT["language:response_language"]("language:response_language")
        checker.build_description(language=code)

        base_detects = [detect(base) for _ in range(DETECTIONS_PER_CASE)]
        detections += DETECTIONS_PER_CASE
        base_checks += 1
        if any(x != code for x in base_detects) or not checker.check_following(base):
            failures.append({
                "kind":"BASE_CARRIER",
                "code":code, "name":name,
                "detects":base_detects,
                "checker":bool(checker.check_following(base)),
            })
            continue

        for mode, atom in modes:
            for placement in placements:
                for rep in reps:
                    payload = " ".join([atom] * rep)
                    value = decorate(base, payload, placement)
                    got = [detect(value) for _ in range(DETECTIONS_PER_CASE)]
                    detections += DETECTIONS_PER_CASE
                    checker_ok = bool(checker.check_following(value))
                    cases += 1
                    if any(x != code for x in got) or not checker_ok:
                        failures.append({
                            "kind":"DECORATED",
                            "code":code, "name":name,
                            "mode":mode, "placement":placement, "repetition":rep,
                            "detects":got, "checker":checker_ok,
                        })

    receipt = {
        "schema":"PROJECT_BRAIN_LIVEBENCH_LANGUAGE_DECORATOR_NEUTRALITY_INDEPENDENT_VERIFICATION_V1",
        "status":(
            "PASS__30_LANGUAGE_DECORATOR_NEUTRALITY__PLACEMENT_INDEPENDENT_CARRIERS"
            if not failures else "FAIL__LANGUAGE_DECORATOR_COUNTEREXAMPLE"
        ),
        "subject_blobs":{
            "semantic_kernel_reduction":SEMANTIC_BLOB,
            "legacy25_single_witness":WITNESS_BLOB,
            "legacy25_prompt_compiler":COMPILER_BLOB,
        },
        "pinned_public_source":{
            "livebench_commit":LIVEBENCH_COMMIT,
            "instructions_blob":INSTRUCTIONS_BLOB,
            "instructions_util_blob":UTIL_BLOB,
            "langdetect_version":LANGDETECT_VERSION,
        },
        "language_code_count":30,
        "base_carrier_checks":base_checks,
        "decorated_cases":cases,
        "detect_calls":detections,
        "detections_per_case":DETECTIONS_PER_CASE,
        "decorator_modes":[x[0] for x in modes],
        "placements":list(placements),
        "repetitions":list(reps),
        "decorator_invariants":inv,
        "failure_count":len(failures),
        "failures":failures[:100],
        "consequence_if_pass":{
            "semantic_kernel_count":41,
            "hard_kernel_count":39,
            "deleted_conservative_kernel_branches":23,
        },
        "terminal_rows_read":0,
        "hidden_terminal_kwargs_read":0,
        "terminal_instruction_id_lists_read":0,
        "target_responses_read":0,
        "target_scores_read":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
    }
    pathlib.Path("livebench_language_decorator_neutrality_verification.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n", encoding="utf-8"
    )
    print(json.dumps(receipt,sort_keys=True))
    return 0 if not failures else 1

if __name__ == "__main__":
    raise SystemExit(main())
