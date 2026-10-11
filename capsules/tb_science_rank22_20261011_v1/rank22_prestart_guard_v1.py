#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,subprocess,sys,tomllib
from pathlib import Path
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]
C=ROOT/"capsules/tb_science_rank22_20261011_v1"
for p in (str(ROOT),str(C)):
    if p not in sys.path: sys.path.insert(0,p)

from execution_guard.rank22_claim_bound_identity_v1 import resolve_claim_bound_identity
from canonical.runtime import tb_science_zero_model_scientific_kernel_v1 as kernel

SCHEMA="PROJECT_BRAIN_TB_SCIENCE_RANK22_ZERO_MODEL_PRESTART_GUARD_V1"
DATASET_TASK="terminal-bench-science/rv-astrometry-fitting"
SLOT_ID=DATASET_TASK+"::trial-0"
TASK_DIGEST="sha256:8e086e1f7245067eaa9a67c259c1519204fa058d8664983066cd582ef258a1ea"
SURFACE_REL="execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
OUT=ROOT/"RANK22_PRESTART_GUARD.json"

def _sha_text(x:str)->str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()

def _write_outputs(row:dict[str,Any])->None:
    target=os.environ.get("GITHUB_OUTPUT")
    if not target: return
    with open(target,"a",encoding="utf-8") as fh:
        fh.write("guard_pass="+("true" if row.get("pass") else "false")+"\n")
        fh.write("task_path="+str(row.get("task_path") or "")+"\n")
        fh.write("logical_attempt_id="+str(row.get("logical_attempt_id") or "")+"\n")

def _artifact_sources(task_toml:Path)->list[str]:
    data=tomllib.loads(task_toml.read_text(encoding="utf-8"))
    rows=data.get("artifacts",[])
    if rows is None: rows=[]
    if not isinstance(rows,list) or len(rows)>16:
        raise RuntimeError("TASK_ARTIFACTS_INVALID")
    out=[]
    for raw in rows:
        if isinstance(raw,str):
            src=raw.strip(); service="main"
        elif isinstance(raw,Mapping):
            if any(k not in {"source","destination","exclude","service"} for k in raw):
                raise RuntimeError("TASK_ARTIFACT_CONFIG_FIELD_INVALID")
            src=raw.get("source"); service=raw.get("service","main")
            if not isinstance(src,str): raise RuntimeError("TASK_ARTIFACT_SOURCE_INVALID")
            src=src.strip()
        else:
            raise RuntimeError("TASK_ARTIFACT_INVALID")
        if service!="main": continue
        if not src.startswith("/") or ".." in Path(src).parts:
            raise RuntimeError("TASK_ARTIFACT_SOURCE_NOT_ABSOLUTE")
        if src not in out: out.append(src)
    if not out:
        raise RuntimeError("TASK_ARTIFACTS_REQUIRED")
    return out

def main()->int:
    result={
        "schema":SCHEMA,
        "status":"PREEXPOSURE_ABORT_NONCONSUMING__GUARD_NOT_COMPLETED",
        "pass":False,
        "slot_id":SLOT_ID,
        "task_digest":TASK_DIGEST,
        "task_read":False,
        "task_started":False,
        "benchmark_trials_consumed":0,
        "model_dependency_count":0,
        "external_model_runtime_calls":0,
        "incremental_spend_usd":0,
    }
    rc=1
    try:
        identity=resolve_claim_bound_identity(
            root=ROOT,surface_rel=SURFACE_REL,
            expected_slot_id=SLOT_ID,expected_task_digest=TASK_DIGEST,
        )
        result.update(identity)
        root=(ROOT/"rank22_task_read").resolve()
        root.mkdir(parents=True,exist_ok=True)
        subprocess.run([
            "harbor","task","download",
            DATASET_TASK+"@"+TASK_DIGEST,
            "--output-dir",str(root),"--overwrite","--export",
        ],check=True)
        task_path=root/"rv-astrometry-fitting"
        instruction_path=task_path/"instruction.md"
        task_toml=task_path/"task.toml"
        if not instruction_path.is_file() or not task_toml.is_file():
            raise RuntimeError("DIGEST_PINNED_TASK_EXPORT_INCOMPLETE")
        raw=instruction_path.read_text(encoding="utf-8")
        goal=raw.strip()
        if not goal: raise RuntimeError("DIGEST_PINNED_TASK_INSTRUCTION_EMPTY")
        result["task_read"]=True
        result["task_path"]=str(task_path)
        result["instruction_sha256"]=_sha_text(raw)
        result["runtime_goal_sha256"]=_sha_text(goal)
        artifacts=_artifact_sources(task_toml)
        result["authoritative_artifacts"]=artifacts
        result["artifact_count"]=len(artifacts)
        route=kernel.classify(goal,SLOT_ID)
        result["route_evidence"]=route
        if route.get("route")!="SHARED_PERIOD_HARMONIC_FITTING":
            raise RuntimeError("ZERO_MODEL_ROUTE_NOT_QUALIFIED_FOR_EXACT_TASK")
        if route.get("model_dependency_count")!=0:
            raise RuntimeError("ZERO_MODEL_ROUTE_MODEL_DEPENDENCY_NONZERO")
        result["pass"]=True
        result["status"]="PASS__RANK22_EXACT_DIGEST_TASK_READ__ZERO_MODEL_ROUTE_QUALIFIED__TASK_NOT_STARTED"
        rc=0
    except Exception as exc:
        result["error_type"]=type(exc).__name__
        result["error"]=str(exc)
        result["status"]="PREEXPOSURE_ABORT_NONCONSUMING__"+type(exc).__name__
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    _write_outputs(result)
    print(json.dumps(result,sort_keys=True))
    return rc

if __name__=="__main__":
    raise SystemExit(main())
