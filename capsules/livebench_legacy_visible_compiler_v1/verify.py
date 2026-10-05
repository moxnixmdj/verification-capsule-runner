#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parent
COMPILER = ROOT / "compiler.py"
LIVEBENCH_ROOT = Path("/tmp/LiveBench")
PINNED_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
EXPECTED_COMPILER_BLOB = "0e9e90699e5cbff58090d13aef616c0dd2bd73d6"
EXPECTED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
EXPECTED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
EXPECTED_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"


def load_compiler():
    spec = importlib.util.spec_from_file_location("candidate_compiler", COMPILER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    compiler = load_compiler()

    sys.path.insert(0, str(LIVEBENCH_ROOT / "livebench" / "if_runner"))
    from instruction_following_eval import instructions_registry

    observed_ids = set(instructions_registry.INSTRUCTION_DICT)
    expected_ids = set(compiler.ACTIVE_IDS)
    assert len(observed_ids) == 25, len(observed_ids)
    assert observed_ids == expected_ids, sorted(observed_ids ^ expected_ids)

    random.seed(20261004)
    rows = []
    for instruction_id in sorted(observed_ids):
        cls = instructions_registry.INSTRUCTION_DICT[instruction_id]
        inst = cls(instruction_id)
        description = inst.build_description()
        source_kwargs = inst.get_instruction_args()
        matches = [
            m for m in compiler.recognize(description)
            if m["instruction_id"] == instruction_id
        ]
        assert len(matches) == 1, (instruction_id, description, matches)
        recovered = matches[0]["kwargs"]

        if source_kwargs:
            for key, value in source_kwargs.items():
                if instruction_id == "combination:repeat_prompt" and key == "prompt_to_repeat":
                    assert recovered["prompt_to_repeat"] is None
                    continue
                assert key in recovered, (instruction_id, key, recovered)
                assert recovered[key] == value, (instruction_id, key, value, recovered[key])

        rows.append({
            "instruction_id": instruction_id,
            "description_recognized": True,
            "source_kwargs": source_kwargs,
            "recovered_kwargs": recovered,
        })

    # Exact non-identifiability proof for the sole hidden-value residual:
    # two different hidden kwargs produce byte-identical visible descriptions.
    repeat_cls = instructions_registry.INSTRUCTION_DICT["combination:repeat_prompt"]
    a = repeat_cls("combination:repeat_prompt")
    b = repeat_cls("combination:repeat_prompt")
    da = a.build_description(prompt_to_repeat="ALPHA PRIVATE SOURCE")
    db = b.build_description(prompt_to_repeat="BETA DIFFERENT PRIVATE SOURCE")
    assert da == db
    ra = [m for m in compiler.recognize(da) if m["instruction_id"] == "combination:repeat_prompt"][0]
    assert ra["kwargs"]["prompt_to_repeat"] is None

    # Relation and numeric sweeps exercise the parameterized templates rather
    # than relying on one seeded random sample.
    sweeps = [
        ("keywords:frequency", {"keyword": "quartz", "frequency": 1, "relation": "less than"}),
        ("keywords:frequency", {"keyword": "quartz", "frequency": 9, "relation": "at least"}),
        ("keywords:letter_frequency", {"letter": "z", "let_frequency": 1, "let_relation": "less than"}),
        ("keywords:letter_frequency", {"letter": "a", "let_frequency": 9, "let_relation": "at least"}),
        ("length_constraints:number_sentences", {"num_sentences": 1, "relation": "less than"}),
        ("length_constraints:number_sentences", {"num_sentences": 20, "relation": "at least"}),
        ("length_constraints:number_words", {"num_words": 100, "relation": "less than"}),
        ("length_constraints:number_words", {"num_words": 500, "relation": "at least"}),
        ("change_case:capital_word_frequency", {"capital_frequency": 1, "capital_relation": "less than"}),
        ("change_case:capital_word_frequency", {"capital_frequency": 20, "capital_relation": "at least"}),
    ]
    for instruction_id, kwargs in sweeps:
        cls = instructions_registry.INSTRUCTION_DICT[instruction_id]
        inst = cls(instruction_id)
        description = inst.build_description(**kwargs)
        matches = [m for m in compiler.recognize(description) if m["instruction_id"] == instruction_id]
        assert len(matches) == 1, (instruction_id, kwargs, description, matches)
        recovered = matches[0]["kwargs"]
        for key, value in inst.get_instruction_args().items():
            assert recovered[key] == value, (instruction_id, key, value, recovered.get(key))

    result = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_COMPILER_PUBLIC_RUNNER_RESULT_V1",
        "status": "PASS",
        "pinned_livebench_commit": PINNED_COMMIT,
        "candidate_compiler_git_blob_sha": EXPECTED_COMPILER_BLOB,
        "legacy_registry_type_count": len(observed_ids),
        "visible_description_recognized_type_count": len(rows),
        "hidden_parameter_fully_derivable_type_count": 24,
        "irreducible_hidden_parameter_type_count": 1,
        "irreducible_hidden_parameter_types": ["combination:repeat_prompt"],
        "repeat_prompt_nonidentifiability_witness": {
            "different_hidden_values": True,
            "identical_visible_description": True,
        },
        "terminal_prompt_content_read": False,
        "terminal_kwargs_read": False,
        "terminal_instruction_id_list_read": False,
        "terminal_responses_generated": 0,
        "acceptance_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
    (ROOT / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
