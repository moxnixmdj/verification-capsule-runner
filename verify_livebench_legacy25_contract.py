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
COMPILER_BLOB = "0bc0ec937127f306d1631ebf50fc797a9c72eb6f"
WITNESS_BLOB = "e927c05071bb4342b41fb9d5be07cc32ea82e820"

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT_ROOT = ROOT / "subject/livebench_legacy25_contract_20261004"
COMPILER_PATH = SUBJECT_ROOT / "canonical/runtime/livebench_legacy25_prompt_contract_compiler_v1.py"
WITNESS_PATH = SUBJECT_ROOT / "canonical/runtime/livebench_legacy25_single_contract_witness_v1.py"

KWARGS = {
    "keywords:existence": {"keywords":["amber","birch"]},
    "keywords:frequency": {"keyword":"cedar","frequency":3,"relation":"at least"},
    "keywords:forbidden_words": {"forbidden_words":["delta","ember"]},
    "keywords:letter_frequency": {"letter":"q","let_frequency":4,"let_relation":"less than"},
    "language:response_language": {"language":"fr"},
    "length_constraints:number_sentences": {"num_sentences":3,"relation":"at least"},
    "length_constraints:number_paragraphs": {"num_paragraphs":3},
    "length_constraints:number_words": {"num_words":120,"relation":"less than"},
    "length_constraints:nth_paragraph_first_word": {"num_paragraphs":3,"nth_paragraph":2,"first_word":"harbor"},
    "detectable_content:number_placeholders": {"num_placeholders":2},
    "detectable_content:postscript": {"postscript_marker":"P.S."},
    "detectable_format:number_bullet_lists": {"num_bullets":3},
    "detectable_format:constrained_response": {},
    "detectable_format:number_highlighted_sections": {"num_highlights":2},
    "detectable_format:multiple_sections": {"section_spliter":"Section","num_sections":3},
    "detectable_format:json_format": {},
    "detectable_format:title": {},
    "combination:two_responses": {},
    "combination:repeat_prompt": {"prompt_to_repeat":"Write a short note."},
    "startend:end_checker": {"end_phrase":"Any other questions?"},
    "change_case:capital_word_frequency": {"capital_frequency":5,"capital_relation":"at least"},
    "change_case:english_capital": {},
    "change_case:english_lowercase": {},
    "punctuation:no_comma": {},
    "startend:quotation": {},
}

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)

