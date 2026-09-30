#!/usr/bin/env python3
import hashlib, json, os, pathlib, re, sqlite3, subprocess, sys, tempfile, threading, time, urllib.parse, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
TASK_REL="canonical/tasks/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
MISSION_REL="canonical/astra_runtime/missions/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
TASK_PATH=ROOT/TASK_REL
MISSION_PATH=ROOT/MISSION_REL
REPORT=ROOT/"openended-sqlite-taska-terminal.json"
TASK_ID="PARENT-OPENENDED-SQLITE-BACKUP-CONSISTENCY-REAL-TASK-20260930-001"
BRAIN_BASE="3ce64b1abb2e6542659617563af48e44eb33f996"
BRAIN_PR=377
CARRIER_CANARY_RUN=36672975512
TASK_BLOB="5d09c9eebcb09612525836e7926bdf297f4bad32"
MISSION_BLOB="c7fa8a9303fdbff1065892d8f8b9b8e540378eea"
EXPECTED_RUNTIME_BLOBS={
 "canonical/runtime/astra_runtime.py":"6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
 "canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
 "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"a22761070ba4d45d3eae7b684d5c66cfb0601669",
 "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
 "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
 "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
 "canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
 "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":"ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
}

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def emit(report):
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True,default=str))

def collect_evidence():
    out=[]
    evid_dir=ROOT/"canonical"/"astra_runtime"/"evidence"
    if evid_dir.is_dir():
        for p in sorted(evid_dir.glob(TASK_ID+"*")):
            if p.is_file():
                raw=p.read_text(encoding="utf-8",errors="replace")
                out.append({
                    "path":str(p.relative_to(ROOT)),
                    "sha256":sha256(p),
                    "content_excerpt":raw[:16000],
                })
    return out

all_expected={TASK_REL:TASK_BLOB,MISSION_REL:MISSION_BLOB,**EXPECTED_RUNTIME_BLOBS}
closure={}
for rel,expected in all_expected.items():
    p=ROOT/rel
    got=git_blob_sha(p) if p.is_file() else None
    closure[rel]={"expected":expected,"observed":got,"match":got==expected}
if not all(x["match"] for x in closure.values()):
    emit({
      "schema":"PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_TERMINAL_V2",
      "status":"CARRIER_CLOSURE_FAIL","brain_base":BRAIN_BASE,"brain_pr":BRAIN_PR,
      "task_id":TASK_ID,"task_executed":False,"execution_count":0,
      "closure":closure,"incremental_spend_usd":0
    })
    raise SystemExit(1)

task=json.loads(TASK_PATH.read_text(encoding="utf-8"))
mission=json.loads(MISSION_PATH.read_text(encoding="utf-8"))
if task.get("task_id")!=TASK_ID or mission.get("mission_id")!=TASK_ID:
    raise SystemExit("TASK_OR_MISSION_ID_MISMATCH")
if mission.get("goal")!=task.get("goal_text"):
    raise SystemExit("MISSION_GOAL_DOES_NOT_EQUAL_FROZEN_TASK_GOAL")
anti=task.get("anti_leakage") or {}
if any(bool(v) for v in anti.values()):
    raise SystemExit("TASK_ANTI_LEAKAGE_CONTRACT_VIOLATED")
constraints=task.get("execution_constraints") or {}
if constraints.get("exactly_one_execution") is not True:
    raise SystemExit("EXACTLY_ONE_EXECUTION_REQUIRED")
if constraints.get("model_dependency_count")!=0:
    raise SystemExit("ZERO_MODEL_DEPENDENCY_REQUIRED")
if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER")!="1":
    raise SystemExit("MODEL_PLANNER_DISABLE_ENV_REQUIRED")

