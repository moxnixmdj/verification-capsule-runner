#!/usr/bin/env python3
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
C=ROOT/"capsules/tb_science_rank23_20261011_v1"
ACTIVATION=C/"ACTIVATE_RANK23_V1_PR.json"
OUT=ROOT/"RANK23_ZERO_EXPOSURE_RESEAL_VERIFY_V1.json"

def main()->int:
    errors=[]
    if ACTIVATION.exists(): errors.append("ACTIVATION_MUST_BE_ABSENT")
    proc=subprocess.run(
        [sys.executable,str(C/"rank23_execution_preflight_v1.py"),"--allow-staged"],
        cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
    )
    if proc.returncode!=0: errors.append("STAGED_PREFLIGHT_FAILED")
    receipt={}
    try: receipt=json.loads((ROOT/"RANK23_EXECUTION_PREFLIGHT_V1.json").read_text(encoding="utf-8"))
    except Exception as exc: errors.append("PREFLIGHT_RECEIPT_MISSING:"+type(exc).__name__)
    if receipt.get("pass") is not True: errors.append("PREFLIGHT_NOT_PASS")
    if receipt.get("task_read") is not False or receipt.get("task_started") is not False:
        errors.append("ZERO_EXPOSURE_ACCOUNTING_INVALID")
    if receipt.get("model_dependency_count")!=0 or receipt.get("external_model_runtime_calls")!=0:
        errors.append("MODEL_DEPENDENCY_NONZERO")
    row={
        "schema":"PROJECT_BRAIN_TB_SCIENCE_RANK23_ZERO_EXPOSURE_RESEAL_VERIFY_V1",
        "status":"PASS__RANK23_DONOR_FREE_DNA_RESEAL__ACTIVATION_ABSENT__TASK_UNREAD_UNSTARTED" if not errors else "FAIL_CLOSED",
        "pass":not errors,"errors":errors,
        "preflight_stdout":proc.stdout[-8000:],
        "slot_id":"terminal-bench-science/dna-storage-codec::trial-0",
        "task_digest":"sha256:bde6852289db3f5474aedc96c54aca201d11be6c61f4fef019998b2b689e65ac",
        "task_read":False,"task_started":False,"benchmark_trials_consumed":0,
        "model_dependency_count":0,"external_model_runtime_calls":0,
        "execution_authority":False,"activation_authority":False,
        "acceptance_credit_delta":0,"terminal_credit_delta":0,
    }
    OUT.write_text(json.dumps(row,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(row,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
