#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
import sys

EXPECTED = {
    "evaluation_main.py": "4a341984936c4d609644a3b77f8c030ac5aa7269",
    "instructions_util.py": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "instructions.py": "4997bab885a676d92545fd91a9a20b48d234a2b2",
}
FROZEN_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
SCHEMA = "LIVEBENCH_ZERO_SENTENCE_UNSAT_INDEPENDENT_VERIFICATION_V1"


def git_blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()

    root = Path(ns.livebench_root).resolve()
    base = root / "livebench" / "if_runner" / "instruction_following_eval"
    paths = {
        "evaluation_main.py": base / "evaluation_main.py",
        "instructions_util.py": base / "instructions_util.py",
        "instructions.py": base / "instructions.py",
    }

    observed = {name: git_blob_sha(path) for name, path in paths.items()}
    assert observed == EXPECTED, (observed, EXPECTED)

    eval_src = paths["evaluation_main.py"].read_text(encoding="utf-8")
    inst_src = paths["instructions.py"].read_text(encoding="utf-8")

    strict_gate = "if response.strip() and instruction.check_following(response):"
    assert strict_gate in eval_src

    class_start = inst_src.index("class NumberOfSentences")
    class_end = inst_src.index("\nclass ", class_start + 10)
    sentence_src = inst_src[class_start:class_end]
    assert "num_sentences = instructions_util.count_sentences(value)" in sentence_src
    assert "return num_sentences < self._num_sentences_threshold" in sentence_src

    sys.path.insert(0, str(root / "livebench" / "if_runner"))
    from instruction_following_eval import instructions_util  # type: ignore
    import nltk

    assert nltk.__version__ == "3.10.3", nltk.__version__

    slices_src = inspect.getsource(nltk.tokenize.punkt.PunktSentenceTokenizer._slices_from_text)
    realign_src = inspect.getsource(nltk.tokenize.punkt.PunktSentenceTokenizer._realign_boundaries)
    assert "yield slice(last_break, len(text.rstrip()))" in slices_src
    assert "if text[sentence1]:" in realign_src
    assert "yield sentence1" in realign_src

    # Dynamic falsification set. The universal proof is source-semantic above;
    # these cases guard surprising tokenizer behavior around punctuation/space.
    nonblank = [
        "x",
        "!",
        "?",
        ".",
        "...",
        "!!!",
        "???",
        "x.",
        "x\n",
        "\n!\n",
        '"',
        "''",
        "0",
        "_",
        "*",
        "***",
        "P.S.",
        "Section1",
        "\t!\t",
        "\n\nq\n\n",
    ]
    counts = {repr(x): instructions_util.count_sentences(x) for x in nonblank}
    assert all(x.strip() for x in nonblank)
    assert all(v >= 1 for v in counts.values()), counts

    # The raw checker alone accepts blank for <1, but the strict evaluator gate
    # forbids that escape. This is the load-bearing conjunction.
    from instruction_following_eval import instructions  # type: ignore
    checker = instructions.NumberOfSentences("length_constraints:number_sentences")
    checker.build_description(num_sentences=1, relation="less than")
    assert checker.check_following("") is True
    assert "".strip() == ""
    for x in nonblank:
        assert checker.check_following(x) is False, (x, counts[repr(x)])

    result = {
        "schema": SCHEMA,
        "status": "PASS__STRICT_EVALUATOR_SENTENCE_LT_ONE_UNSAT_VERIFIED",
        "frozen_livebench_commit": FROZEN_COMMIT,
        "verified_livebench_blobs": observed,
        "nltk_version": nltk.__version__,
        "strict_nonempty_gate_verified": True,
        "punkt_universal_final_slice_semantics_verified": True,
        "dynamic_nonblank_case_count": len(nonblank),
        "dynamic_sentence_counts": counts,
        "theorem": (
            "blank responses can satisfy the raw <1 checker but are rejected by "
            "the strict evaluator; every strict-admissible nonblank response has "
            "at least one Punkt sentence; therefore strict sentence<1 is UNSAT"
        ),
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_case_ids_read": 0,
        "acceptance_credit": False,
    }
    Path(ns.output).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