state_path=ROOT/"canonical"/"astra_runtime"/"state"/f"{TASK_ID}.json"
evid_dir=ROOT/"canonical"/"astra_runtime"/"evidence"
preexisting=list(evid_dir.glob(TASK_ID+"*")) if evid_dir.is_dir() else []
if state_path.exists() or preexisting:
    emit({
      "schema":"PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_TERMINAL_V2",
      "status":"PRESTART_REPLAY_GUARD_REJECTED",
      "task_id":TASK_ID,"task_executed":False,"execution_count":0,
      "state_preexisting":state_path.exists(),
      "evidence_preexisting":[str(p.relative_to(ROOT)) for p in preexisting],
      "incremental_spend_usd":0
    })
    raise SystemExit(1)

report={
  "schema":"PROJECT_BRAIN_OPEN_ENDED_PARENT_TASK_A_TERMINAL_V2",
  "brain_base":BRAIN_BASE,
  "brain_pr":BRAIN_PR,
  "carrier_canary_run":CARRIER_CANARY_RUN,
  "task_id":TASK_ID,
  "task_blob":TASK_BLOB,
  "mission_blob":MISSION_BLOB,
  "mission_sha256":sha256(MISSION_PATH),
  "closure":closure,
  "task_executed":True,
  "execution_count":1,
  "source_task_replay":False,
  "incremental_spend_usd":0,
  "model_planner_disabled":True,
  "canonical_cli_entrypoint":True,
}

env=dict(os.environ)
env["ASTRA_DISABLE_MODEL_PLANNER"]="1"
try:
    proc=subprocess.run(
        [sys.executable,"canonical/runtime/astra_runtime.py",MISSION_REL],
        cwd=ROOT,env=env,text=True,capture_output=True,timeout=600
    )
except subprocess.TimeoutExpired as exc:
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "parent_task_completed":False,
      "first_causal_blocker":"CANONICAL_ASTRA_CLI_TIMEOUT",
      "runtime_stdout_excerpt":(exc.stdout or "")[-16000:] if isinstance(exc.stdout,str) else "",
      "runtime_stderr_excerpt":(exc.stderr or "")[-16000:] if isinstance(exc.stderr,str) else "",
      "evidence":collect_evidence(),
      "independent_oracle_executed":False,
    })
    emit(report)
    raise SystemExit(2)

report["runtime_returncode"]=proc.returncode
report["runtime_stdout_excerpt"]=proc.stdout[-16000:]
report["runtime_stderr_excerpt"]=proc.stderr[-16000:]
state=json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
report["runtime_state_status"]=state.get("status")
report["runtime_mission_path"]=state.get("mission_path")
report["runtime_mission_sha256"]=state.get("mission_sha256")
report["mission_path_bound"]=state.get("mission_path")==MISSION_REL and state.get("mission_sha256")==sha256(MISSION_PATH)
report["evidence"]=collect_evidence()

if state.get("status")!="COMPLETE" or proc.returncode!=0:
    blocker=state.get("blocker") or {}
    report.update({
      "status":"FAIL_FIRST_CAUSAL_GAP",
      "parent_task_completed":False,
      "first_causal_blocker":blocker.get("error") or f"RUNTIME_NONCOMPLETE_RETURN_{proc.returncode}",
      "first_causal_stage":blocker.get("phase") or blocker.get("adapter") or "RUNTIME",
      "runtime_blocker":blocker,
      "independent_oracle_executed":False,
      "same_task_replay_allowed":False,
    })
    emit(report)
    raise SystemExit(2)

history=state.get("history") or []
producer_result=history[-1].get("result") if history and isinstance(history[-1],dict) else None
report["producer_result"]=producer_result
if not isinstance(producer_result,dict):
    report.update({
      "status":"FAIL_PRODUCER_OUTPUT_CONTRACT",
      "parent_task_completed":False,
      "first_causal_blocker":"PRODUCER_RESULT_NOT_OBJECT",
      "independent_oracle_executed":False,
      "same_task_replay_allowed":False,
    })
    emit(report)
    raise SystemExit(3)

