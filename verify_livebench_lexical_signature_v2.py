#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

SUBJECT = Path("subject/livebench_lexical_signature_v2/livebench_legacy15_lexical_collision_signature_v2.py")
EXPECTED_BLOB = "a87d53a8f21d1fa0b05b3e3500799f5153a649ad"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_subject():
    spec = importlib.util.spec_from_file_location("subject_lexical_v2", SUBJECT)
    if spec is None or spec.loader is None:
        raise RuntimeError("SUBJECT_IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def independent_expected_count() -> dict:
    fixed_words = 5
    end_phrases = 2
    fixed_nth = fixed_words * (2 ** fixed_words) * end_phrases
    generic_per_end = (2 ** fixed_words) + ((2 ** fixed_words) - 1)
    generic_nth = generic_per_end * end_phrases
    return {
        "fixed_nth": fixed_nth,
        "generic_nth": generic_nth,
        "total": fixed_nth + generic_nth,
        "cartesian_bound": 6 * 2 * (2 ** 6),
    }


def main() -> int:
    actual_blob = git_blob_sha(SUBJECT)
    assert actual_blob == EXPECTED_BLOB, (actual_blob, EXPECTED_BLOB)

    q = load_subject()
    signatures = q.enumerate_reachable_signatures()
    independent = independent_expected_count()

    assert independent == {
        "fixed_nth": 320,
        "generic_nth": 126,
        "total": 446,
        "cartesian_bound": 768,
    }
    assert len(signatures) == independent["total"]
    assert len(signatures) == len(set(signatures))
    assert q.exact_reachable_signature_count() == 446
    assert q.conservative_cartesian_bound() == 768

    fixed_index = {word: i for i, word in enumerate(q.FIXED_RELEVANT_WORDS)}
    counts = {"fixed": 0, "generic_not_forbidden": 0, "generic_forbidden": 0}
    for end_idx, nth_category, bits, nth_forbidden in signatures:
        assert end_idx in (0, 1)
        assert len(bits) == 5
        assert sum(bits) <= 5
        if nth_category in fixed_index:
            counts["fixed"] += 1
            assert nth_forbidden == bits[fixed_index[nth_category]]
        else:
            assert nth_category == "generic"
            if nth_forbidden:
                counts["generic_forbidden"] += 1
                assert sum(bits) <= 4
            else:
                counts["generic_not_forbidden"] += 1

    assert counts == {
        "fixed": 320,
        "generic_not_forbidden": 64,
        "generic_forbidden": 62,
    }

    section_sig = (0, "generic", (False, False, False, False, True), False)
    assert "MANDATORY_SECTION_SPLITTER_IS_FORBIDDEN_WORD:section" in q.lexical_unsat_reasons(section_sig)

    end0 = (0, "generic", (True, False, False, False, False), False)
    assert q.lexical_unsat_reasons(end0) == (
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:other",
    )

    end1 = (1, "generic", (False, True, True, True, False), False)
    assert q.lexical_unsat_reasons(end1) == (
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:anything",
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:can",
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:help",
    )

    nth = (0, "generic", (False, False, False, False, False), True)
    assert q.lexical_unsat_reasons(nth) == ("NTH_FIRST_WORD_IS_FORBIDDEN_WORD",)

    proof = q.prove_count()
    assert proof["exact_reachable_signature_count"] == 446
    assert proof["prior_320_bound_is_sound_for_current_kernel"] is False
    assert proof["raw_word_combination_enumeration_required"] is False
    assert proof["terminal_data_used"] is False
    assert proof["acceptance_credit"] is False

    receipt = {
        "schema": "PROJECT_BRAIN_INDEPENDENT_LIVEBENCH_LEXICAL_SIGNATURE_V2_VERIFICATION",
        "status": "PASS__EXACT_BLOB_AND_446_REACHABLE_SIGNATURES_VERIFIED",
        "subject_git_blob_sha": actual_blob,
        "exact_reachable_signature_count": len(signatures),
        "independent_fixed_nth_count": independent["fixed_nth"],
        "independent_generic_nth_count": independent["generic_nth"],
        "conservative_cartesian_bound": independent["cartesian_bound"],
        "prior_320_bound_valid": False,
        "section_collision_explicit": True,
        "terminal_rows_read": 0,
        "terminal_prompts_read": 0,
        "terminal_scores_read": 0,
        "acceptance_credit": False,
    }
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
