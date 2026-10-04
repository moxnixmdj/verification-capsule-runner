#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_punkt_nonempty_unsat_20261005"
ARCH = SUBJECT / "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py"
LEMMA = SUBJECT / "canonical/runtime/livebench_punkt_nonempty_unsat_v1.py"

EXPECTED_ARCH_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
EXPECTED_LEMMA_BLOB = "88c08504e3cace1b81aae0b06d9a87d6ccdd8fce"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
INSTRUCTIONS_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
NLTK_VERSION = "3.10.3"
NLTK_PUNKT_SOURCE_BLOB = "48496d2448c009221d2452c8e928699027b20ebe"

LB = Path("/tmp/LiveBench")
NLTK_SRC = Path("/tmp/nltk-src")


def blob(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


assert blob(ARCH) == EXPECTED_ARCH_BLOB
assert blob(LEMMA) == EXPECTED_LEMMA_BLOB

ipath = LB / "livebench/if_runner/instruction_following_eval/instructions.py"
upath = LB / "livebench/if_runner/instruction_following_eval/instructions_util.py"
ppath = NLTK_SRC / "nltk/tokenize/punkt.py"
assert blob(ipath) == INSTRUCTIONS_BLOB
assert blob(upath) == INSTRUCTIONS_UTIL_BLOB
assert blob(ppath) == NLTK_PUNKT_SOURCE_BLOB

# Prove the load-bearing Punkt invariant directly from the exact NLTK 3.10.3
# source. A final rstrip-bounded slice is always emitted; _pair_iter preserves
# a singleton slice; _realign_boundaries emits a slice whenever it contains
# any character. Thus any response with non-whitespace content has >=1 sentence.
punkt_src = ppath.read_text(encoding="utf-8")
for fragment in (
    "yield slice(last_break, len(text.rstrip()))",
    "yield (prev, None)",
    "if text[sentence1]:",
    "yield sentence1",
):
    assert fragment in punkt_src, fragment

sys.path.insert(0, str(LB / "livebench/if_runner"))
from instruction_following_eval import instructions, instructions_util

# Runtime-check the theorem boundary and representative non-empty forms.
assert instructions_util.count_sentences("") == 0
assert instructions_util.count_sentences("   \n\t") == 0
for value in (
    "rock",
    "<<x>>",
    "* x",
    "Section 1",
    "P.S.",
    '""',
    "Any other questions?",
    "x " * 100,
    "rock\n\nother",
):
    assert value.rstrip()
    assert instructions_util.count_sentences(value) >= 1, value

sys.path.insert(0, str(SUBJECT))
from canonical.runtime import livebench_punkt_nonempty_unsat_v1 as f

sentence = {
    "instruction_id": f.SENTENCE,
    "slots": {"num_sentences": 1, "relation": "less than"},
}

contracts = [
    {
        "instruction_id": f.EXISTENCE,
        "slots": {"keywords": ["rock", "signal"]},
        "checker": instructions.KeywordChecker,
        "build": {"keywords": ["rock", "signal"]},
    },
    {
        "instruction_id": f.WORDS,
        "slots": {"num_words": 100, "relation": "at least"},
        "checker": instructions.NumberOfWords,
        "build": {"num_words": 100, "relation": "at least"},
    },
    {
        "instruction_id": f.NTH,
        "slots": {"num_paragraphs": 2, "nth_paragraph": 1, "first_word": "rock"},
        "checker": instructions.ParagraphFirstWordCheck,
        "build": {"num_paragraphs": 2, "nth_paragraph": 1, "first_word": "rock"},
    },
    {
        "instruction_id": f.POSTSCRIPT,
        "slots": {"postscript_marker": "P.S."},
        "checker": instructions.PostscriptChecker,
        "build": {"postscript_marker": "P.S."},
    },
    {
        "instruction_id": f.BULLETS,
        "slots": {"num_bullets": 1},
        "checker": instructions.BulletListChecker,
        "build": {"num_bullets": 1},
    },
    {
        "instruction_id": f.TITLE,
        "slots": {},
        "checker": instructions.TitleChecker,
        "build": {},
    },
    {
        "instruction_id": f.SECTIONS,
        "slots": {"section_spliter": "Section", "num_sections": 1},
        "checker": instructions.SectionChecker,
        "build": {"section_spliter": "Section", "num_sections": 1},
    },
    {
        "instruction_id": f.END,
        "slots": {"end_phrase": "Any other questions?"},
        "checker": instructions.EndChecker,
        "build": {"end_phrase": "Any other questions?"},
    },
    {
        "instruction_id": f.QUOTATION,
        "slots": {},
        "checker": instructions.QuotationChecker,
        "build": {},
    },
]

for item in contracts:
    checker = item["checker"](item["instruction_id"])
    checker.build_description(**item["build"])
    # Every whitespace-only response must fail each claimed non-empty forcer.
    for whitespace in ("", " ", "\n", "\t", " \n\t "):
        assert checker.check_following(whitespace) is False, (
            item["instruction_id"], repr(whitespace)
        )

    visible = {"instruction_id": item["instruction_id"], "slots": item["slots"]}
    assert f.forces_nonempty_response(visible) is True, item["instruction_id"]

    out = f.classify_visible_contracts([sentence, visible])
    assert out["status"] == "PROVED_UNSAT", (item["instruction_id"], out)
    assert any(
        reason == "SENTENCE_LT_ONE_WITH_NONEMPTY_REQUIRED:" + item["instruction_id"]
        for reason in out["hard_unsat_reasons"]
    ), out

# Negative controls: constraints that permit empty output must not be promoted.
for visible in (
    {
        "instruction_id": "keywords:forbidden_words",
        "slots": {"forbidden_words": ["rock"]},
    },
    {
        "instruction_id": f.WORDS,
        "slots": {"num_words": 100, "relation": "less than"},
    },
):
    assert f.forces_nonempty_response(visible) is False
    out = f.classify_visible_contracts([sentence, visible])
    assert out["status"] == "NO_PUNKT_NONEMPTY_UNSAT_CERTIFICATE", out

# Bind key exact checker source facts used by non-empty certificates.
inst_src = ipath.read_text(encoding="utf-8")
for fragment in (
    'if not re.search(keyword, value, flags=re.IGNORECASE):',
    'num_words = instructions_util.count_words(value)',
    'if not paragraph:',
    'postscript = re.findall(postscript_pattern, value, flags=re.MULTILINE)',
    'bullet_lists = re.findall(r"^\\s*\\*[^\\*].*$", value, flags=re.MULTILINE)',
    'pattern = r"<<[^\\n]+>>"',
    'return num_sections >= self._num_sections',
    'return value.endswith(self._end_phrase)',
    'return len(value) > 1 and value[0] == \'"\' and value[-1] == \'"\'',
):
    assert fragment in inst_src, fragment

summary = f.proof_summary()
assert summary["status"] == "PASS__GENERAL_PUNKT_NONEMPTY_UNSAT_LEMMA_ENCODED"
assert len(summary["certifiable_nonempty_checker_ids"]) == 9
assert summary["terminal_data_used"] is False
assert summary["acceptance_credit"] is False

receipt = {
    "schema": "PROJECT_BRAIN_LIVEBENCH_PUNKT_NONEMPTY_UNSAT_INDEPENDENT_VERIFICATION_20261005_V1",
    "status": "PASS__GENERAL_PUNKT_NONEMPTY_UNSAT_LEMMA_EXACTLY_VERIFIED",
    "brain_subject_blobs": {
        "composition_archetypes_v1": EXPECTED_ARCH_BLOB,
        "punkt_nonempty_unsat_v1": EXPECTED_LEMMA_BLOB,
    },
    "public_bindings": {
        "livebench_commit": LIVEBENCH_COMMIT,
        "instructions_blob": INSTRUCTIONS_BLOB,
        "instructions_util_blob": INSTRUCTIONS_UTIL_BLOB,
        "nltk_version": NLTK_VERSION,
        "nltk_punkt_source_blob": NLTK_PUNKT_SOURCE_BLOB,
    },
    "verified_nonempty_checker_ids": [
        item["instruction_id"] for item in contracts
    ],
    "verified_pairwise_classes_collapsed": len(contracts),
    "negative_controls": [
        "keywords:forbidden_words",
        "length_constraints:number_words__LESS_THAN",
    ],
    "terminal_rows_read": 0,
    "terminal_scores_read": 0,
    "acceptance_credit_delta": 0,
    "family_credit_delta": 0,
    "capability_credit_delta": 0,
    "ownership_credit_delta": 0,
}
Path("livebench_punkt_nonempty_unsat_verification.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(receipt, sort_keys=True))
