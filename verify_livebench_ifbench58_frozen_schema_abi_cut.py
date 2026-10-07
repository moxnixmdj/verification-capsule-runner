#!/usr/bin/env python3
import hashlib
import json
import re
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
EXPECTED_BLOBS = {
    "livebench/common.py": "95373cc6a82bc935013e2c23d2a183022f802f5c",
    "livebench/gen_api_answer.py": "a9186172abfa62ef087a16dfec0cb57013ff84b5",
    "livebench/gen_ground_truth_judgment.py": "b36561da5b54380c724c507462d0ee65feefeac8",
    "livebench/incremental_judge.py": "40e352e3cf440c9643e44f3ad11d3b2ffb999ccf",
    "livebench/process_results/instruction_following/utils.py": "8ce01747887ec0792c8f024e1972e34ece781676",
    "livebench/if_runner/ifbench/evaluation_lib.py": "2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
    "livebench/if_runner/ifbench/instructions.py": "02b2dfeb50f036b89bec3df34522c73f756d8f44",
}

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def class_block(src: str, name: str) -> str:
    marker = "class " + name
    start = src.index(marker)
    nxt = src.find("\nclass ", start + len(marker))
    return src[start:] if nxt < 0 else src[start:nxt]

def load_bound_sources(root: Path) -> dict[str, str]:
    out = {}
    for rel, expected in EXPECTED_BLOBS.items():
        data = (root / rel).read_bytes()
        assert git_blob(data) == expected, (rel, git_blob(data), expected)
        out[rel] = data.decode("utf-8")
    return out

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

    src = load_bound_sources(root)
    common = src["livebench/common.py"]
    api = src["livebench/gen_api_answer.py"]
    judge = src["livebench/gen_ground_truth_judgment.py"]
    incremental = src["livebench/incremental_judge.py"]
    adapter = src["livebench/process_results/instruction_following/utils.py"]
    evaluation = src["livebench/if_runner/ifbench/evaluation_lib.py"]
    instructions = src["livebench/if_runner/ifbench/instructions.py"]

    ng = class_block(instructions, "NGramOverlapChecker")
    rs = class_block(instructions, "RepeatSpanChecker")

    # Exact checker semantics.
    assert 'return ["reference_text", "percentage"]' in ng
    assert "self._reference_text = reference_text" in ng
    assert "random.randint(1, 100)" in ng
    assert "nltk.ngrams(self._reference_text, n)" in ng

    assert 'return ["n_start", "n_end", "prompt_to_repeat"]' in rs
    assert 'raise ValueError("prompt_to_repeat must be set.")' in rs
    assert "random.randint(0, len(self._prompt_to_repeat.split()) - 2)" in rs
    assert "random.randint(self._n_start + 1, len(self._prompt_to_repeat.split()) - 1)" in rs
    assert "self._prompt_to_repeat.strip().lower().split()[self._n_start:self._n_end]" in rs

    # Exact scorer adapter: row kwargs are used directly; exceptions become score zero.
    assert 'inp.kwargs[index] = {key: value for key, value in inp.kwargs[index].items() if value is not None}' in evaluation
    assert "instruction.build_description(**inp.kwargs[index])" in evaluation
    assert "kwargs=question['kwargs']" in adapter
    assert "result = evaluation_lib.test_instruction_following_strict(inp, response)" in adapter
    assert "except Exception as e:" in adapter
    assert "return 0" in adapter

    # Bound loader and both grading paths preserve the question kwargs object.
    assert 'return load_dataset(f"{LIVE_BENCH_HF_ORGANIZATION}/{dataset_name}", split=split)' in common
    assert 'score = ifbench_process_results(question, llm_answer, debug)' in judge
    assert 'MatchSingle(dict(question), self.model_id, answer)' in incremental
    assert "question['kwargs']" not in common
    assert "question['kwargs']" not in api
    assert "question['kwargs']" not in judge
    assert "question['kwargs']" not in incremental

    # No scoring-path file can inject the missing checker state by name.
    pre_adapter_path = common + "\n" + api + "\n" + judge + "\n" + incremental + "\n" + adapter + "\n" + evaluation
    assert "reference_text" not in pre_adapter_path
    assert re.search(r"\bn_start\b", pre_adapter_path) is None
    assert re.search(r"\bpercentage\b", pre_adapter_path) is None

    # RepeatSpan uses Python's random module. The pinned scoring path never seeds it.
    assert re.search(r"^import random\s*$", instructions, re.M)
    scoring_path = judge + "\n" + incremental + "\n" + adapter + "\n" + evaluation + "\n" + instructions
    assert "random.seed(" not in scoring_path
    assert "np.random.seed(0)" in judge  # only numpy shuffle order, not Python random state

    receipt = {
        "schema": "LIVEBENCH_IFBENCH58_FROZEN_DATASET_SCHEMA_ABI_CUT_INDEPENDENT_VERIFIER_V2",
        "status": "PASS",
        "hf_revision": "0868379c4b5cf62aeacaf8be4f08fced815c81bb",
        "parquet_sha256": EXPECTED_PARQUET_SHA256,
        "parquet_bytes": EXPECTED_PARQUET_BYTES,
        "kwargs_struct_fields": sorted(fields),
        "absent_score_relevant_fields": sorted(FORBIDDEN_ABSENT_FIELDS),
        "out_of_band_missing_kwarg_injection_on_pinned_path": False,
        "ratio_overlap_fixed_reference_text_representable": False,
        "ratio_overlap_exception_to_zero_path_verified": True,
        "repeat_span_fixed_indices_representable": False,
        "repeat_span_runtime_random_index_defaults_verified": True,
        "repeat_span_python_random_seed_bound_on_scoring_path": False,
        "numpy_shuffle_seed_does_not_bind_python_random": True,
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
