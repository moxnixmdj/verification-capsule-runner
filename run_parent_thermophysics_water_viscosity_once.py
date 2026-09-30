#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, math, os, pathlib, re, subprocess, sys, traceback, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
TASK_ID="PARENT-THERMOPHYSICS-WATER-VISCOSITY-OPEN-RESEARCH-TASK-A-20260930-002"
TASK_REL="canonical/tasks/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
MISSION_REL="canonical/astra_runtime/missions/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
RESULT_REL="canonical/astra_runtime/tmp/PARENT_THERMOPHYSICS_WATER_VISCOSITY_RESULT.json"
REPORT=ROOT/"thermophysics-parent-task-terminal.json"
START=ROOT/".THERMOPHYSICS_PARENT_TASK_STARTED"
BRAIN_MAIN="fc07395c387563cbb2b3dfdc3b14fd80239a080b"

EXPECTED_BLOBS={
  TASK_REL:"dc92f7b8e76889c754576dd1a5036e7a7c62b8eb",
  MISSION_REL:"982b883b353b937d8500bd9b70c1929c33313393",
  "canonical/runtime/astra_runtime.py":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
  "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
  "canonical/runtime/auto_capability_acquisition.py":"fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
  "canonical/runtime/auto_apt_cli_acquisition.py":"0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
  "canonical/runtime/auto_pypi_library_acquisition.py":"6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
  "canonical/runtime/capability_discovery.py":"b9e7423ab24bf2da98869b02d782e791a779892a",
  "canonical/runtime/verify_pending_cli_binding.py":"a6b028c25d79d2dff59c87e3b3ad91d9fe934dae",
  "canonical/runtime/promote_pending_binding.py":"f100c0d1ce5a4b07af0175035c3122d816459b0b",
}

