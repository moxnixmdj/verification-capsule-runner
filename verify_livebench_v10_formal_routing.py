#!/usr/bin/env python3
from __future__ import annotations
import ast,hashlib,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "diagnose_livebench_replay72_v10_formal_routing.py":"56ea114d59f0309bc14ef0504a44bec1f808e876",
 "launch_livebench_v10_formal_routing_atomic.py":"d7cd5b5c90f19ef02c1f27afa1629ed6af5500d9",
 "canonical/runtime/root2_livebench_if_astra_inference_adapter_v2.py":"dbc895a0e458e411aafd3c96e0ddc2c01e657375",
 "canonical/runtime/instruction_constraint_compiler_v1.py":"a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
 "diagnose_livebench_replay72_v8_structural.py":"bc5bfd7d791b1343cbcf4d09d8f41c6f73ed9f68",
 "livebench_v8_structural_classifier.py":"0c48d463989f8351e3b0a502a174b59ff391ffe8",
 "execute_livebench_if_replay72_v4_candidate.py":"2a57ce896ddbd6819246aab8b44d17a00f36b61e",
}
EPOCH="a71f24f79df6b6be6e910efb1299776ac9fede9e78539577695d6e386fc2eb52"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,want in EXPECTED.items():
    p=ROOT/rel
    if not p.is_file() or blob(p)!=want:
        raise SystemExit("FAIL_CLOSED:BLOB_MISMATCH:"+rel)

w=(ROOT/"diagnose_livebench_replay72_v10_formal_routing.py").read_text(encoding="utf-8")
l=(ROOT/"launch_livebench_v10_formal_routing_atomic.py").read_text(encoding="utf-8")
ast.parse(w);ast.parse(l)
checks=[
 'root2_livebench_if_astra_inference_adapter_v2 as adapter' in w,
 'a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f' in w,
 f'EPOCH_DIGEST="{EPOCH}"' in w,
 f'EPOCH_DIGEST="{EPOCH}"' in l,
 'CLAIM_REF="refs/heads/livebench-v10-claims/"+EPOCH_DIGEST' in l,
 'if e.code==422: fail("ATOMIC_ONE_USE_CLAIM_ALREADY_EXISTS")' in l,
 'LIVEBENCH_V10_ACTIVATION_BLOB' in l,
]
if not all(checks): raise SystemExit("FAIL_CLOSED:CONTRACT")
if not l.index("atomic_claim()") < l.index("import diagnose_livebench_replay72_v10_formal_routing as diagnostic") < l.index("diagnostic.main(authorized=True,activation_blob=activation_blob)"):
    raise SystemExit("FAIL_CLOSED:ORDER")
for text in (w,l):
    for forbidden in ("REPLAY_LIMIT=200","case_73","parse_population(" if text is l else "__NEVER__"):
        if forbidden!="__NEVER__" and forbidden in text:
            raise SystemExit("FAIL_CLOSED:SCOPE_EXPANSION:"+forbidden)
print("PASS:LIVEBENCH_V10_WRAPPER_AND_ATOMIC_LAUNCHER_ZERO_CASE_VERIFICATION")
