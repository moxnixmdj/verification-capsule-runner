#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

BRAIN_ARCHETYPES_BLOB = "0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
BRAIN_FEASIBILITY_BLOB = "70af00025df343398ef3b1e4302208ef93ba7872"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT_ROOT = ROOT / "subject/livebench_slot_feasibility_20261005"
ARCH = SUBJECT_ROOT / "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py"
FEAS = SUBJECT_ROOT / "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def main() -> int:
    assert run(["git", "hash-object", str(ARCH)], capture_output=True).stdout.strip() == BRAIN_ARCHETYPES_BLOB
    assert run(["git", "hash-object", str(FEAS)], capture_output=True).stdout.strip() == BRAIN_FEASIBILITY_BLOB

    sys.path.insert(0, str(SUBJECT_ROOT))
    from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as f

    theorem = f.prove_id_compatibility_is_not_satisfiability()
    assert theorem["status"] == "PASS__ID_COMPATIBILITY_STRICTLY_WEAKER_THAN_SLOT_SATISFIABILITY"
    assert theorem["counterexample_archetype"] == "NTH_PARAGRAPH"
    assert theorem["hard_unsat_reasons"] == ["NTH_FIRST_WORD_IS_FORBIDDEN_WORD"]
    assert theorem["terminal_data_used"] is False
    assert theorem["hidden_kwargs_used"] is False
    assert theorem["acceptance_credit"] is False

    end_case = f.classify_visible_contracts([
        {"instruction_id": f.END, "slots": {"end_phrase": "Any other questions?"}},
        {"instruction_id": f.FORBIDDEN, "slots": {"forbidden_words": ["other"]}},
    ])
    assert end_case["status"] == "PROVED_UNSAT"
    assert end_case["hard_unsat_reasons"] == [
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:other"
    ]

    with tempfile.TemporaryDirectory(prefix="livebench-slot-feas-") as td:
        checkout = pathlib.Path(td) / "LiveBench"
        run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
             "https://github.com/LiveBench/LiveBench.git", str(checkout)])
        run(["git", "-C", str(checkout), "fetch", "--quiet", "--depth=1", "origin", LIVEBENCH_COMMIT])
        run(["git", "-C", str(checkout), "checkout", "--quiet", "--detach", LIVEBENCH_COMMIT])

        ipath = "livebench/if_runner/instruction_following_eval/instructions.py"
        rpath = "livebench/if_runner/instruction_following_eval/instructions_registry.py"
        got_i = run(["git", "-C", str(checkout), "rev-parse", f"HEAD:{ipath}"], capture_output=True).stdout.strip()
        got_r = run(["git", "-C", str(checkout), "rev-parse", f"HEAD:{rpath}"], capture_output=True).stdout.strip()
        assert got_i == INSTRUCTIONS_BLOB, (got_i, INSTRUCTIONS_BLOB)
        assert got_r == REGISTRY_BLOB, (got_r, REGISTRY_BLOB)

        src = (checkout / ipath).read_text(encoding="utf-8")
        # Bind the exact load-bearing checker semantics used by the proof.
        required_fragments = [
            'paragraph = paragraphs[self._nth_paragraph - 1].strip()',
            'first_word == self._first_word',
            're.search(r"\\b" + word + r"\\b", value, flags=re.IGNORECASE)',
        ]
        for fragment in required_fragments:
            assert fragment in src, fragment

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_SLOT_FEASIBILITY_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__EXACT_BYTE_SUBJECT_AND_PINNED_CHECKER_SEMANTICS_VERIFIED",
        "brain_archetypes_blob": BRAIN_ARCHETYPES_BLOB,
        "brain_feasibility_blob": BRAIN_FEASIBILITY_BLOB,
        "livebench_commit": LIVEBENCH_COMMIT,
        "instructions_blob": INSTRUCTIONS_BLOB,
        "registry_blob": REGISTRY_BLOB,
        "verified": [
            "ID_COMPATIBILITY_STRICTLY_WEAKER_THAN_SLOT_SATISFIABILITY",
            "NTH_FIRST_WORD_FORBIDDEN_COLLISION_CERTIFIED",
            "MANDATORY_END_PHRASE_FORBIDDEN_COLLISION_CERTIFIED",
            "PINNED_CHECKER_SOURCE_SEMANTICS_BOUND",
            "ZERO_TERMINAL_ROW_CONTENT_USED",
        ],
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
    pathlib.Path("livebench_slot_feasibility_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
