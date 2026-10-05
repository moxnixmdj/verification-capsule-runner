#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "livebench_schema19_singleton_totality_20261005"
sys.path.insert(0, str(SUBJECT))
sys.path.insert(0, "/tmp/livebench/livebench/if_runner")

EXPECTED_BLOBS = {
    "canonical/runtime/livebench_active15_plus_one_noarg_pointwise_v1.py": "2ecd3e14ebd47830a717cca4b4eba987e8dd1684",
    "canonical/runtime/livebench_schema19_pointwise_candidate_v1.py": "221131ad2cd0b6b01f3d5e5a6004cfbd1d64becd",
    "canonical/runtime/livebench_frozen_schema19_envelope_v1.py": "8259959828398e7b1415e305fd9bbd8ca308dfc5",
    "canonical/runtime/livebench_release_schema_scope_bridge_v1.py": "fa90615507b048894b5dc118e0c6c39cb2146fcf",
    "canonical/runtime/livebench_union25_archetypes_v1.py": "8c68e63bbc1e1b843f076dbcd8c4bfae11d4cc2a",
    "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py": "71e637c70edf1c582e28ea38b3b798965c803a06",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py": "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py": "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
}

def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

for rel, expected in EXPECTED_BLOBS.items():
    actual = git_blob_sha1((SUBJECT / rel).read_bytes())
    if actual != expected:
        raise AssertionError(f"BLOB_MISMATCH:{rel}:{actual}:{expected}")

from canonical.runtime import livebench_active15_plus_one_noarg_pointwise_v1 as plus1
from canonical.runtime import livebench_schema19_pointwise_candidate_v1 as schema19
from canonical.runtime import livebench_union25_archetypes_v1 as u
from instruction_following_eval import instructions as pinned

def contract(iid):
    return {"instruction_id": iid, "slots": {}}

def checker_for(iid):
    if iid == u.CONSTRAINED:
        c = pinned.ConstrainedResponseChecker(iid)
        c.build_description()
        return c
    if iid == u.ENGLISH_CAPITAL:
        c = pinned.CapitalLettersEnglishChecker(iid)
        c.build_description()
        return c
    if iid == u.ENGLISH_LOWERCASE:
        c = pinned.LowercaseLettersEnglishChecker(iid)
        c.build_description()
        return c
    if iid == u.NO_COMMA:
        c = pinned.CommaChecker(iid)
        c.build_description()
        return c
    raise AssertionError("UNSUPPORTED_EXTRA:" + iid)

# First prove the exact bug is gone in the direct Active15+1 layer.
singleton_results = {}
for iid in (u.ENGLISH_CAPITAL, u.ENGLISH_LOWERCASE, u.NO_COMMA):
    out = plus1.solve_contracts([contract(iid)])
    if out.get("status") != "CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE":
        raise AssertionError(f"SINGLETON_NOT_SOLVED:{iid}:{out}")
    if out.get("theoretical_max_pass_count") != 1:
        raise AssertionError(f"SINGLETON_MAX_PASS_DRIFT:{iid}:{out}")
    if out.get("sacrificed_instruction_ids") != []:
        raise AssertionError(f"SINGLETON_FALSE_SACRIFICE:{iid}:{out}")
    response = str(out.get("response") or "")
    # Case checkers include langdetect. Re-run to stress the unseeded exact checker.
    repetitions = 32 if iid in {u.ENGLISH_CAPITAL, u.ENGLISH_LOWERCASE} else 1
    passes = sum(bool(checker_for(iid).check_following(response)) for _ in range(repetitions))
    if passes != repetitions:
        raise AssertionError(f"PINNED_CHECKER_SINGLETON_FAILURE:{iid}:{passes}/{repetitions}")
    singleton_results[iid] = {
        "response_length": len(response),
        "exact_checker_passes": passes,
        "exact_checker_trials": repetitions,
    }

# Then bind the complete six extra-only signatures exposed by schema19.
signatures = (
    (u.CONSTRAINED,),
    (u.ENGLISH_CAPITAL,),
    (u.ENGLISH_LOWERCASE,),
    (u.NO_COMMA,),
    (u.ENGLISH_CAPITAL, u.NO_COMMA),
    (u.ENGLISH_LOWERCASE, u.NO_COMMA),
)
surface_results = []
for sig in signatures:
    out = schema19.solve_contracts([contract(iid) for iid in sig])
    if out.get("status") != "CANDIDATE_POINTWISE_OPTIMAL_SCHEMA19":
        raise AssertionError(f"SCHEMA19_SIGNATURE_NOT_SOLVED:{sig}:{out}")
    if out.get("theoretical_max_pass_count") != len(sig):
        raise AssertionError(f"SCHEMA19_SIGNATURE_NOT_FULL_PASS:{sig}:{out}")
    if out.get("sacrificed_instruction_ids") != []:
        raise AssertionError(f"SCHEMA19_SIGNATURE_FALSE_SACRIFICE:{sig}:{out}")
    response = str(out.get("response") or "")
    per_checker = {}
    for iid in sig:
        repetitions = 32 if iid in {u.ENGLISH_CAPITAL, u.ENGLISH_LOWERCASE} else 1
        passes = sum(bool(checker_for(iid).check_following(response)) for _ in range(repetitions))
        if passes != repetitions:
            raise AssertionError(
                f"PINNED_CHECKER_SCHEMA19_FAILURE:{sig}:{iid}:{passes}/{repetitions}"
            )
        per_checker[iid] = {"passes": passes, "trials": repetitions}
    surface_results.append({
        "signature": list(sig),
        "response_length": len(response),
        "checker_results": per_checker,
    })

receipt = {
    "schema": "PROJECT_BRAIN_LIVEBENCH_SCHEMA19_SINGLETON_TOTALITY_INDEPENDENT_VERIFICATION_V1",
    "status": "PASS__EXACT_PR_BLOBS_BOUND__SINGLETON_HOLE_CLOSED__ALL_SIX_EXTRA_ONLY_SCHEMA19_SIGNATURES_PASS_PINNED_CHECKERS",
    "brain_pr_head": "8ac9f20887ab24932cea64c4e27b726418e7e297",
    "pinned_livebench_commit": "8f8e5c381a16e3f24257776edd53471fe86f8091",
    "pinned_langdetect": "1.0.9",
    "subject_blobs": EXPECTED_BLOBS,
    "singleton_results": singleton_results,
    "schema19_extra_only_surface_results": surface_results,
    "terminal_rows_read": 0,
    "hidden_terminal_kwargs_read": 0,
    "target_responses_read": 0,
    "target_scores_read": 0,
    "acceptance_credit": False,
    "family_credit": False,
    "capability_credit": False,
    "ownership_credit": False,
}
Path("livebench_schema19_singleton_totality_receipt.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(receipt, indent=2, sort_keys=True))
