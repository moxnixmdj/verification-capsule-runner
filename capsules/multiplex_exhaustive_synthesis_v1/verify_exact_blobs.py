from __future__ import annotations
import hashlib, json
from pathlib import Path
from canonical.runtime.multiplex_exhaustive_family_witness_v1 import evaluate

ROOT=Path(__file__).resolve().parent
EXPECTED={
  "canonical/runtime/multiplex_exhaustive_family_witness_v1.py": "d3d066198f773074a1b1e956360df7fe7382a71c",
  "canonical/tests/test_multiplex_exhaustive_family_witness_v1.py": "166ef8f3918d863429a8bb2d48c7144f70d3bd5f",
  "canonical/governance/COMMUNICATION_SYNTHESIS_MULTIPLEX_EXHAUSTIVE_WITNESS_CANDIDATE_V1.json": "73aae414bb61dc7a92119f3611846194762aae4a",
  "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json": "eb4bca0fe6a015d49d2854998fbe046c979c7ea9",
  "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json": "ee187f611a0e82b2de495ee377682f39bc31dd31",
  "canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json": "8c7ffe3d9ff789eddd286496f6de3ce84472c909",
  "canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json": "ad790afa864bd8f770c3d8a6e3ac901ed2843d26",
  "canonical/verification/P3_SYNTHESIS_T1_T3_MULTIPLEX_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "597854ad2cfffe6b943c8c0c3990071a5d5e5a44",
  "canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json": "c61882d69a66f61b4ea1ce6ad14f86fcefd1f76a",
  "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json": "bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
  "canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json": "51e3e7578e9adbeee2168d2223b84481fea16a09"
}

def git_blob_sha(path: Path) -> str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(rel: str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def main() -> int:
    errors=[]
    for rel,exp in EXPECTED.items():
        p=ROOT/rel
        if not p.is_file():
            errors.append("MISSING:"+rel); continue
        got=git_blob_sha(p)
        if got!=exp:
            errors.append("BLOB_MISMATCH:"+rel+":"+got+":"+exp)
    if errors:
        print(json.dumps({"status":"FAIL_CLOSED","errors":errors},indent=2,sort_keys=True)); return 1

    family="COMMUNICATION_AND_SYNTHESIS"
    behavior="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
    binding_path="canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json"
    out=evaluate(
        family=family,behavior_id=behavior,binding_path=binding_path,
        binding_blob_sha=EXPECTED[binding_path],
        protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
        registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
        direct_contracts=load("canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json"),
        binding=load(binding_path),
        binding_verification=load("canonical/verification/P3_SYNTHESIS_T1_T3_MULTIPLEX_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
        executor_manifest=load("canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json"),
        terminal_result=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
        postwave_reduction=load("canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"),
    )
    if not out.get("pass"): errors.append("LIVE_LIFTER_FAIL:"+repr(out.get("errors")))
    w=out.get("candidate_witness") or {}
    if w.get("mode")!="EXHAUSTIVE_FINITE": errors.append("WITNESS_MODE")
    if w.get("verified") is not False or w.get("independent") is not False: errors.append("PREMATURE_VERIFICATION")
    if w.get("result")!={"exhaustive":True,"all_cases_pass":True}: errors.append("WITNESS_RESULT")
    if w.get("source_parent_portfolios")!=["T1","T3"]: errors.append("PARENT_PORTFOLIOS")
    if w.get("source_parent_observation_count")!=2: errors.append("PARENT_OBSERVATION_COUNT")

    candidate=load("canonical/governance/COMMUNICATION_SYNTHESIS_MULTIPLEX_EXHAUSTIVE_WITNESS_CANDIDATE_V1.json")
    if "CANDIDATE" not in str(candidate.get("status","")): errors.append("CANDIDATE_STATUS")
    if candidate.get("capability_credit_delta")!=0 or candidate.get("family_credit_delta")!=0: errors.append("NONZERO_CREDIT")
    if candidate.get("execution_authority") is not False or candidate.get("promotion_authority") is not False: errors.append("PREMATURE_AUTHORITY")

    result={
      "schema":"PROJECT_BRAIN_MULTIPLEX_EXHAUSTIVE_SYNTHESIS_PUBLIC_VERIFIER_V1",
      "status":"PASS__EXACT_BLOBS__EXHAUSTIVE_SYNTHESIS_CANDIDATE_VALID__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,"errors":errors,"exact_blob_count":len(EXPECTED),
      "candidate_family":family,"candidate_behavior":behavior,"candidate_mode":w.get("mode"),
      "new_reality_units_consumed":0,"terminal_replay_count":0,
      "capability_credit_delta":0,"family_credit_delta":0,"promotion_authority":False
    }
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__": raise SystemExit(main())
