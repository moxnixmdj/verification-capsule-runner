#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_lexical_quotient_74_20261005/livebench_legacy15_lexical_collision_quotient_v1.py"
LIVEBENCH_UTIL = Path("/tmp/livebench/livebench/if_runner/instruction_following_eval/instructions_util.py")

EXPECTED_SUBJECT_BLOB = "85f3ec7ae829cd7708c7b774bbf879ef39ac0aa4"
EXPECTED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
EXPECTED_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

assert blob_sha(SUBJECT) == EXPECTED_SUBJECT_BLOB
assert blob_sha(LIVEBENCH_UTIL) == EXPECTED_UTIL_BLOB

# Extract the exact public WORD_LIST without importing benchmark execution code.
text = LIVEBENCH_UTIL.read_text()
start = text.index("WORD_LIST = [")
end = text.index("]  # pylint: disable=line-too-long", start)
words = re.findall(r'"([^"]+)"', text[start:end+1])
assert len(words) == 1525
assert len(set(words)) == 1525
assert all(re.fullmatch(r"[A-Za-z]+", w) for w in words)
wordset = set(words)

special = ("other", "anything", "can", "help")
assert all(w in wordset for w in special)
generic_reps = ("western", "sentence", "signal", "dump", "spot", "opposite", "bottom", "potato")
assert all(w in wordset for w in generic_reps)
assert sum(1 for w in words if w + "x" in wordset) == 0

# Load exact vendored Brain subject after the source facts are independently checked.
spec = importlib.util.spec_from_file_location("subject_quotient", SUBJECT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)

out = mod.verify()
assert out["status"] == "PASS__EXACT_REACHABLE_LEXICAL_COLLISION_QUOTIENT_74"
assert out["reachable_signature_count"] == 74
assert out["first_end_signature_count"] == 18
assert out["second_end_signature_count"] == 56

# Independent symbolic enumeration. Do not call the subject enumerator here.
ends = {
    "Any other questions?": ("other",),
    "Is there anything else I can help with?": ("anything", "can", "help"),
}
categories = (*special, "__OTHER_WORD_LIST_VALUE__")
independent = set()
for end_phrase, relevant in ends.items():
    for category in categories:
        for nth_forbidden in (False, True):
            for mask in itertools.product((False, True), repeat=len(relevant)):
                if category in relevant:
                    i = relevant.index(category)
                    if nth_forbidden != mask[i]:
                        continue
                independent.add((end_phrase, category, nth_forbidden, tuple(mask)))

assert len(independent) == 74
assert sum(x[0] == "Any other questions?" for x in independent) == 18
assert sum(x[0] == "Is there anything else I can help with?" for x in independent) == 56

subject_sigs = set()
for sig in mod.enumerate_reachable_signatures():
    subject_sigs.add((sig.end_phrase, sig.nth_category, sig.nth_is_forbidden, tuple(sig.end_forbidden_mask)))
assert subject_sigs == independent

# Independently validate every canonical representative against the exact public
# vocabulary and the quotient's observable membership facts.
for sig in mod.enumerate_reachable_signatures():
    row = mod.representative(sig)
    forbidden = row["forbidden_words"]
    nth = row["nth_first_word"]
    end = row["end_phrase"]

    assert len(forbidden) == 5
    assert len(set(forbidden)) == 5
    assert all(w in wordset for w in forbidden)
    assert nth in wordset
    assert (nth in set(forbidden)) == sig.nth_is_forbidden

    relevant = ends[end]
    observed_mask = tuple(w in set(forbidden) for w in relevant)
    assert observed_mask == tuple(sig.end_forbidden_mask)

# Combinatorial derivation independently reproduces the closed form:
# first end: 2 + 4*4 = 18; second end: 3*8 + 2*16 = 56.
assert 2 + 4 * 4 == 18
assert 3 * 8 + 2 * 16 == 56
assert 18 + 56 == 74

report = {
    "schema": "PROJECT_BRAIN_LIVEBENCH_LEXICAL_QUOTIENT_74_INDEPENDENT_VERIFICATION_V1",
    "status": "PASS__EXACT_SUBJECT_BYTES__FROZEN_WORD_DOMAIN__INDEPENDENT_74_STATE_ENUMERATION__REPRESENTATIVE_BIJECTION",
    "subject_git_blob_sha": EXPECTED_SUBJECT_BLOB,
    "livebench_commit": EXPECTED_LIVEBENCH_COMMIT,
    "instructions_util_git_blob_sha": EXPECTED_UTIL_BLOB,
    "word_list_entries": len(words),
    "word_list_unique": len(set(words)),
    "reachable_signature_count": len(independent),
    "first_end_signature_count": 18,
    "second_end_signature_count": 56,
    "prior_upper_bound": 320,
    "reduction_factor": 320 / 74,
    "active_terminal_rows_read": 0,
    "terminal_frequency_used": False,
    "acceptance_credit_delta": 0,
}
print(json.dumps(report, sort_keys=True))