required=list((task.get("required_output") or {}).get("fields") or [])
def find_payload(obj):
    if isinstance(obj,dict):
        if all(k in obj for k in required):
            return obj
        for v in obj.values():
            got=find_payload(v)
            if got is not None:
                return got
    elif isinstance(obj,list):
        for v in obj:
            got=find_payload(v)
            if got is not None:
                return got
    return None

payload=find_payload(producer_result)
if payload is None:
    report.update({
      "status":"FAIL_PRODUCER_OUTPUT_CONTRACT",
      "parent_task_completed":False,
      "first_causal_blocker":"REQUIRED_OPEN_ENDED_OUTPUT_FIELDS_MISSING",
      "required_fields":required,
      "independent_oracle_executed":False,
      "same_task_replay_allowed":False,
    })
    emit(report)
    raise SystemExit(3)

prov_ok=(
    payload.get("model_dependency_count")==0
    and payload.get("cognition_dependency_class")=="MODEL_INDEPENDENT"
    and payload.get("cognition_provenance_authority")=="ASTRA_RUNTIME_DERIVED_V1"
)
if not prov_ok:
    report.update({
      "status":"FAIL_COGNITION_PROVENANCE",
      "parent_task_completed":False,
      "first_causal_blocker":"RUNTIME_DERIVED_MODEL_INDEPENDENT_PROVENANCE_NOT_PROVEN",
      "producer_payload":payload,
      "independent_oracle_executed":False,
      "same_task_replay_allowed":False,
    })
    emit(report)
    raise SystemExit(3)

def urls_in(obj):
    found=[]
    if isinstance(obj,str):
        found.extend(re.findall(r"https?://[^\s\]\[\)\(\}\{\"']+",obj))
    elif isinstance(obj,dict):
        for v in obj.values():
            found.extend(urls_in(v))
    elif isinstance(obj,list):
        for v in obj:
            found.extend(urls_in(v))
    return found

source_urls=[]
for u in urls_in(payload.get("source_provenance")):
    try:
        p=urllib.parse.urlparse(u)
    except Exception:
        continue
    if p.scheme in ("http","https") and p.netloc:
        source_urls.append(u.rstrip(".,;"))
source_urls=list(dict.fromkeys(source_urls))
primary_sqlite=[u for u in source_urls if urllib.parse.urlparse(u).netloc.lower().endswith("sqlite.org")]

source_checks=[]
for u in primary_sqlite[:4]:
    try:
        req=urllib.request.Request(u,headers={"User-Agent":"Project-Brain-Independent-Oracle/1.0"})
        with urllib.request.urlopen(req,timeout=20) as resp:
            body=resp.read(150000).decode("utf-8","replace")
            source_checks.append({
              "url":u,
              "status":getattr(resp,"status",200),
              "sha256_prefix":hashlib.sha256(body.encode()).hexdigest()[:24],
              "mentions_backup":"backup" in body.lower(),
            })
    except Exception as exc:
        source_checks.append({"url":u,"error":type(exc).__name__+":"+str(exc)[:300]})

