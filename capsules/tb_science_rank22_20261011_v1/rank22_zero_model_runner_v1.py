#!/usr/bin/env python3
from __future__ import annotations
import json,os,subprocess,sys,time,tomllib
from pathlib import Path,PurePosixPath
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]
C=ROOT/"capsules/tb_science_rank22_20261011_v1"
for p in (str(ROOT),str(C)):
    if p not in sys.path: sys.path.insert(0,p)

from execution_guard import terminal_agent_start_barrier_v1 as start_barrier
from execution_guard.rank22_claim_bound_identity_v1 import resolve_claim_bound_identity

SCHEMA="PROJECT_BRAIN_TB_SCIENCE_RANK22_ZERO_MODEL_BARRIER_RUNNER_V1"
SLOT_ID="terminal-bench-science/rv-astrometry-fitting::trial-0"
TASK_DIGEST="sha256:8e086e1f7245067eaa9a67c259c1519204fa058d8664983066cd582ef258a1ea"
BARRIER_REL=Path("RANK22_AGENT_START_BARRIER")
READY_REL=BARRIER_REL/"AGENT_READY.json"
COMMIT_REL=BARRIER_REL/"START_COMMITTED.json"
CAS_RECEIPT=ROOT/"RANK22_START_CAS_V1.json"
RUNNER_RECEIPT=ROOT/"RANK22_ZERO_MODEL_RUNNER_RECEIPT_V1.json"
HARBOR_LOG=ROOT/"RANK22_ZERO_MODEL_HARBOR_RUN.log"
READY_TIMEOUT_S=1800.0
POLL_S=0.2

class BarrierRunnerError(RuntimeError): pass

def _artifact_source(raw:Any)->str|None:
    service="main"
    if isinstance(raw,str):
        source=raw.strip()
    elif isinstance(raw,Mapping):
        allowed={"source","destination","exclude","service"}
        if any(k not in allowed for k in raw): raise BarrierRunnerError("TASK_ARTIFACT_CONFIG_FIELD_INVALID")
        source=raw.get("source")
        if not isinstance(source,str): raise BarrierRunnerError("TASK_ARTIFACT_SOURCE_INVALID")
        source=source.strip(); service=raw.get("service","main")
        if not isinstance(service,str) or not service: raise BarrierRunnerError("TASK_ARTIFACT_SERVICE_INVALID")
        dest=raw.get("destination")
        if dest is not None:
            if not isinstance(dest,str) or "\\" in dest: raise BarrierRunnerError("TASK_ARTIFACT_DESTINATION_INVALID")
            if dest:
                p=PurePosixPath(dest)
                if p.is_absolute() or any(x==".." for x in p.parts): raise BarrierRunnerError("TASK_ARTIFACT_DESTINATION_INVALID")
        exclude=raw.get("exclude",[])
        if not isinstance(exclude,list) or any(not isinstance(x,str) for x in exclude):
            raise BarrierRunnerError("TASK_ARTIFACT_EXCLUDE_INVALID")
    else:
        raise BarrierRunnerError("TASK_ARTIFACT_INVALID")
    if service!="main": return None
    p=PurePosixPath(source)
    if not p.is_absolute() or any(x==".." for x in p.parts): raise BarrierRunnerError("TASK_ARTIFACT_SOURCE_NOT_ABSOLUTE")
    return source

def _task_artifacts_json()->str:
    task_path=os.environ.get("TASK_PATH") or ""
    task_toml=Path(task_path)/"task.toml"
    if not task_toml.is_file(): raise BarrierRunnerError("TASK_TOML_REQUIRED")
    try: data=tomllib.loads(task_toml.read_text(encoding="utf-8"))
    except Exception as exc: raise BarrierRunnerError("TASK_TOML_INVALID") from exc
    rows=data.get("artifacts",[])
    if rows is None: rows=[]
    if not isinstance(rows,list) or len(rows)>16: raise BarrierRunnerError("TASK_ARTIFACTS_INVALID")
    out=[]
    for raw in rows:
        src=_artifact_source(raw)
        if src is not None and src not in out: out.append(src)
    if not out: raise BarrierRunnerError("TASK_ARTIFACTS_REQUIRED")
    return json.dumps(out,sort_keys=True,separators=(",",":"))

def _identity()->dict[str,str]:
    return resolve_claim_bound_identity(
        root=ROOT,surface_rel="execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json",
        expected_slot_id=SLOT_ID,expected_task_digest=TASK_DIGEST,
    )

def _child_env()->dict[str,str]:
    env=dict(os.environ)
    env.pop("GH_TOKEN",None); env.pop("GITHUB_TOKEN",None)
    env["PYTHONPATH"]=str(ROOT)+os.pathsep+str(C)
    env["BRAIN_AGENT_START_BARRIER_DIR"]=str(ROOT/BARRIER_REL)
    env["BRAIN_SLOT_ID"]=SLOT_ID
    env["BRAIN_TASK_DIGEST"]=TASK_DIGEST
    env["BRAIN_TASK_ARTIFACTS_JSON"]=_task_artifacts_json()
    carried=str(os.environ.get("BRAIN_LOGICAL_ATTEMPT_ID") or "").strip()
    identity=_identity()
    if carried!=identity["logical_attempt_id"]: raise BarrierRunnerError("LOGICAL_ATTEMPT_ID_NOT_CLAIM_BOUND")
    env["BRAIN_LOGICAL_ATTEMPT_ID"]=carried
    env["BRAIN_EXECUTION_CLAIM_BINDING_DIGEST"]=identity["execution_claim_binding_digest"]
    env["BRAIN_AGENT_START_BARRIER_TIMEOUT_S"]=str(int(READY_TIMEOUT_S))
    return env

