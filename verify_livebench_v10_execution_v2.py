#!/usr/bin/env python3
from __future__ import annotations
import ast,hashlib,json,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
  "diagnose_livebench_replay72_v10_formal_routing.py":"56ea114d59f0309bc14ef0504a44bec1f808e876",
  "launch_livebench_v10_formal_routing_atomic.py":"2d3b9ad4e3f4f02af56f402733a8d8bb04ab79c0",
  "canonical/runtime/root2_livebench_if_astra_inference_adapter_v2.py":"dbc895a0e458e411aafd3c96e0ddc2c01e657375",
  "canonical/runtime/instruction_constraint_compiler_v1.py":"a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
  "execute_livebench_if_replay72_v4_candidate.py":"2a57ce896ddbd6819246aab8b44d17a00f36b61e",
  "LIVEBENCH_V10_REPLAY72_ACTIVATION_V1.json":"7a2c2fdc3cc08862850a13667ee2cd2b2e2aae91",
}
EPOCH="a71f24f79df6b6be6e910efb1299776ac9fede9e78539577695d6e386fc2eb52"

def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

for rel,want in EXPECTED.items():
    p=ROOT/rel
    if not p.is_file() or blob(p)!=want:
        raise SystemExit("FAIL_CLOSED:BLOB_MISMATCH:"+rel)

launcher=(ROOT/"launch_livebench_v10_formal_routing_atomic.py").read_text(encoding="utf-8")
wrapper=(ROOT/"diagnose_livebench_replay72_v10_formal_routing.py").read_text(encoding="utf-8")
ast.parse(launcher);ast.parse(wrapper)
main_i=launcher.index("def main():")
verify_i=launcher.index("activation_blob = verify_exact_activation()",main_i)
claim_i=launcher.index("atomic_claim()",verify_i)
import_i=launcher.index("import diagnose_livebench_replay72_v10_formal_routing as diagnostic",claim_i)
run_i=launcher.index("diagnostic.main(authorized=True, activation_blob=activation_blob)",import_i)
if not (verify_i < claim_i < import_i < run_i):
    raise SystemExit("FAIL_CLOSED:CALL_ORDER")

a=json.loads((ROOT/"LIVEBENCH_V10_REPLAY72_ACTIVATION_V1.json").read_text())
if a.get("schema")!="PROJECT_BRAIN_LIVEBENCH_V10_REPLAY72_ACTIVATION_V1":
    raise SystemExit("FAIL_CLOSED:ACTIVATION_SCHEMA")
if a.get("target_predicate")!="LIVEBENCH_IF_GE_65_7":
    raise SystemExit("FAIL_CLOSED:TARGET")
if a.get("epoch_digest_sha256")!=EPOCH:
    raise SystemExit("FAIL_CLOSED:EPOCH")
if a.get("launcher_git_blob_sha")!=EXPECTED["launch_livebench_v10_formal_routing_atomic.py"]:
    raise SystemExit("FAIL_CLOSED:LAUNCHER_BINDING")
scope=a.get("replay_scope") or {}
auth=a.get("authority") or {}
if not (
    scope.get("already_exposed_prefix_only") is True
    and scope.get("replay_prefix_limit")==72
    and scope.get("case_73_or_later") is False
    and auth.get("replay72") is True
    and auth.get("new_case_exposure") is False
    and auth.get("fresh_reality") is False
    and auth.get("promotion") is False
    and auth.get("acceptance_credit") is False
):
    raise SystemExit("FAIL_CLOSED:SCOPE_OR_AUTHORITY")

if "REPLAY_LIMIT=200" in launcher or "REPLAY_LIMIT=200" in wrapper:
    raise SystemExit("FAIL_CLOSED:SCOPE_EXPANSION")
print("PASS:LIVEBENCH_V10_EXECUTION_V2_ZERO_CASE_VERIFICATION")
