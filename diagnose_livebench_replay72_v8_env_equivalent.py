#!/usr/bin/env python3
from __future__ import annotations

import collections
import concurrent.futures
import json
import os
import pathlib
import re
import sys
import tempfile

import diagnose_livebench_replay72_v7_sanitized as v7

EXPECTED_V7_DIAGNOSTIC_BLOB = "e9a5a5937b19e76bf04444c288e3a75113874ed7"
EXPECTED_CLASSIFIER_BLOB = "44df7313c83914204299953dda81900fae85ab68"
EXPECTED_BASE_EXECUTOR_BLOB = "2a57ce896ddbd6819246aab8b44d17a00f36b61e"
REPLAY_LIMIT = 72


def _same_blob(path: pathlib.Path, expected: str) -> None:
    got = v7.git_blob_sha(path)
    if got != expected:
        raise RuntimeError(f"BLOB_DRIFT:{path.name}:{got}:{expected}")


def prepare_v6_equivalent_precase(base: pathlib.Path, mod):
    # Exact environment preparation performed by the V6 executor before any
    # terminal dataset read. This is deliberately duplicated in order, not
    # approximated.
    mod.install_scorer_deps()
    mod.prepare_nltk(base)
    lb = mod.clone_livebench(base)

    sys.path.insert(0, str(lb / "livebench/if_runner"))
    from instruction_following_eval import evaluation_main as legacy_eval
    sys.path.insert(0, str(lb))
    from livebench.if_runner.ifbench import evaluation_lib as ifbench_eval

    legacy_synth = legacy_eval.InputExample(
        key=0,
        instruction_id_list=["punctuation:no_comma"],
        prompt="synthetic legacy prompt",
        kwargs=[{}],
    )
    legacy_out = legacy_eval.test_instruction_following_strict(
        legacy_synth, {"synthetic legacy prompt": "hello world"}
    )
    if legacy_out.follow_all_instructions is not True:
        raise SystemExit("FAIL_CLOSED:SYNTHETIC_LEGACY_SCORER_SMOKE")

    modern_synth = ifbench_eval.InputExample(
        key=0,
        instruction_id_list=["format:no_whitespace"],
        prompt="synthetic modern prompt",
        kwargs=[{}],
    )
    modern_out = ifbench_eval.test_instruction_following_strict(
        modern_synth, "helloworld"
    )
    if modern_out.follow_all_instructions is not True:
        raise SystemExit("FAIL_CLOSED:SYNTHETIC_IFBENCH_SCORER_SMOKE")

    return v7.build_diagnostic_template(base, mod)


def main(*, authorized=False, activation_blob=None):
    if authorized is not True:
        raise SystemExit("FAIL_CLOSED:VERIFIED_V8_DIAGNOSTIC_LAUNCHER_REQUIRED")
    if not isinstance(activation_blob, str) or re.fullmatch(r"[0-9a-f]{40}", activation_blob) is None:
        raise SystemExit("FAIL_CLOSED:VERIFIED_V8_ACTIVATION_BLOB_REQUIRED")
    if os.environ.get("GITHUB_ACTIONS") != "true" or str(os.environ.get("REPOSITORY_PRIVATE", "")).lower() != "false":
        raise SystemExit("FAIL_CLOSED:PUBLIC_STANDARD_GITHUB_RUNNER_REQUIRED")
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("FAIL_CLOSED:PYTHON_3_12_REQUIRED")

    _same_blob(v7.ROOT / "diagnose_livebench_replay72_v7_sanitized.py", EXPECTED_V7_DIAGNOSTIC_BLOB)
    _same_blob(v7.ROOT / "livebench_v7_sanitized_classifier.py", EXPECTED_CLASSIFIER_BLOB)
    _same_blob(v7.ROOT / "execute_livebench_if_replay72_v4_candidate.py", EXPECTED_BASE_EXECUTOR_BLOB)

    mod = v7.load_base()
    if mod.REPLAY_LIMIT != REPLAY_LIMIT:
        raise SystemExit("FAIL_CLOSED:REPLAY_LIMIT_DRIFT")

    with tempfile.TemporaryDirectory(prefix="lb-v8-diagnostic-") as td:
        base = pathlib.Path(td)

        # This closes the V7 revocation reason before any terminal data read.
        template = prepare_v6_equivalent_precase(base, mod)

        # Synthetic inference classification remains pre-exposure.
        synthetic = {
            "question_id": "SYNTHETIC_ZERO_CASE",
            "turns": ["Reply with exactly SYNTHETIC_OK."],
        }
        synth = v7.classify_one(template, synthetic, mod.BENCHMARK_ID)
        if not (
            synth == "VALID_RESPONSE"
            or synth.startswith("STATIC_BLOCKER:")
            or synth.startswith("STATIC_ADAPTER_BLOCKER:")
            or synth.startswith("POLICY_BLOCK:")
        ):
            raise SystemExit("FAIL_CLOSED:V8_SYNTHETIC_CLASSIFIER:" + synth)

        # Only the already-exposed 72-case prefix is read.
        parquet = mod.download_dataset(base)
        questions = mod.parse_population(base, parquet)
        classes = []
        batch = 8
        for start in range(0, REPLAY_LIMIT, batch):
            current = questions[start:start + batch]
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(batch, os.cpu_count() or 2)) as ex:
                classes.extend(ex.map(lambda q: v7.classify_one(template, q, mod.BENCHMARK_ID), current))

        if len(classes) != REPLAY_LIMIT:
            raise RuntimeError("REPLAY_PREFIX_COUNT_MISMATCH")

        hist = dict(sorted(collections.Counter(classes).items()))
        valid = hist.get("VALID_RESPONSE", 0)
        unclassified = sum(v for k, v in hist.items() if k.startswith("UNCLASSIFIED_RUNTIME:"))
        out = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_V8_ENV_EQUIVALENT_SANITIZED_BLOCKER_DIAGNOSTIC_RESULT_V1",
            "status": "DIAGNOSTIC_COMPLETE",
            "benchmark_id": mod.BENCHMARK_ID,
            "activation_blob_sha": activation_blob,
            "base_executor_git_blob_sha": EXPECTED_BASE_EXECUTOR_BLOB,
            "replay_prefix_limit": REPLAY_LIMIT,
            "terminal_cases_consumed": REPLAY_LIMIT,
            "new_case_exposure": False,
            "case_ids_emitted": False,
            "prompt_text_emitted": False,
            "response_text_emitted": False,
            "raw_exception_text_emitted": False,
            "v6_precase_environment_equivalence": True,
            "valid_response_count": valid,
            "unclassified_runtime_count": unclassified,
            "classification_histogram": hist,
            "acceptance_credit_authority": False,
            "promotion_authority": False,
        }
        print("LIVEBENCH_V8_SANITIZED_DIAGNOSTIC=" + json.dumps(out, sort_keys=True), flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit("FAIL_CLOSED:VERIFIED_V8_DIAGNOSTIC_LAUNCHER_REQUIRED")
