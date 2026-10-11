#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TB_SCIENCE_RANK23_SLOT_RECEIPT_V1"
SLOT_ID="terminal-bench-science/dna-storage-codec::trial-0"
TASK_DIGEST="sha256:bde6852289db3f5474aedc96c54aca201d11be6c61f4fef019998b2b689e65ac"
SAFE_ID="dna-storage-codec-trial-0"
OUT=ROOT/(SAFE_ID+"__SLOT_RECEIPT_V1.json")

def _read(path:Path)->dict[str,Any]:
    try:
        v=json.loads(path.read_text(encoding="utf-8"))
        return v if isinstance(v,dict) else {}
    except Exception:
        return {}

def _sha(path:Path)->str|None:
    try: return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception: return None

def _results()->list[tuple[Path,dict[str,Any]]]:
    base=ROOT/"jobs"/SAFE_ID
    out=[]
    if not base.exists(): return out
    for p in base.rglob("result.json"):
        row=_read(p)
        if row: out.append((p,row))
    return out

def _reward(rows:list[tuple[Path,dict[str,Any]]])->float|None:
    vals=[]
    for _p,row in rows:
        vr=row.get("verifier_result")
        rewards=vr.get("rewards") if isinstance(vr,dict) else None
        raw=rewards.get("reward") if isinstance(rewards,dict) else None
        if isinstance(raw,(int,float)) and not isinstance(raw,bool):
            vals.append(float(raw))
    if not vals: return None
    if len(set(vals))!=1: raise RuntimeError("MULTIPLE_DISTINCT_REWARDS")
    return vals[0]

def main()->int:
    guard=_read(ROOT/"RANK23_PRESTART_GUARD.json")
    check=_read(ROOT/"RANK23_START_CAS_CHECK_V1.json")
    cas=_read(ROOT/"RANK23_START_CAS_V1.json")
    runner=_read(ROOT/"RANK23_DNA_STORAGE_RUNNER_RECEIPT_V1.json")
    task_read=guard.get("task_read") is True
    task_started=(cas.get("acquired") is True and cas.get("task_started") is True) or runner.get("task_started") is True
    consumed=1 if task_started else 0
    rows=_results()
    reward=_reward(rows) if task_started else None
    if not task_started:
        status="PREEXPOSURE_ABORT_NONCONSUMING" if not task_read else "EXPOSED_PRESTART_ABORT_NONCONSUMING__NO_RETRY"
    else:
        status="SUCCESS" if reward is not None and reward>=1.0 else "FINAL_ZERO"
        if reward is None: reward=0.0
    hashes=[]
    for p,_ in rows:
        hashes.append({"path":str(p.relative_to(ROOT)),"sha256":_sha(p)})
    receipt={
        "schema":SCHEMA,"date":"2026-10-11","status":status,
        "slot_id":SLOT_ID,"task_digest":TASK_DIGEST,
        "logical_attempt_id":guard.get("logical_attempt_id") or cas.get("logical_attempt_id"),
        "execution_claim_binding_digest":guard.get("execution_claim_binding_digest") or cas.get("execution_claim_binding_digest"),
        "task_read":task_read,"task_started":task_started,
        "durable_start_cas_acquired":cas.get("acquired") is True,
        "benchmark_trials_consumed":consumed,
        "result_present":bool(rows),"reward":reward,
        "prestart_guard_status":guard.get("status"),
        "start_absence_check_status":check.get("status"),
        "start_cas_status":cas.get("status"),
        "runner_status":runner.get("status"),
        "harbor_returncode":runner.get("harbor_returncode"),
        "model_dependency_count":0,
        "external_model_runtime_calls":0,
        "network_dependency_count":0,
        "result_hashes":hashes,
        "retry_authority":False,"replacement_authority":False,"replay_authority":False,
        "acceptance_credit_delta":0,"terminal_credit_delta":0,"incremental_spend_usd":0,
    }
    OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
