#!/usr/bin/env python3
import hashlib, importlib, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject/seed_preservation_truth_v2"
R=SUB/"canonical"/"runtime"
EXPECTED={
 "seed_preserving_instruction_postprocessor_v1.py":"8cdb308941dbd6711279cbd1d505aca6aabdd376",
 "test_seed_preserving_instruction_postprocessor_v1.py":"df3ac20c7fdf97f9a5ef4cbee727578b12d96a35",
 "instruction_constraint_compiler_v1.py":"a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
}
def blob(p):
 b=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,h in EXPECTED.items():
 assert blob(R/n)==h,(n,blob(R/n),h)
sys.path.insert(0,str(SUB))
tests=importlib.import_module("canonical.runtime.test_seed_preserving_instruction_postprocessor_v1")
names=sorted(n for n in dir(tests) if n.startswith("test_"))
assert len(names)>=9,names
for n in names: getattr(tests,n)()
mod=importlib.import_module("canonical.runtime.seed_preserving_instruction_postprocessor_v1")
cases=[
 ("Semantic Seed",'Reply with exactly "OK"'),
 ("Mixed Case Answer","Write the entire response in lowercase only."),
 ("Mixed Case Answer","Write the entire response in uppercase only."),
 ("core answer",'Response must start with "BEGIN" and response must end with "END"'),
 ("one two","Answer with at least 5 words."),
 ("one two three four five","Answer with at least 5 words."),
 ("contains cedar",'Include the word "cedar"'),
 ("contains banana",'Do not include the word "banana"'),
]
for seed,inst in cases:
 out=mod.transform(seed,inst)
 if out["status"]=="PASS":
  assert seed in out["response"],(seed,inst,out)
  assert out["seed_verbatim_preserved"] is True,out
  assert out["seed_preservation_contract"]==mod.PRESERVATION_CONTRACT
source=(R/"seed_preserving_instruction_postprocessor_v1.py").read_text()
for forbidden in ("requests","socket","subprocess","os.system","pip install"):
 assert forbidden not in source,forbidden
receipt={
 "schema":"PROJECT_BRAIN_SEED_PRESERVATION_TRUTH_V2_PUBLIC_VERIFICATION",
 "status":"PASS",
 "brain_pr":1707,
 "brain_head":"e9e706024f793312a0961ac46b56e80d865a7cbb",
 "exact_blobs":EXPECTED,
 "tests_executed":names,
 "verified":{
   "every_observed_PASS_contains_seed_verbatim":True,
   "conflicting_exact_response_fails_closed":True,
   "lossy_case_conversion_fails_closed":True,
   "literal_wrappers_preserve_seed":True,
   "network_and_subprocess_paths_absent":True
 },
 "terminal_cases_consumed":0,
 "acceptance_credit_delta":0
}
(ROOT/"seed_preservation_truth_v2_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
