import hashlib, json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED_RUNTIME="4677f0e690a5bd97da600613e08df6982dd6c8bf"
EXPECTED_TEST="ead559488855a082e081c7ff6fc761fa3d517842"

def git_blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

runtime=ROOT/"canonical/runtime/livebench_write_only_result_escrow_v1.py"
test=ROOT/"canonical/tests/test_livebench_write_only_result_escrow_v1.py"
assert git_blob(runtime)==EXPECTED_RUNTIME,(git_blob(runtime),EXPECTED_RUNTIME)
assert git_blob(test)==EXPECTED_TEST,(git_blob(test),EXPECTED_TEST)

suite=unittest.defaultTestLoader.loadTestsFromName("canonical.tests.test_livebench_write_only_result_escrow_v1")
result=unittest.TextTestRunner(stream=sys.stderr,verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)

print(json.dumps({
  "schema":"PROJECT_BRAIN_LIVEBENCH_WRITE_ONLY_RESULT_ESCROW_PUBLIC_VERIFIER_V1",
  "status":"PASS",
  "runtime_git_blob_sha":EXPECTED_RUNTIME,
  "test_git_blob_sha":EXPECTED_TEST,
  "test_count":result.testsRun,
  "cryptography_version":"50.0.2",
  "fixed_size_ciphertext_verified":True,
  "separate_test_only_decryption_verified":True,
  "production_decrypt_capability_present":False,
  "plaintext_result_surface_visible":False,
  "result_derived_filename_signal":False,
  "result_derived_artifact_size_signal":False,
  "result_derived_completion_signal":False,
  "terminal_cases_consumed":0,
  "paid_external_model_or_api_used":False
},sort_keys=True))
