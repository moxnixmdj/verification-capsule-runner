#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"seed_preserving_instruction_postprocessor_v1"
RUNTIME=SUB/"canonical"/"runtime"
FILES={
    RUNTIME/"seed_preserving_instruction_postprocessor_v1.py":"6762868d0954102e996ab240c85fdfee22e3f219",
    RUNTIME/"test_seed_preserving_instruction_postprocessor_v1.py":"39881bd8fc9f6390b84a572bd01fa51a5a0b1039",
    RUNTIME/"instruction_constraint_compiler_v1.py":"a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
}

def blob(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for path,expected in FILES.items():
    got=blob(path)
    assert got==expected,(str(path),got,expected)

source=(RUNTIME/"seed_preserving_instruction_postprocessor_v1.py").read_text(encoding="utf-8")
for forbidden in ("urllib","requests","socket","subprocess","os.system","pip install"):
    assert forbidden not in source,forbidden

sys.path.insert(0,str(SUB))
tests=importlib.import_module("canonical.runtime.test_seed_preserving_instruction_postprocessor_v1")
names=sorted(n for n in dir(tests) if n.startswith("test_"))
assert len(names)==7,names
for name in names:
    getattr(tests,name)()

mod=importlib.import_module("canonical.runtime.seed_preserving_instruction_postprocessor_v1")
extra=mod.transform("alpha beta","Answer with at least 4 words.")
assert extra["status"]=="FAIL_CLOSED"
assert extra["error"]=="UNSAFE_TRANSFORMATION_REQUIRED"
assert extra["network_used"] is False
assert extra["incremental_spend_usd"]==0
assert extra["terminal_authority"] is False

receipt={
 "schema":"PROJECT_BRAIN_SEED_PRESERVING_INSTRUCTION_POSTPROCESSOR_PUBLIC_VERIFICATION_V1",
 "status":"PASS",
 "subject_git_blobs":{p.name:h for p,h in FILES.items()},
 "synthetic_tests_executed":names,
 "test_count":len(names),
 "verified":{
   "safe_structural_transforms_pass":True,
   "unsafe_semantic_invention_or_deletion_fails_closed":True,
   "exact_postvalidation_used":True,
   "network_path_absent":True,
   "subprocess_path_absent":True,
   "incremental_spend_usd":0,
   "terminal_authority":False
 },
 "hard_nonclaims":[
   "NO_GENERAL_NATURAL_LANGUAGE_INSTRUCTION_FOLLOWING_PROOF",
   "NO_LIVEBENCH_ACCEPTANCE_CREDIT",
   "NO_TERMINAL_CASE_DATA_USED"
 ]
}
path=ROOT/"seed_preserving_instruction_postprocessor_verification_receipt.json"
path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(receipt,sort_keys=True))
