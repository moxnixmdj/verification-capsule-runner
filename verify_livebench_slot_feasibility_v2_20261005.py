#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_slot_feasibility_v2_20261005"

EXPECTED = {
    SUBJECT / "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    SUBJECT / "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "70af00025df343398ef3b1e4302208ef93ba7872",
    SUBJECT / "canonical/runtime/livebench_legacy15_slot_feasibility_v2.py":
        "23474430c72929cd2ae8e0a24b871e64effd612c",
}

LIVEBENCH = Path("/tmp/LiveBench")
GEN = Path("/tmp/LiveBenchGen")
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"
SCORE_UTILS_BLOB = "8ce01747887ec0792c8f024e1972e34ece781676"


def blob(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


for path, expected in EXPECTED.items():
    got = blob(path)
    assert got == expected, (path, got, expected)

ipath = LIVEBENCH / "livebench/if_runner/instruction_following_eval/instructions.py"
rpath = LIVEBENCH / "livebench/if_runner/instruction_following_eval/instructions_registry.py"
upath = LIVEBENCH / "livebench/if_runner/instruction_following_eval/instructions_util.py"
spath = LIVEBENCH / "livebench/process_results/instruction_following/utils.py"
gpath = GEN / "livebench/if_runner/live_data.py"

assert blob(ipath) == INSTRUCTIONS_BLOB
assert blob(rpath) == REGISTRY_BLOB
assert blob(upath) == UTIL_BLOB
assert blob(spath) == SCORE_UTILS_BLOB
assert blob(gpath) == GENERATOR_BLOB

sys.path.insert(0, str(SUBJECT))
from canonical.runtime import livebench_legacy15_slot_feasibility_v2 as f

# Independent execution of the candidate theorem.
proof = f.prove_sentence_end_unsat()
assert proof["status"] == "PASS__THIRD_PUBLIC_SLOT_UNSAT_CLASS_CERTIFIED"
assert proof["terminal_data_used"] is False
assert proof["hidden_kwargs_used"] is False
assert proof["acceptance_credit"] is False

# Bind the exact public checker behavior, not merely source comments.
sys.path.insert(0, str(LIVEBENCH / "livebench/if_runner"))
from instruction_following_eval import instructions, instructions_util

sentence_id = "length_constraints:number_sentences"
end_id = "startend:end_checker"
for phrase in sorted(f.PUBLIC_END_PHRASES):
    s = instructions.NumberOfSentences(sentence_id)
    s.build_description(num_sentences=1, relation="less than")
    e = instructions.EndChecker(end_id)
    e.build_description(end_phrase=phrase)
    assert e.check_following(phrase) is True, phrase
    assert instructions_util.count_sentences(phrase) >= 1, phrase
    assert s.check_following(phrase) is False, phrase

    out = f.classify_visible_contracts([
        {
            "instruction_id": sentence_id,
            "slots": {"num_sentences": 1, "relation": "less than"},
        },
        {
            "instruction_id": end_id,
            "slots": {"end_phrase": phrase},
        },
    ])
    assert out["status"] == "PROVED_UNSAT", out
    assert out["hard_unsat_reasons"] == [
        "LESS_THAN_ONE_SENTENCE_WITH_MANDATORY_PUBLIC_END_PHRASE"
    ], out

# Confirm the frozen registry does not deconflict this pair.
registry_src = rpath.read_text(encoding="utf-8")
assert '_LENGTH + "number_sentences": {_LENGTH + "number_sentences"}' in registry_src
assert '_STARTEND + "end_checker": {_STARTEND + "end_checker"}' in registry_src

# Confirm the historical generator can draw both IDs before deconfliction.
generator_src = gpath.read_text(encoding="utf-8")
assert '"length_constraints:number_sentences"' in generator_src
assert '"startend:end_checker"' in generator_src
assert "np.random.randint(2, max_instructions+1" in generator_src
assert "np.random.choice(all_constraints, draw, replace=False)" in generator_src
assert "build_instruction.build_description()" in generator_src

# Frozen LiveBench case scoring: if two instructions are jointly impossible,
# follow_all is necessarily false and at most one of two individual checks can
# pass, so the exact per-case score ceiling is (0 + 1/2) / 2 = 0.25.
score_src = spath.read_text(encoding="utf-8")
assert "avg_score = (score_1 + score_2) / 2" in score_src
case_score_ceiling = (0.0 + 0.5) / 2.0
assert case_score_ceiling == 0.25
superset_case_score_ceilings = {k: ((k - 1) / k) / 2.0 for k in range(2, 6)}
assert max(superset_case_score_ceilings.values()) == 0.4

receipt = {
    "schema": "PROJECT_BRAIN_LIVEBENCH_SLOT_FEASIBILITY_V2_INDEPENDENT_VERIFICATION_20261005_V1",
    "status": "PASS__EXACT_BYTE_V2_AND_PINNED_CHECKER_EXECUTION_VERIFIED",
    "brain_subject_blobs": {
        "composition_archetypes_v1": EXPECTED[SUBJECT / "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py"],
        "slot_feasibility_v1": EXPECTED[SUBJECT / "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py"],
        "slot_feasibility_v2": EXPECTED[SUBJECT / "canonical/runtime/livebench_legacy15_slot_feasibility_v2.py"],
    },
    "public_bindings": {
        "livebench_commit": LIVEBENCH_COMMIT,
        "historical_generator_commit": GENERATOR_COMMIT,
        "instructions_blob": INSTRUCTIONS_BLOB,
        "registry_blob": REGISTRY_BLOB,
        "instructions_util_blob": UTIL_BLOB,
        "generator_blob": GENERATOR_BLOB,
        "score_utils_blob": SCORE_UTILS_BLOB,
    },
    "verified": [
        "SENTENCE_LT_1_PLUS_EITHER_FROZEN_PUBLIC_END_PHRASE_IS_HARD_UNSAT",
        "PAIR_IS_NOT_DECLARED_CONFLICTING_BY_PINNED_REGISTRY",
        "PAIR_IS_DRAWABLE_BY_HISTORICAL_GENERATOR_BEFORE_DECONFLICTION",
        "PINNED_PUNKT_EXECUTION_COUNTS_EACH_PUBLIC_END_PHRASE_AS_AT_LEAST_ONE_SENTENCE",
        "V2_PRESERVES_ZERO_TERMINAL_DATA_AND_ZERO_ACCEPTANCE_CREDIT",
    ],
    "unsat_pair_exact_case_score_ceiling": case_score_ceiling,
    "unsat_pair_superset_case_score_ceiling_by_k": superset_case_score_ceilings,
    "unsat_pair_superset_case_score_ceiling_for_k_le_5": max(superset_case_score_ceilings.values()),
    "terminal_rows_read": 0,
    "terminal_scores_read": 0,
    "acceptance_credit_delta": 0,
    "family_credit_delta": 0,
    "capability_credit_delta": 0,
    "ownership_credit_delta": 0,
}
Path("livebench_slot_feasibility_v2_verification.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(receipt, sort_keys=True))
