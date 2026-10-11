#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,subprocess,sys,tomllib
from pathlib import Path,PurePosixPath
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]
C=ROOT/"capsules/tb_science_rank23_20261011_v1"
for p in (str(ROOT),str(C)):
    if p not in sys.path: sys.path.insert(0,p)

from execution_guard.rank23_claim_bound_identity_v1 import resolve_claim_bound_identity
from canonical.runtime import dna_storage_task_adapter_v1 as adapter

DATASET_TASK="terminal-bench-science/dna-storage-codec"
SLOT_ID=DATASET_TASK+"::trial-0"
TASK_DIGEST="sha256:bde6852289db3f5474aedc96c54aca201d11be6c61f4fef019998b2b689e65ac"
OUT=ROOT/"RANK23_PRESTART_GUARD.json"

def _sha_text(value:str)->str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def _artifact_source(raw:Any)->str|None:
    service="main"
    if isinstance(raw,str):
        source=raw.strip()
    elif isinstance(raw,Mapping):
        allowed={"source","destination","exclude","service"}
        if any(k not in allowed for k in raw): raise RuntimeError("TASK_ARTIFACT_CONFIG_FIELD_INVALID")
        source=raw.get("source")
        if not isinstance(source,str): raise RuntimeError("TASK_ARTIFACT_SOURCE_INVALID")
        source=source.strip()
        service=raw.get("service","main")
        if not isinstance(service,str) or not service: raise RuntimeError("TASK_ARTIFACT_SERVICE_INVALID")
        dest=raw.get("destination")
        if dest is not None:
            if not isinstance(dest,str) or "\\" in dest: raise RuntimeError("TASK_ARTIFACT_DESTINATION_INVALID")
            if dest:
                p=PurePosixPath(dest)
                if p.is_absolute() or any(x==".." for x in p.parts): raise RuntimeError("TASK_ARTIFACT_DESTINATION_INVALID")
        exclude=raw.get("exclude",[])
        if not isinstance(exclude,list) or any(not isinstance(x,str) for x in exclude):
            raise RuntimeError("TASK_ARTIFACT_EXCLUDE_INVALID")
    else:
        raise RuntimeError("TASK_ARTIFACT_INVALID")
    if service!="main": return None
    p=PurePosixPath(source)
    if not p.is_absolute() or any(x==".." for x in p.parts): raise RuntimeError("TASK_ARTIFACT_SOURCE_NOT_ABSOLUTE")
    return source

def _artifact_sources(task_toml:Path)->list[str]:
    data=tomllib.loads(task_toml.read_text(encoding="utf-8"))
    rows=data.get("artifacts",[])
    if rows is None: rows=[]
    if not isinstance(rows,list) or len(rows)>16: raise RuntimeError("TASK_ARTIFACTS_INVALID")
    out=[]
    for raw in rows:
        src=_artifact_source(raw)
        if src is not None and src not in out: out.append(src)
    if not out: raise RuntimeError("TASK_ARTIFACTS_REQUIRED")
    return out

def _write_outputs(row:dict[str,Any])->None:
    p=os.environ.get("GITHUB_OUTPUT")
    if not p: return
    with open(p,"a",encoding="utf-8") as fh:
        fh.write("guard_pass="+("true" if row.get("pass") else "false")+"\n")
        fh.write("task_path="+str(row.get("task_path") or "")+"\n")
        fh.write("logical_attempt_id="+str(row.get("logical_attempt_id") or "")+"\n")

def main()->int:
    result={
        "schema":"PROJECT_BRAIN_TB_SCIENCE_RANK23_PRESTART_GUARD_V1",
        "status":"PRESTART",
        "slot_id":SLOT_ID,
        "task_digest":TASK_DIGEST,
        "pass":False,
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
            root=ROOT,
            surface_rel="execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json",
            expected_slot_id=SLOT_ID,
            expected_task_digest=TASK_DIGEST,
        )
        result["logical_attempt_id"]=identity["logical_attempt_id"]
        result["execution_claim_binding_digest"]=identity["execution_claim_binding_digest"]
        root=(ROOT/"rank23_task_read").resolve()
        root.mkdir(parents=True,exist_ok=True)
        subprocess.run([
            "harbor","task","download",
            DATASET_TASK+"@"+TASK_DIGEST,
            "--output-dir",str(root),"--overwrite","--export",
        ],check=True)
        task_path=root/"dna-storage-codec"
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
        plan=adapter.resolve_plan(goal,artifacts)
        result["resolved_plan"]={
            "mode":plan.mode,
            "input_path":plan.input_path,
            "output_path":plan.output_path,
            "evidence":list(plan.evidence),
        }
        result["pass"]=True
        result["status"]="PASS__RANK23_EXACT_DIGEST_TASK_READ__DONOR_FREE_DNA_CONTRACT_QUALIFIED__TASK_NOT_STARTED"
        rc=0
    except Exception as exc:
        result["error_type"]=type(exc).__name__
        result["error"]=str(exc)
        result["status"]="PRESTART_ABORT_NONCONSUMING__"+type(exc).__name__
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    _write_outputs(result)
    print(json.dumps(result,sort_keys=True))
    return rc

if __name__=="__main__":
    raise SystemExit(main())
