from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from canonical.runtime import unknown_domain_direct_generator_v1 as generator
from canonical.runtime import unknown_domain_direct_candidate_v1 as candidate
from canonical.runtime import unknown_domain_direct_scorer_v1 as scorer

ROOT=Path(__file__).resolve().parent

EXPECTED={
  "canonical/governance/UNKNOWN_DOMAIN_DIRECT_ORACLE_FAMILY_FREEZE_V1.json":"7a9fccc52df48d4b0088f653db38d902fe1450fc",
  "canonical/governance/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_REQUALIFICATION_V1.json":"43a1d95cb37b409c5b7db1e8bf90ba961a6878ce",
  "canonical/runtime/unknown_domain_direct_generator_v1.py":"091504068eb70591a4bcb555f2b4760bee847c5d",
  "canonical/runtime/unknown_domain_direct_scorer_v1.py":"4e2fcbb4fc6a76b605c08788faa0c723df38d551",
  "canonical/runtime/unknown_domain_direct_candidate_v1.py":"32c5fade3f53c3a43c2c5e091ed5f1580851344b",
  "canonical/runtime/decision_discriminator_v3.py":"3ec9e43a7bbe40a264fa3560a93039461941dbee",
  "canonical/tests/test_unknown_domain_direct_family_freeze_v1.py":"8d2f97ab83d7cc9b72dcf5a51a66f7201ab0cdca",
  "canonical/tests/test_unknown_domain_direct_candidate_v1.py":"5e0709613bc3865391eb514acddb87a278a14f34",
}

def git_blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def verify_exact_blobs():
    for rel,expected in EXPECTED.items():
        got=git_blob_sha((ROOT/rel).read_bytes())
        assert got==expected,(rel,got,expected)

def verify_fixture_behavior():
    cases=generator.generate("INDEPENDENT-VERIFIER-PREQUAL-BEACON-V1")["cases"]
    results=[candidate.solve(case["visible"]) for case in cases]
    out=scorer.score_cases(cases,results)
    assert out["pass"] is True,out
    assert out["case_count"]==48,out
    assert out["by_mode"]["IDENTIFIABLE_TRANSFER"]=={"pass":24,"total":24},out
    assert out["by_mode"]["NONIDENTIFIABLE_ABSTAIN"]=={"pass":12,"total":12},out
    assert out["by_mode"]["UNDERSPECIFIED_REQUEST_DISCRIMINATOR"]=={"pass":12,"total":12},out
    for result in results:
        assert result["persistent_learned_bytes"]==0,result
        assert result["external_frontier_model_calls"]==0,result
        assert result["external_learned_capability_calls"]==0,result
    return out

if __name__=="__main__":
    verify_exact_blobs()
    subprocess.check_call([
        "python","-m","unittest",
        "canonical.tests.test_unknown_domain_direct_family_freeze_v1",
        "canonical.tests.test_unknown_domain_direct_candidate_v1",
        "-v",
    ])
    out=verify_fixture_behavior()
    print(json.dumps({
      "status":"INDEPENDENT_PREQUALIFICATION_PASS",
      "case_count":out["case_count"],
      "by_mode":out["by_mode"],
      "persistent_learned_bytes":0,
      "external_frontier_model_calls":0,
      "external_learned_capability_calls":0,
    },indent=2,sort_keys=True))
