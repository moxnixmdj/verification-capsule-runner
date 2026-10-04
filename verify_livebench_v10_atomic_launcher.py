#!/usr/bin/env python3
from __future__ import annotations
import ast,hashlib,pathlib,re

ROOT=pathlib.Path(__file__).resolve().parent
LAUNCHER=ROOT/"launch_livebench_v10_formal_routing_atomic.py"
WRAPPER=ROOT/"diagnose_livebench_replay72_v10_formal_routing.py"
CANDIDATE=ROOT/"canonical/governance/LIVEBENCH_V10_FORMAL_ROUTING_REPLAY72_CANDIDATE_V1.json"
EXPECTED_LAUNCHER="952bec0697b7ed30157a7ea3541e8a942ba184e5"
EXPECTED_WRAPPER="d13bbb89fa336524627de08f4c78d0e703fb4bfa"
EXPECTED_CANDIDATE="7d42814e46abda96eed0fb1929bef5a829bd2236"
EPOCH="a71f24f79df6b6be6e910efb1299776ac9fede9e78539577695d6e386fc2eb52"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for p,want,label in (
    (LAUNCHER,EXPECTED_LAUNCHER,"LAUNCHER"),
    (WRAPPER,EXPECTED_WRAPPER,"WRAPPER"),
    (CANDIDATE,EXPECTED_CANDIDATE,"CANDIDATE"),
):
    if not p.is_file() or blob(p)!=want:
        raise SystemExit("FAIL_CLOSED:"+label+"_BLOB")

lt=LAUNCHER.read_text(encoding="utf-8")
wt=WRAPPER.read_text(encoding="utf-8")
ast.parse(lt); ast.parse(wt)

launcher_checks=[
 f'EPOCH_DIGEST="{EPOCH}"' in lt,
 'CLAIM_REF="refs/heads/livebench-v10-claims/"+EPOCH_DIGEST' in lt,
 'method="POST"' in lt,
 'if e.code==422: fail("ATOMIC_ONE_USE_CLAIM_ALREADY_EXISTS")' in lt,
 'if status!=201: fail("ATOMIC_ONE_USE_CLAIM_NOT_201")' in lt,
 'LIVEBENCH_V10_ACTIVATION_BLOB' in lt,
]
if not all(launcher_checks):
    raise SystemExit("FAIL_CLOSED:LAUNCHER_CONTRACT")
if not lt.index("atomic_claim()") < lt.index("import diagnose_livebench_replay72_v10_formal_routing as diagnostic") < lt.index("diagnostic.main(authorized=True,activation_blob=activation_blob)"):
    raise SystemExit("FAIL_CLOSED:CLAIM_ORDER")
for forbidden in ("download_dataset","parse_population","test.parquet","case_73"):
    if forbidden in lt:
        raise SystemExit("FAIL_CLOSED:LAUNCHER_DATASET_OR_SCOPE_ACCESS:"+forbidden)

wrapper_checks=[
 'root2_livebench_if_astra_inference_adapter_v2.py":"dbc895a0e458e411aafd3c96e0ddc2c01e657375"' in wt,
 'instruction_constraint_compiler_v1.py":"a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f"' in wt,
 f'EPOCH_DIGEST="{EPOCH}"' in wt,
 'v8.CASE_DRIVER=v8.CASE_DRIVER.replace(old,new,1)' in wt,
 'return v8.main(authorized=True,activation_blob=activation_blob)' in wt,
]
if not all(wrapper_checks):
    raise SystemExit("FAIL_CLOSED:WRAPPER_CONTRACT")
if "replay_prefix_limit" in wt or "73" in wt:
    raise SystemExit("FAIL_CLOSED:WRAPPER_SCOPE_MUTATION")
print("PASS:LIVEBENCH_V10_WRAPPER_AND_ATOMIC_LAUNCHER_ZERO_CASE_VERIFICATION")
