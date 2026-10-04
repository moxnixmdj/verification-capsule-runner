#!/usr/bin/env python3
from __future__ import annotations
import hashlib,pathlib,re,shutil

import diagnose_livebench_replay72_v8_structural as v8

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/root2_livebench_if_astra_inference_adapter_v2.py":"dbc895a0e458e411aafd3c96e0ddc2c01e657375",
 "canonical/runtime/instruction_constraint_compiler_v1.py":"a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
 "diagnose_livebench_replay72_v8_structural.py":"bc5bfd7d791b1343cbcf4d09d8f41c6f73ed9f68",
 "livebench_v8_structural_classifier.py":"0c48d463989f8351e3b0a502a174b59ff391ffe8",
 "execute_livebench_if_replay72_v4_candidate.py":"2a57ce896ddbd6819246aab8b44d17a00f36b61e",
}
EPOCH_DIGEST="a71f24f79df6b6be6e910efb1299776ac9fede9e78539577695d6e386fc2eb52"

def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,want in EXPECTED.items():
    p=ROOT/rel
    if not p.is_file() or blob(p)!=want:
        raise SystemExit("FAIL_CLOSED:V10_SUBJECT_BLOB_DRIFT:"+rel)

_original_build=v8.build_template
def _build_v10(base,mod):
    template=_original_build(base,mod)
    for name in (
      "root2_livebench_if_astra_inference_adapter_v2.py",
      "instruction_constraint_compiler_v1.py",
    ):
        src=ROOT/"canonical"/"runtime"/name
        dst=template/"canonical"/"runtime"/name
        shutil.copy2(src,dst)
    return template

v8.build_template=_build_v10
old="from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as adapter"
new="from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as adapter"
if old not in v8.CASE_DRIVER:
    raise SystemExit("FAIL_CLOSED:V8_CASE_DRIVER_IMPORT_NOT_FOUND")
v8.CASE_DRIVER=v8.CASE_DRIVER.replace(old,new,1)

def main(*,authorized=False,activation_blob=None):
    if authorized is not True:
        raise SystemExit("FAIL_CLOSED:VERIFIED_V10_LAUNCHER_REQUIRED")
    if not isinstance(activation_blob,str) or re.fullmatch(r"[0-9a-f]{40}",activation_blob) is None:
        raise SystemExit("FAIL_CLOSED:VERIFIED_V10_ACTIVATION_BLOB_REQUIRED")
    return v8.main(authorized=True,activation_blob=activation_blob)

if __name__=="__main__":
    raise SystemExit("FAIL_CLOSED:VERIFIED_V10_LAUNCHER_REQUIRED")
