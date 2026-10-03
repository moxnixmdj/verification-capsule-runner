#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/retrieval_v4_router_epoch_executor_v1.py":"c5799537acdddc34199f3318b62fac3db83a707f",
 "canonical/tests/test_retrieval_v4_router_epoch_executor_v1.py":"e3a6a59635a762b992971e2b77a4ecc02cbd8403",
 "canonical/runtime/public_source_federation_v2.py":"32f0443bfb1859168e14f7266a3b5b3c99a40f45",
 "canonical/runtime/federated_retrieval_epoch_gate_v1.py":"0a36836c8f0428338a9931b757090a26f73c2672",
 "canonical/runtime/residual_witness_backend_router_v1.py":"578c5f87901a458b12d7df984e0a6a525d367456",
 "canonical/runtime/residual_witness_retrieval_compiler_v1.py":"9daa8d590f3356b3fc51eccf75c56cbf515239e4",
 "canonical/runtime/public_source_federation_v1.py":"3f69b3e8371fe3e5abc173c6c9fe17e9003a938b",
}

def git_blob(path:str)->str:
    return subprocess.check_output(["git","rev-parse","HEAD:"+path],cwd=ROOT,text=True).strip()

def main()->int:
    mismatches={p:[git_blob(p),sha] for p,sha in EXPECTED.items() if git_blob(p)!=sha}
    if mismatches:
        print(json.dumps({"status":"FAIL","blob_mismatches":mismatches},sort_keys=True))
        return 1
    cp=subprocess.run(
      [sys.executable,"-m","unittest","canonical.tests.test_retrieval_v4_router_epoch_executor_v1","-v"],
      cwd=ROOT,text=True,capture_output=True
    )
    if cp.returncode!=0:
        print(cp.stdout); print(cp.stderr,file=sys.stderr)
        return cp.returncode
    out={
      "schema":"PROJECT_BRAIN_RETRIEVAL_V4_ROUTER_EPOCH_EXECUTOR_PUBLIC_RUNNER_VERIFICATION_V1",
      "status":"PASS",
      "exact_brain_blobs":EXPECTED,
      "verified":{
        "all_selected_v2_cells_receive_verified_router_receipts":True,
        "epoch_gate_consumption_requires_complete_receipt_matrix":True,
        "off_domain_candidates_dropped":True,
        "transient_failures_preserve_unknown":True,
        "candidate_authority_leak_rejected":True,
        "zero_credit_preserved":True,
      },
      "acceptance_credit_delta":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
    }
    print(json.dumps(out,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
