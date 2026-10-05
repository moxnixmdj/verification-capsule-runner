from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
S=ROOT/"subject"/"current_8x14_totalization"
FILES={
 S/"canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json":"72a5cd689f55df84de73693371264f02ef4e7226",
 S/"canonical/verification/OPUS55_MATCHED_TARGET_NORMALIZATION_V3_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"b5192b1903dc603e75efe92b9a00ced0b2722f8c",
 S/"canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V3.json":"892678035303d753b714bd4c0870d0972ec1a7ad",
 S/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"a3fd20e58fdbd9b86278b7de0c245de3063dce27",
 S/"canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V5.json":"8397c1341b48947727c070f37a184580ca32c844",
 S/"canonical/runtime/brain_witness_normalization_verifier_v3.py":"b056cd99dce49d09060de130eeb08c1d879b5a39",
 S/"canonical/runtime/current_witness_target_totalization_v3.py":"58772362e702852c12f5e06245097e352ce8bb88",
 S/"canonical/tests/test_current_witness_target_totalization_v3.py":"d671c27818b6d083585ce3afadbfdc9855e9bf79",
}
def blob(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def fail(x): raise SystemExit("VERIFY_FAIL:"+x)
for p,h in FILES.items():
 if blob(p)!=h: fail("BLOB:"+p.name+":"+blob(p)+":"+h)

sys.path.insert(0,str(S))
from canonical.runtime.current_witness_target_totalization_v3 import totalize

load=lambda p: json.loads(p.read_text())
target=load(S/"canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json")
targetv=load(S/"canonical/verification/OPUS55_MATCHED_TARGET_NORMALIZATION_V3_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
witness=load(S/"canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V3.json")
evidence=load(S/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
root3=load(S/"canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V5.json")
out=totalize(target,targetv,witness,evidence,root3,evidence_blob_sha=blob(S/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"))
if out.get("pass") is not True: fail("TOTALIZER:"+repr(out))
expected={
 "target_count":8,"witness_count":14,"pair_count":112,
 "target_atom_occurrence_count":37,"target_metric_occurrence_count":7,
 "positive_atom_binding_count":0,"positive_metric_binding_count":0,
 "positive_semantic_edge_count":0,"closed_target_count":0,"residual_target_count":8,
}
for k,v in expected.items():
 if out.get(k)!=v: fail("FIELD:"+k+":"+repr(out.get(k))+":"+repr(v))
ids={x.get("predicate_id") for x in out.get("target_results",[])}
root7=set(root3.get("shared_matched_scope_targets",[]))
if ids != root7|{"SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"}:
 fail("TARGET_ID_SET")
if any(x.get("closed_by_current_normalized_witness_reuse") for x in out.get("target_results",[])):
 fail("FALSE_DIRECT_CLOSURE")
print(json.dumps({
 "schema":"PROJECT_BRAIN_CURRENT_8X14_TOTALIZATION_INDEPENDENT_VERIFICATION_V1",
 "pass":True,"target_count":8,"witness_count":14,"pair_count":112,
 "closed_target_count":0,"residual_target_count":8,
 "exact_subject_blobs":{p.name:h for p,h in FILES.items()},
 "acceptance_credit_delta":0,"execution_authority":False,
 "promotion_authority":False,"fresh_reality_authority":False
},sort_keys=True))
