#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_sentence_wrapper_closure_20261005"
RUNTIME = SUBJECT / "canonical/runtime"
OUT = ROOT / "livebench_composer_v2_verification.json"

EXPECTED_BLOBS = {
    "livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "livebench_legacy15_word_upper_domain_collapse_v1.py":
        "9f6af0da7a26cbe0b12e8dde44aca73f9b46359f",
}

def git_blob_sha(path: pathlib.Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def write(payload: dict) -> None:
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def main() -> int:
    actual={name:git_blob_sha(RUNTIME/name) for name in EXPECTED_BLOBS}
    mismatches={name:{"expected":EXPECTED_BLOBS[name],"actual":actual[name]}
                for name in EXPECTED_BLOBS if actual[name]!=EXPECTED_BLOBS[name]}
    if mismatches:
        write({"schema":"PROJECT_BRAIN_LIVEBENCH_WORD_UPPER_COLLAPSE_INDEPENDENT_VERIFICATION_V1",
               "status":"FAIL__SUBJECT_BLOB_MISMATCH","mismatches":mismatches})
        return 1

    sys.path.insert(0,str(SUBJECT))
    try:
        from canonical.runtime import livebench_legacy15_word_upper_domain_collapse_v1 as proof
        result=proof.prove("/tmp/LiveBench")
    except Exception as exc:
        payload={
            "schema":"PROJECT_BRAIN_LIVEBENCH_WORD_UPPER_COLLAPSE_INDEPENDENT_VERIFICATION_V1",
            "status":"FAIL__VERIFIER_EXCEPTION",
            "subject_blobs":actual,
            "exception_type":type(exc).__name__,
            "exception":str(exc),
            "traceback":traceback.format_exc(),
        }
        write(payload)
        raise

    passed=(
        result.get("status")
        =="PASS__ALL_PUBLIC_WORD_LESS_THAN_THRESHOLDS_COLLAPSE_PARAMETRICALLY"
        and result.get("conservative_mandatory_word_bound")==63
        and result.get("public_word_threshold_domain",{}).get("count")==401
        and result.get("word_constraint_special_route_violations")==0
    )
    receipt={
        "schema":"PROJECT_BRAIN_LIVEBENCH_WORD_UPPER_COLLAPSE_INDEPENDENT_VERIFICATION_V1",
        "status":(
            "PASS__INDEPENDENT_WORD_UPPER_DOMAIN_COLLAPSE__63_LT_100"
            if passed else "FAIL__INDEPENDENT_WORD_UPPER_DOMAIN_COLLAPSE"
        ),
        "subject_blobs":actual,
        "proof_result":result,
        "terminal_rows_read":0,
        "terminal_kwargs_read":0,
        "terminal_instruction_id_lists_read":0,
        "target_scores_read":0,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
    }
    write(receipt)
    print(json.dumps({
        "status":receipt["status"],
        "bound":result.get("conservative_mandatory_word_bound"),
        "word_sets":result.get("word_constraint_structural_id_sets"),
        "threshold_count":result.get("public_word_threshold_domain",{}).get("count"),
    },sort_keys=True))
    return 0 if passed else 1

if __name__=="__main__":
    raise SystemExit(main())
