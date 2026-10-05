from __future__ import annotations
import copy, hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUBJECT=ROOT/"subject"/"current_14_witness_normalization"
SOURCE=SUBJECT/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
NORMALIZED=SUBJECT/"canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V3.json"
RUNTIME=SUBJECT/"canonical/runtime/brain_witness_normalization_verifier_v3.py"
TEST=SUBJECT/"canonical/tests/test_brain_witness_normalization_v3.py"
EXPECTED={
 SOURCE:"a3fd20e58fdbd9b86278b7de0c245de3063dce27",
 NORMALIZED:"892678035303d753b714bd4c0870d0972ec1a7ad",
 RUNTIME:"b056cd99dce49d09060de130eeb08c1d879b5a39",
 TEST:"2e6609a1547a9ae6ac910e0a286e9dedb6d832c3",
}
def blob(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def fail(x): raise SystemExit("VERIFY_FAIL:"+x)
for p,h in EXPECTED.items():
 if blob(p)!=h: fail("BLOB:"+p.name+":"+blob(p)+":"+h)
source=json.loads(SOURCE.read_text())
norm=json.loads(NORMALIZED.read_text())
if source.get("saturation",{}).get("proved_predicate_count")!=14: fail("SOURCE_PROVED_COUNT")
if source.get("saturation",{}).get("unresolved_predicate_count")!=24: fail("SOURCE_UNRESOLVED_COUNT")
sys.path.insert(0,str(SUBJECT))
from canonical.runtime.brain_witness_normalization_verifier_v3 import evaluate
out=evaluate(source,norm,blob(SOURCE))
if out.get("pass") is not True: fail("EVALUATE:"+repr(out))
if out.get("witness_count")!=14: fail("WITNESS_COUNT")
ids={w.get("source_predicate_id") for w in norm.get("witnesses",[])}
required={"LIVEBENCH_IF_GE_65_7","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"}
if not required.issubset(ids): fail("NEW_WITNESSES_MISSING:"+repr(required-ids))
if len(ids)!=14: fail("UNIQUE_WITNESS_COUNT")
for w in norm.get("witnesses",[]):
 if w.get("normalized_target_atoms")!=[]: fail("ATOM_CREDIT")
 if w.get("normalized_metric_bounds")!={}: fail("METRIC_CREDIT")
 if w.get("semantic_implications")!=[]: fail("SEMANTIC_CREDIT")
bad=copy.deepcopy(norm)
bad["witnesses"][0]["normalized_target_atoms"]=["invented"]
if evaluate(source,bad,blob(SOURCE)).get("pass") is not False: fail("INVENTED_ATOM_ACCEPTED")
bad=copy.deepcopy(norm)
bad["witnesses"][0]["normalized_metric_bounds"]={"invented":1}
if evaluate(source,bad,blob(SOURCE)).get("pass") is not False: fail("INVENTED_METRIC_ACCEPTED")
print(json.dumps({
 "schema":"PROJECT_BRAIN_CURRENT_14_WITNESS_NORMALIZATION_INDEPENDENT_VERIFICATION_V1",
 "pass":True,"witness_count":14,"proved_atomic":14,"unresolved_atomic":24,
 "new_witnesses":sorted(required),
 "exact_subject_blobs":{p.name:h for p,h in EXPECTED.items()},
 "semantic_credit_delta":0,"acceptance_credit_delta":0,
 "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False
},sort_keys=True))