def one_trial(index):
    with tempfile.TemporaryDirectory(prefix=f"sqlite-oracle-{index}-") as td:
        src_path=pathlib.Path(td)/"src.db"
        dst_path=pathlib.Path(td)/"dst.db"
        con=sqlite3.connect(src_path)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        con.execute("CREATE TABLE events(txn INTEGER NOT NULL,item INTEGER NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(txn,item))")
        payload_text="x"*512
        for tx in range(300):
            con.executemany("INSERT INTO events(txn,item,payload) VALUES(?,?,?)",[(tx,i,payload_text) for i in range(10)])
        con.commit()
        con.close()

        stop=threading.Event()
        lock=threading.Lock()
        commits={"n":0}
        writer_error={"v":None}
        def writer():
            try:
                w=sqlite3.connect(src_path,timeout=5)
                tx=300
                while not stop.is_set():
                    w.execute("BEGIN IMMEDIATE")
                    w.executemany("INSERT INTO events(txn,item,payload) VALUES(?,?,?)",[(tx,i,payload_text) for i in range(10)])
                    w.commit()
                    tx+=1
                    with lock:
                        commits["n"]+=1
                    time.sleep(0.001)
                w.close()
            except Exception as exc:
                writer_error["v"]=type(exc).__name__+":"+str(exc)
                stop.set()
        th=threading.Thread(target=writer,daemon=True)
        th.start()
        deadline=time.time()+5
        while True:
            with lock:
                n=commits["n"]
            if n>=8 or time.time()>deadline or writer_error["v"]:
                break
            time.sleep(0.005)
        with lock:
            before=commits["n"]
        src=sqlite3.connect(src_path,timeout=5)
        dst=sqlite3.connect(dst_path,timeout=5)
        progress_calls={"n":0}
        def progress(status,remaining,total):
            progress_calls["n"]+=1
            time.sleep(0.001)
        src.backup(dst,pages=1,progress=progress,sleep=0.001)
        dst.commit()
        with lock:
            after=commits["n"]
        stop.set()
        th.join(timeout=5)
        integrity=dst.execute("PRAGMA integrity_check").fetchone()[0]
        counts=dst.execute("SELECT txn,COUNT(*) FROM events GROUP BY txn").fetchall()
        total_rows=dst.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        dst.close()
        src.close()
        bad_groups=[(tx,c) for tx,c in counts if c!=10]
        return {
          "trial":index,
          "writer_commits_before_backup":before,
          "writer_commits_after_backup":after,
          "concurrent_commits_during_backup":max(0,after-before),
          "backup_progress_callbacks":progress_calls["n"],
          "integrity_check":integrity,
          "destination_rows":total_rows,
          "transaction_groups":len(counts),
          "incomplete_transaction_groups":bad_groups[:10],
          "writer_error":writer_error["v"],
          "pass":integrity=="ok" and not bad_groups and after>before and writer_error["v"] is None,
        }

trials=[]
oracle_error=None
try:
    for i in range(3):
        trials.append(one_trial(i+1))
except Exception as exc:
    oracle_error=type(exc).__name__+":"+str(exc)

source_ok=any(x.get("status")==200 and x.get("mentions_backup") for x in source_checks)
experiment_ok=oracle_error is None and len(trials)==3 and all(x.get("pass") for x in trials)
decision_text=json.dumps(payload.get("decision"),sort_keys=True,default=str).lower()
producer_affirms_consistency=("consistent" in decision_text and "not consistent" not in decision_text and "cannot produce" not in decision_text)
oracle_affirms_consistency=experiment_ok
agreement=producer_affirms_consistency==oracle_affirms_consistency
oracle_pass=bool(primary_sqlite and source_ok and experiment_ok and agreement)

report["independent_oracle"]={
  "producer_modules_imported":False,
  "producer_source_urls":source_urls,
  "primary_sqlite_urls":primary_sqlite,
  "source_checks":source_checks,
  "experiment_trials":trials,
  "experiment_error":oracle_error,
  "producer_affirms_consistency":producer_affirms_consistency,
  "oracle_affirms_consistency":oracle_affirms_consistency,
  "conclusion_agreement":agreement,
  "pass":oracle_pass,
}
report["independent_oracle_executed"]=True
report["producer_payload"]=payload
report["same_task_replay_allowed"]=False
if not oracle_pass:
    report.update({
      "status":"FAIL_INDEPENDENT_ORACLE",
      "parent_task_completed":False,
      "first_causal_blocker":"INDEPENDENT_PRIMARY_SOURCE_AND_EXECUTABLE_ORACLE_NOT_FULLY_SATISFIED",
    })
    emit(report)
    raise SystemExit(4)

report.update({
  "status":"PASS_OPEN_ENDED_PARENT_TASK_A",
  "parent_task_completed":True,
  "independent_oracle_verified":True,
  "model_dependency_count":0,
  "cognition_dependency_class":"MODEL_INDEPENDENT",
  "cognition_provenance_authority":"ASTRA_RUNTIME_DERIVED_V1",
})
emit(report)
