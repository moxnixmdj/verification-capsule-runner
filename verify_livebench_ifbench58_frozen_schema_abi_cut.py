#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

EXPECTED_PARQUET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
EXPECTED_PARQUET_BYTES = 537024
EXPECTED_KWARGS_FIELDS = {
    "num_bullets",
    "num_paragraphs",
    "num_words",
    "relation",
    "forbidden_words",
    "section_spliter",
    "num_sections",
    "keywords",
    "end_phrase",
    "postscript_marker",
    "num_sentences",
    "nth_paragraph",
    "first_word",
    "prompt_to_repeat",
}
FORBIDDEN_ABSENT_FIELDS = {"reference_text", "percentage", "n_start", "n_end"}

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def class_block(src: str, name: str) -> str:
    marker = "class " + name
    start = src.index(marker)
    nxt = src.find("\nclass ", start + len(marker))
    return src[start:] if nxt < 0 else src[start:nxt]

def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: verifier.py PARQUET LIVEBENCH_ROOT")
    parquet = Path(sys.argv[1])
    root = Path(sys.argv[2])

    data = parquet.read_bytes()
    assert len(data) == EXPECTED_PARQUET_BYTES, len(data)
    assert hashlib.sha256(data).hexdigest() == EXPECTED_PARQUET_SHA256

    # Schema-only read. No row groups, prompt text, instruction IDs, or kwargs values are read.
    schema = pq.read_schema(parquet)
    kwargs_type = schema.field("kwargs").type
    value_type = kwargs_type.value_type
    fields = set(value_type.names)
    assert fields == EXPECTED_KWARGS_FIELDS, sorted(fields)
    assert fields.isdisjoint(FORBIDDEN_ABSENT_FIELDS)

    instructions_path = root / "livebench/if_runner/ifbench/instructions.py"
    eval_path = root / "livebench/if_runner/ifbench/evaluation_lib.py"
    adapter_path = root / "livebench/process_results/instruction_following/utils.py"

    instructions_b = instructions_path.read_bytes()
    eval_b = eval_path.read_bytes()
    adapter_b = adapter_path.read_bytes()

    assert git_blob(instructions_b) == "02b2dfeb50f036b89bec3df34522c73f756d8f44"
    assert git_blob(eval_b) == "2c7bd1290031dbe4ae0f016c53255f4af0ec645b"
    assert git_blob(adapter_b) == "8ce01747887ec0792c8f024e1972e34ece781676"

    instructions = instructions_b.decode("utf-8")
    evaluation = eval_b.decode("utf-8")
    adapter = adapter_b.decode("utf-8")

    ng = class_block(instructions, "NGramOverlapChecker")
    rs = class_block(instructions, "RepeatSpanChecker")

    assert 'return ["reference_text", "percentage"]' in ng
    assert "self._reference_text = reference_text" in ng
    assert "random.randint(1, 100)" in ng
    assert "nltk.ngrams(self._reference_text, n)" in ng

    assert 'return ["n_start", "n_end", "prompt_to_repeat"]' in rs
    assert 'raise ValueError("prompt_to_repeat must be set.")' in rs
    assert "random.randint(0, len(self._prompt_to_repeat.split()) - 2)" in rs
    assert "random.randint(self._n_start + 1, len(self._prompt_to_repeat.split()) - 1)" in rs
    assert "self._prompt_to_repeat.strip().lower().split()[self._n_start:self._n_end]" in rs

    assert 'inp.kwargs[index] = {key: value for key, value in inp.kwargs[index].items() if value is not None}' in evaluation
    assert "instruction.build_description(**inp.kwargs[index])" in evaluation

    assert "kwargs=question['kwargs']" in adapter
    assert "result = evaluation_lib.test_instruction_following_strict(inp, response)" in adapter
    assert "except Exception as e:" in adapter
    assert "return 0" in adapter

    receipt = {
        "schema": "LIVEBENCH_IFBENCH58_FROZEN_DATASET_SCHEMA_ABI_CUT_INDEPENDENT_VERIFIER_V1",
        "status": "PASS",
        "hf_revision": "0868379c4b5cf62aeacaf8be4f08fced815c81bb",
        "parquet_sha256": EXPECTED_PARQUET_SHA256,
        "parquet_bytes": EXPECTED_PARQUET_BYTES,
        "kwargs_struct_fields": sorted(fields),
        "absent_score_relevant_fields": sorted(FORBIDDEN_ABSENT_FIELDS),
        "ratio_overlap_fixed_reference_text_representable": False,
        "repeat_span_fixed_indices_representable": False,
        "repeat_span_runtime_random_index_defaults_verified": True,
        "adapter_exception_to_zero_verified": True,
        "terminal_rows_read": 0,
        "terminal_instruction_lists_read": 0,
        "terminal_kwargs_values_read": 0,
        "prompt_or_turn_text_read": 0,
    }
    Path("livebench_ifbench58_frozen_schema_abi_cut_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))

if __name__ == "__main__":
    main()