def main() -> int:
    got_compiler = run(["git","hash-object",str(COMPILER_PATH)],capture_output=True).stdout.strip()
    got_witness = run(["git","hash-object",str(WITNESS_PATH)],capture_output=True).stdout.strip()
    assert got_compiler == COMPILER_BLOB, (got_compiler, COMPILER_BLOB)
    assert got_witness == WITNESS_BLOB, (got_witness, WITNESS_BLOB)

    sys.path.insert(0, str(SUBJECT_ROOT))
    from canonical.runtime import livebench_legacy25_prompt_contract_compiler_v1 as subject
    from canonical.runtime import livebench_legacy25_single_contract_witness_v1 as witness

    assert len(subject.ACTIVE_LEGACY_IDS) == 25
    assert set(subject.ACTIVE_LEGACY_IDS) == set(KWARGS)

    with tempfile.TemporaryDirectory(prefix="livebench-legacy25-") as td:
        checkout = pathlib.Path(td) / "LiveBench"
        run(["git","clone","--quiet","--filter=blob:none","--no-checkout","https://github.com/LiveBench/LiveBench.git",str(checkout)])
        run(["git","-C",str(checkout),"fetch","--quiet","--depth=1","origin",LIVEBENCH_COMMIT])
        run(["git","-C",str(checkout),"checkout","--quiet","--detach",LIVEBENCH_COMMIT])

        registry_path = "livebench/if_runner/instruction_following_eval/instructions_registry.py"
        instructions_path = "livebench/if_runner/instruction_following_eval/instructions.py"
        got_registry = run(["git","-C",str(checkout),"rev-parse",f"HEAD:{registry_path}"],capture_output=True).stdout.strip()
        got_instructions = run(["git","-C",str(checkout),"rev-parse",f"HEAD:{instructions_path}"],capture_output=True).stdout.strip()
        assert got_registry == REGISTRY_BLOB, (got_registry, REGISTRY_BLOB)
        assert got_instructions == INSTRUCTIONS_BLOB, (got_instructions, INSTRUCTIONS_BLOB)

        sys.path.insert(0, str(checkout / "livebench/if_runner"))
        from instruction_following_eval import instructions_registry, instructions_util

        active = instructions_registry.INSTRUCTION_DICT
        assert len(active) == 25, len(active)
        assert set(active) == set(subject.ACTIVE_LEGACY_IDS)

        receipts = []
        for instruction_id in subject.ACTIVE_LEGACY_IDS:
            checker = active[instruction_id](instruction_id)
            description = checker.build_description(**KWARGS[instruction_id])
            prompt = (
                KWARGS[instruction_id]["prompt_to_repeat"] + "\n" + description
                if instruction_id == "combination:repeat_prompt"
                else description
            )
            compiled = subject.compile_prompt(prompt)
            ids = compiled["recognized_instruction_ids"]
            assert instruction_id in ids, (instruction_id, description, ids)
            result = witness.witness_from_prompt(prompt)
            response = result["response"]
            passed = bool(checker.check_following(response))
            assert passed, (instruction_id, description, response, compiled)
            receipts.append({
                "instruction_id": instruction_id,
                "description_length": len(description),
                "recognized": True,
                "constructive_witness_pass": True,
                "response_length": len(response),
            })

        language_receipts = []
        for code, name in instructions_util.LANGUAGE_CODES.items():
            checker = active["language:response_language"]("language:response_language")
            description = checker.build_description(language=code)
            compiled = subject.compile_prompt(description)
            contracts = [c for c in compiled["contracts"] if c["instruction_id"] == "language:response_language"]
            assert len(contracts) == 1, (code, name, compiled)
            slots = contracts[0]["slots"]
            assert slots["language"] == code, (code, slots)
            assert slots["language_name"] == name, (name, slots)
            response = witness.witness_from_prompt(description)["response"]
            assert checker.check_following(response), (code, name, response)
            language_receipts.append({
                "code":code,
                "name":name,
                "recognized":True,
                "constructive_witness_pass":True,
                "response_length":len(response),
            })

        receipt = {
            "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY25_CONSTRUCTIVE_COMPILER_INDEPENDENT_VERIFICATION_V1",
            "status":"PASS",
            "pinned_livebench_commit":LIVEBENCH_COMMIT,
            "registry_blob":REGISTRY_BLOB,
            "instructions_blob":INSTRUCTIONS_BLOB,
            "brain_compiler_blob":COMPILER_BLOB,
            "brain_witness_blob":WITNESS_BLOB,
            "active_registry_count":len(active),
            "source_generated_family_descriptions_tested":len(receipts),
            "source_generated_family_descriptions_recognized":sum(1 for x in receipts if x["recognized"]),
            "source_generated_single_contract_witnesses_passed":sum(1 for x in receipts if x["constructive_witness_pass"]),
            "language_descriptions_tested":len(language_receipts),
            "language_descriptions_recognized":sum(1 for x in language_receipts if x["recognized"]),
            "language_witnesses_passed":sum(1 for x in language_receipts if x["constructive_witness_pass"]),
            "multi_contract_composition_proved":False,
            "terminal_case_content_read":False,
            "terminal_kwargs_read":False,
            "terminal_instruction_ids_read":False,
            "semantic_capability_credit":False,
            "acceptance_credit_delta":0,
            "family_receipts":receipts,
            "language_receipts":language_receipts,
        }
        pathlib.Path("livebench_legacy25_contract_verification.json").write_text(
            json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