def _harbor_command()->list[str]:
    task_path=os.environ.get("TASK_PATH") or ""
    if not task_path: raise BarrierRunnerError("TASK_PATH_REQUIRED")
    safe_id=os.environ.get("SAFE_ID") or "rv-astrometry-fitting-trial-0"
    jobs=ROOT/"jobs"/safe_id; jobs.mkdir(parents=True,exist_ok=True)
    return [
        "harbor","run","-p",task_path,
        "-a","canonical.runtime.harbor_science_zero_model_agent_v1:HarborScienceZeroModelAgent",
        "-k","1","-n","1","-r","0",
        "--agent-timeout-multiplier","1.0",
        "--environment-build-timeout-multiplier","1.0",
        "--verifier-timeout-multiplier","1.0",
        "--job-name",safe_id,"--jobs-dir",str(jobs),
    ]

def _acquire()->None:
    proc=subprocess.run([sys.executable,str(C/"rank22_start_cas_v1.py"),"--acquire"],cwd=ROOT,env=dict(os.environ),check=False)
    if proc.returncode!=0: raise BarrierRunnerError("START_CAS_ACQUIRE_FAILED")

def _cas_acquired()->bool:
    try: row=json.loads(CAS_RECEIPT.read_text(encoding="utf-8"))
    except Exception: return False
    return isinstance(row,dict) and row.get("acquired") is True and row.get("task_started") is True

def _release()->None:
    start_barrier.release_from_cas(
        ready_path=ROOT/READY_REL,cas_receipt_path=CAS_RECEIPT,output_path=ROOT/COMMIT_REL,
    )

def _terminate(proc:Any)->None:
    try:
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=10)
            except Exception: proc.kill(); proc.wait(timeout=10)
    except Exception: pass

def _write(row:dict[str,Any])->None:
    RUNNER_RECEIPT.write_text(json.dumps(row,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def main()->int:
    barrier=ROOT/BARRIER_REL; barrier.mkdir(parents=True,exist_ok=True)
    for p in (ROOT/READY_REL,ROOT/COMMIT_REL):
        if p.exists(): p.unlink()
    receipt={
        "schema":SCHEMA,"slot_id":SLOT_ID,"task_digest":TASK_DIGEST,
        "status":"PRESTART","harbor_launched":False,"agent_ready":False,
        "start_cas_acquired":False,"agent_released":False,"task_started":False,
        "benchmark_trials_consumed":0,"github_credentials_exposed_to_harbor":False,
        "model_dependency_count":0,"external_model_runtime_calls":0,
        "incremental_spend_usd":0,
    }
    proc=None; log=None
    try:
        child=_child_env()
        if "GH_TOKEN" in child or "GITHUB_TOKEN" in child: raise BarrierRunnerError("CHILD_GITHUB_CREDENTIAL_STRIP_FAILED")
        log=open(HARBOR_LOG,"wb")
        proc=subprocess.Popen(_harbor_command(),cwd=ROOT,env=child,stdout=log,stderr=subprocess.STDOUT)
        receipt["harbor_launched"]=True
        deadline=time.monotonic()+READY_TIMEOUT_S
        ready=ROOT/READY_REL
        while not ready.is_file():
            rc=proc.poll()
            if rc is not None: raise BarrierRunnerError("HARBOR_EXITED_BEFORE_AGENT_READY:"+str(rc))
            if time.monotonic()>=deadline: raise BarrierRunnerError("AGENT_READY_TIMEOUT__NO_START_COMMIT")
            time.sleep(POLL_S)
        receipt["agent_ready"]=True
        _acquire()
        if not _cas_acquired(): raise BarrierRunnerError("START_CAS_RECEIPT_NOT_ACQUIRED")
        receipt["start_cas_acquired"]=True; receipt["task_started"]=True; receipt["benchmark_trials_consumed"]=1
        _release()
        if not (ROOT/COMMIT_REL).is_file(): raise BarrierRunnerError("START_COMMIT_RELEASE_FILE_MISSING")
        receipt["agent_released"]=True
        rc=int(proc.wait())
        receipt["harbor_returncode"]=rc
        receipt["status"]="HARBOR_COMPLETE" if rc==0 else "POSTSTART_HARBOR_NONZERO"
        _write(receipt)
        return rc
    except Exception as exc:
        committed=bool(receipt.get("start_cas_acquired")) or _cas_acquired()
        if committed:
            receipt["start_cas_acquired"]=True; receipt["task_started"]=True; receipt["benchmark_trials_consumed"]=1
            receipt["status"]="POSTSTART_ABORT__IRREVERSIBLE"
        else:
            receipt["task_started"]=False; receipt["benchmark_trials_consumed"]=0
            receipt["status"]="PRESTART_ABORT__NONCONSUMING"
        receipt["error_type"]=type(exc).__name__; receipt["error"]=str(exc)
        if proc is not None: _terminate(proc)
        _write(receipt)
        return 1
    finally:
        if log is not None: log.close()

if __name__=="__main__":
    raise SystemExit(main())