def git_blob_sha(path:pathlib.Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def emit(obj):
    REPORT.write_text(json.dumps(obj,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    print(json.dumps(obj,indent=2,sort_keys=True,default=str))

def load_json(path):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None

def urls_in(value):
    found=[]
    def walk(x):
        if isinstance(x,dict):
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
        elif isinstance(x,str):
            for u in re.findall(r"https?://[^\\s\\]\\[<>{}\"']+",x):
                u=u.rstrip(".,;:)")
                if u not in found: found.append(u)
    walk(value); return found

def numeric_value(value):
    if isinstance(value,bool) or value is None: return None
    if isinstance(value,(int,float)) and math.isfinite(float(value)): return float(value)
    if isinstance(value,dict):
        for k in ("value","numeric_value","viscosity","amount"):
            if k in value:
                v=numeric_value(value[k])
                if v is not None:return v
        for v0 in value.values():
            v=numeric_value(v0)
            if v is not None:return v
    if isinstance(value,str):
        m=re.search(r"[-+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][-+]?\\d+)?",value)
        if m:
            try:return float(m.group())
            except ValueError:return None
    return None

def decision_bool(value):
    if isinstance(value,bool):return value
    s=str(value).strip().lower()
    if any(x in s for x in ("not less than half","no","false","does not")): return False
    if any(x in s for x in ("less than half","yes","true")): return True
    return None

def source_contains_value(text,target):
    nums=[]
    for s in re.findall(r"[-+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][-+]?\\d+)?",text):
        try:
            x=float(s)
            if math.isfinite(x):nums.append(x)
        except ValueError:pass
    for x in nums:
        for scale in (1.0,1e-3,1e3):
            y=x*scale
            if abs(y-target)<=max(1e-9,abs(target)*0.005):
                return True
    return False

closure={}
for rel,expected in EXPECTED_BLOBS.items():
    p=ROOT/rel
    observed=git_blob_sha(p) if p.is_file() else None
    closure[rel]={"expected":expected,"observed":observed,"match":observed==expected}
if not all(v["match"] for v in closure.values()):
    emit({"schema":"PROJECT_BRAIN_THERMOPHYSICS_PARENT_TERMINAL_V1","status":"CARRIER_CLOSURE_FAIL","task_id":TASK_ID,"task_executed":False,"execution_count":0,"closure":closure,"incremental_spend_usd":0})
    raise SystemExit(1)

if os.environ.get("GITHUB_RUN_ATTEMPT","1")!="1":
    emit({"schema":"PROJECT_BRAIN_THERMOPHYSICS_PARENT_TERMINAL_V1","status":"RERUN_FORBIDDEN","task_id":TASK_ID,"task_executed":False,"execution_count":0,"github_run_attempt":os.environ.get("GITHUB_RUN_ATTEMPT"),"incremental_spend_usd":0})
    raise SystemExit(1)
try:
    fd=os.open(START,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600); os.close(fd)
except FileExistsError:
    emit({"schema":"PROJECT_BRAIN_THERMOPHYSICS_PARENT_TERMINAL_V1","status":"LOCAL_SINGLEFLIGHT_ABORT","task_id":TASK_ID,"task_executed":False,"execution_count":0,"incremental_spend_usd":0})
    raise SystemExit(1)

task=load_json(ROOT/TASK_REL)
mission=load_json(ROOT/MISSION_REL)
if not task or not mission or task.get("task_id")!=TASK_ID or mission.get("mission_id")!=TASK_ID:
    emit({"schema":"PROJECT_BRAIN_THERMOPHYSICS_PARENT_TERMINAL_V1","status":"IDENTITY_PREFLIGHT_FAIL","task_id":TASK_ID,"task_executed":False,"execution_count":0,"incremental_spend_usd":0})
    raise SystemExit(1)

env=os.environ.copy()
env["ASTRA_DISABLE_MODEL_PLANNER"]="1"
try:
    proc=subprocess.run([sys.executable,"canonical/runtime/astra_runtime.py",MISSION_REL],cwd=ROOT,text=True,capture_output=True,timeout=600,env=env)
except Exception as exc:
    emit({"schema":"PROJECT_BRAIN_THERMOPHYSICS_PARENT_TERMINAL_V1","status":"EXECUTION_EXCEPTION","task_id":TASK_ID,"task_executed":True,"execution_count":1,"error":type(exc).__name__+":"+str(exc),"traceback_tail":traceback.format_exc()[-6000:],"incremental_spend_usd":0})
    raise SystemExit(2)

state_path=ROOT/"canonical/astra_runtime/state"/f"{TASK_ID}.json"
blocker_path=ROOT/"canonical/astra_runtime/evidence"/f"{TASK_ID}__BLOCKER.json"
result_path=ROOT/RESULT_REL
state=load_json(state_path) or {}
blocker=load_json(blocker_path) or state.get("blocker") or {}
result=load_json(result_path) if result_path.is_file() else None
producer_complete=(proc.returncode==0 and state.get("status")=="COMPLETE" and isinstance(result,dict))
first_blocker=(blocker.get("error") if isinstance(blocker,dict) else None) or (state.get("blocker",{}).get("error") if isinstance(state.get("blocker"),dict) else None)

oracle={"executed":False,"status":"NOT_RUN_PRODUCER_NOT_COMPLETE"}
terminal_status="PASS_PARENT_PRODUCER_AND_INDEPENDENT_ORACLE" if producer_complete else "FAIL_FIRST_CAUSAL_GAP"
exit_code=0 if producer_complete else 2

if producer_complete:
    oracle={"executed":True,"status":"FAIL_CLOSED"}
    try:
        v20=numeric_value(result.get("viscosity_20c"))
        v40=numeric_value(result.get("viscosity_40c"))
        claimed_ratio=numeric_value(result.get("ratio_40c_to_20c"))
        claimed_decision=decision_bool(result.get("decision"))
        if v20 is None or v40 is None or v20<=0 or v40<=0:
            raise RuntimeError("PRODUCER_NUMERIC_FIELDS_INVALID")
        recomputed=v40/v20
        independent_decision=(recomputed<0.5)
        if claimed_ratio is None or abs(claimed_ratio-recomputed)>max(1e-12,abs(recomputed)*1e-9):
            raise RuntimeError("PRODUCER_RATIO_MISMATCH")
        if claimed_decision is None or claimed_decision!=independent_decision:
            raise RuntimeError("PRODUCER_DECISION_MISMATCH")
        urls=urls_in(result.get("source_provenance"))
        if not urls: raise RuntimeError("NO_SOURCE_URL_IN_PROVENANCE")
        receipts=[]
        seen20=seen40=False
        for url in urls[:8]:
            req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-IndependentOracle/1"})
            with urllib.request.urlopen(req,timeout=30) as resp:
                raw=resp.read(12_000_000)
                final_url=resp.geturl()
                code=getattr(resp,"status",None)
            txt=raw.decode("utf-8","replace")
            m20=source_contains_value(txt,v20); m40=source_contains_value(txt,v40)
            seen20=seen20 or m20; seen40=seen40 or m40
            receipts.append({"url":url,"final_url":final_url,"http_status":code,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"matches_viscosity_20c":m20,"matches_viscosity_40c":m40})
        if not (seen20 and seen40): raise RuntimeError("CITED_SOURCE_NUMERIC_VALUES_NOT_INDEPENDENTLY_RECOVERED")
        oracle={"executed":True,"status":"VERIFIED","viscosity_20c":v20,"viscosity_40c":v40,"recomputed_ratio":recomputed,"independent_decision_less_than_half":independent_decision,"source_receipts":receipts}
        terminal_status="PASS_PARENT_PRODUCER_AND_INDEPENDENT_ORACLE"
        exit_code=0
    except Exception as exc:
        oracle={"executed":True,"status":"FAILED","error":type(exc).__name__+":"+str(exc)}
        terminal_status="PRODUCER_COMPLETE__INDEPENDENT_ORACLE_FAILED__NO_PROMOTION"
        exit_code=3

report={
 "schema":"PROJECT_BRAIN_THERMOPHYSICS_PARENT_TERMINAL_V1",
 "status":terminal_status,
 "brain_main":BRAIN_MAIN,
 "task_id":TASK_ID,
 "domain":task.get("domain"),
 "task_executed":True,
 "execution_count":1,
 "source_task_replay":False,
 "runtime_returncode":proc.returncode,
 "runtime_state_status":state.get("status"),
 "first_causal_blocker":first_blocker,
 "result_path":RESULT_REL if result_path.is_file() else None,
 "producer_complete":producer_complete,
 "independent_oracle":oracle,
 "model_planner_disabled":True,
 "incremental_spend_usd":0,
 "user_device_used":False,
 "parent_promotion_authorized":bool(producer_complete and oracle.get("status")=="VERIFIED"),
 "closure":closure,
 "stdout_tail":proc.stdout[-10000:],
 "stderr_tail":proc.stderr[-10000:],
}
emit(report)
raise SystemExit(exit_code)
