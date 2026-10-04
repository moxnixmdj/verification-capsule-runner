#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_v6_forced_fail_20261004"
LOG=SUB/"execution.log"
REC=SUB/"reconciliation.json"
EXIT=SUB/"exit_code.txt"

EXPECTED_BLOBS={
    LOG:"6c9c89cd2f7e977405017cb5ddfa8033126f4bf2",
    REC:"b1e14f11d97673a499f2d9a5e2c708d9aba969fb",
    EXIT:"573541ac9702dd3969c9bc859d2b91ec1f7e6e56",
}
EMPTY_SHA256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
POPULATION=200
EXACT_OPUS_MEAN_PERCENT=65.73775

def git_blob_sha(path: Path) -> str:
    d=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def main() -> int:
    for path, expected in EXPECTED_BLOBS.items():
        assert path.exists(), path
        assert git_blob_sha(path)==expected,(path,git_blob_sha(path),expected)
    assert EXIT.read_text().strip()=="0"

    cases=[]
    terminal=None
    for line in LOG.read_text().splitlines():
        if line.startswith("LIVEBENCH_CASE_RECEIPT="):
            cases.append(json.loads(line.split("=",1)[1]))
        elif line.startswith("LIVEBENCH_TERMINAL_RESULT="):
            terminal=json.loads(line.split("=",1)[1])

    assert len(cases)==72
    assert len({c["question_id"] for c in cases})==72

    # Load-bearing distinction from the generic lower-bound repair:
    # these are actual completed scorer outputs, not inferred lower bounds.
    assert all("score" in c for c in cases)
    assert all(float(c["score"])==0.0 for c in cases)
    assert all(c.get("scoring_error") is None for c in cases)
    assert all(c.get("response_sha256")==EMPTY_SHA256 for c in cases)

    exact_case_intervals=[(float(c["score"]),float(c["score"])) for c in cases]
    assert all(lo==0.0 and hi==0.0 for lo,hi in exact_case_intervals)

    observed_exact_mass=sum(lo for lo,_ in exact_case_intervals)
    observed_exact_upper_mass=sum(hi for _,hi in exact_case_intervals)
    assert observed_exact_mass==0.0
    assert observed_exact_upper_mass==0.0

    remaining=POPULATION-len(cases)
    conservative_upper_mass=observed_exact_upper_mass+remaining*1.0
    conservative_upper_percent=100.0*conservative_upper_mass/POPULATION

    assert remaining==128
    assert conservative_upper_mass==128.0
    assert conservative_upper_percent==64.0
    assert conservative_upper_percent < EXACT_OPUS_MEAN_PERCENT

    assert terminal is not None
    assert terminal["status"]=="FAIL_FORCED"
    assert terminal["predicate_fail_forced"] is True
    assert float(terminal["observed_score_mass"])==0.0
    assert float(terminal["conservative_full_population_upper_percent"])==64.0

    rec=json.loads(REC.read_text())
    assert rec["observed"]["replay_prefix_count"]==72
    assert rec["observed"]["observed_score_mass"]==0
    assert rec["observed"]["scoring_error_count"]==0
    assert rec["threshold_proof"]["predicate_pass_mathematically_possible_for_frozen_candidate"] is False

    result={
        "schema":"PROJECT_BRAIN_LIVEBENCH_V6_EXACT_SCORE_PRECEDENCE_INDEPENDENT_VERIFICATION_V1",
        "status":"PASS__EXACT_EXECUTION_SCORE_INTERVALS_PROVE_V6_FORCED_FAIL__GENERIC_LOWER_BOUND_REPAIR_NOT_APPLICABLE_TO_BOUND_72",
        "source_blobs":{
            "execution_log":EXPECTED_BLOBS[LOG],
            "reconciliation":EXPECTED_BLOBS[REC],
            "exit_code":EXPECTED_BLOBS[EXIT],
        },
        "verified":{
            "case_count":72,
            "unique_question_ids":72,
            "actual_score_field_present_all":True,
            "actual_score_exact_zero_all":True,
            "scoring_error_null_all":True,
            "empty_response_hash_all":True,
            "observed_exact_score_interval":"72_CASES_EACH_[0.0,0.0]",
            "remaining_unseen":128,
            "conservative_full_population_upper_percent":64.0,
            "exact_opus_mean_percent":EXACT_OPUS_MEAN_PERCENT,
            "forced_fail":True,
            "case_73_plus_needed_for_v6_decision":False,
        },
        "logic":{
            "generic_rule_preserved":"LOWER_BOUND_ONLY_EVIDENCE_DOES_NOT_PROVE_UPPER_BOUND",
            "specific_override":"ACTUAL_COMPLETED_SCORER_OUTPUT_IS_EXACT_FOR_THAT_BOUND_EXECUTION_AND_THEREFORE_SUPPLIES_BOTH_LOWER_AND_UPPER_BOUND",
            "conclusion":"THE_LATER_ROOT1_REVOCATION_PREMISE_THAT_THE_72_V6_CASES_WERE_LOWER_BOUND_ONLY_IS_FALSE",
        },
        "hard_nonclaims":[
            "NO_SUCCESSOR_PASS_CLAIM",
            "NO_NEW_TERMINAL_CASE_CONTENT",
            "NO_ACCEPTANCE_OR_CAPABILITY_CREDIT",
        ],
    }
    out=ROOT/"livebench_v6_exact_score_precedence_receipt.json"
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
