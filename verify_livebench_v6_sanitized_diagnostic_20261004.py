#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_v6_sanitized_diagnostic_20261004"
DIAG=SUB/"diagnose_livebench_v6_sanitized_blockers.py"
ORIG=SUB/"execute_livebench_if_replay72_v4_candidate.py"
EXPECTED_DIAG="00b1cc439ef957928633f0c3e7f625721524bbb1"
EXPECTED_ORIG="2a57ce896ddbd6819246aab8b44d17a00f36b61e"

def blob(p):
 d=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

assert blob(DIAG)==EXPECTED_DIAG
assert blob(ORIG)==EXPECTED_ORIG=="2a57ce896ddbd6819246aab8b44d17a00f36b61e"

spec=importlib.util.spec_from_file_location("diag",DIAG)
assert spec and spec.loader
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

assert m.REPLAY_LIMIT==72

# Privacy proof on a synthetic frozen-runtime source universe.
with tempfile.TemporaryDirectory() as td:
 root=pathlib.Path(td)
 runtime=root/"canonical"/"runtime"
 runtime.mkdir(parents=True)
 (runtime/"x.py").write_text(
   'class DemoBlocker(RuntimeError):\n'
   '    pass\n'
   'ERR="CAPABILITY_ACQUISITION_REQUIRED"\n'
   'ERR2="APT_ORIGIN_MISSION_PATH_INVALID"\n',
   encoding="utf-8",
 )
 codes,classes=m.build_source_allowlist(root)
 assert "CAPABILITY_ACQUISITION_REQUIRED" in codes
 assert "APT_ORIGIN_MISSION_PATH_INVALID" in codes
 assert "DemoBlocker" in classes

 secret="SECRET_PROMPT_TEXT_DO_NOT_LEAK_928374"
 raw=(
   "Traceback: DemoBlocker: CAPABILITY_ACQUISITION_REQUIRED "
   +secret+" USER_PRIVATE_LITERAL APT_ORIGIN_MISSION_PATH_INVALID"
 )
 safe=m.sanitize_hidden_text(raw,codes,classes)
 encoded=json.dumps(safe,sort_keys=True)
 assert secret not in encoded
 assert "USER_PRIVATE_LITERAL" not in encoded
 assert "CAPABILITY_ACQUISITION_REQUIRED" in safe["source_error_codes"]
 assert "APT_ORIGIN_MISSION_PATH_INVALID" in safe["source_error_codes"]
 assert "DemoBlocker" in safe["source_exception_classes"]
 assert safe["sha256"]==hashlib.sha256(raw.encode()).hexdigest()
 assert safe["bytes"]==len(raw.encode())

# An uppercase prompt-looking token cannot escape unless present in frozen source.
safe2=m.sanitize_hidden_text(
 "UNKNOWN_TERMINAL_SECRET_TOKEN RuntimeError: x",codes,classes
)
assert "UNKNOWN_TERMINAL_SECRET_TOKEN" not in safe2["source_error_codes"]

# The diagnostic cannot execute without separate authority.
try:
 m.main(authorized=False,activation_blob=None)
 raise AssertionError("unauthorized diagnostic execution accepted")
except SystemExit as exc:
 assert "SANITIZED_DIAGNOSTIC_AUTHORITY_REQUIRED" in str(exc)

src=DIAG.read_text(encoding="utf-8")
for forbidden in (
 "print(cp.stderr",
 "print(cp.stdout",
 '"raw_stderr":',
 '"raw_stdout":',
 '"prompt":q["turns"][0]',
 '"response":answer',
):
 assert forbidden not in src,forbidden

# Explicit nonclaims remain machine-visible.
for required in (
 '"new_case_exposure_count":0',
 '"raw_prompt_persisted":False',
 '"raw_response_persisted":False',
 '"raw_stdout_persisted":False',
 '"raw_stderr_persisted":False',
 '"acceptance_credit_delta":0',
 '"root1_reclassification_authority":False',
):
 assert required in src,required

print(json.dumps({
 "status":"PASS__LIVEBENCH_V6_SANITIZED_DIAGNOSTIC_PREEXECUTION",
 "diagnostic_blob":EXPECTED_DIAG,
 "original_executor_blob":EXPECTED_ORIG,
 "terminal_cases_consumed":0,
 "new_case_authority":False,
 "privacy_adversarial_secret_excluded":True,
 "source_derived_allowlist_verified":True,
 "unauthorized_execution_fails_closed":True,
},sort_keys=True))
