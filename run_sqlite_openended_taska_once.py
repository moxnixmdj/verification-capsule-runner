#!/usr/bin/env python3
import hashlib, json, os, pathlib, re, sqlite3, subprocess, sys, tempfile, threading, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_REL = "canonical/astra_runtime/missions/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
TASK_REL = "canonical/tasks/PARENT_OPENENDED_SQLITE_BACKUP_CONSISTENCY_REAL_TASK_20260930_001.json"
MISSION_ID = "PARENT-OPENENDED-SQLITE-BACKUP-CONSISTENCY-REAL-TASK-20260930-001"
ARM_REL = "ARM_SQLITE_OPENENDED_TASKA_20260930_V1"
REPORT_PATH = ROOT / "sqlite-openended-taska-terminal.json"
BRAIN_MAIN = "3ce64b1abb2e6542659617563af48e44eb33f996"
RUNNER_MAIN = "eff796468741f509650904cd7fbaf8eab3958ff1"

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_pypi_library_acquisition.py": "6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
    TASK_REL: "5d09c9eebcb09612525836e7926bdf297f4bad32",
    MISSION_REL: "fd14b94c31e4f53851d6ad86fc7b59e65359e859",
}

def blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def safe_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def emit(report):
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, default=str))

def first_blocker(state, proc):
    if isinstance(state, dict):
        for key in ("blocker", "error", "first_causal_blocker", "failure"):
            v = state.get(key)
            if v:
                return str(v)
    return (proc.stderr[-5000:] or proc.stdout[-5000:] or "CANONICAL_RUNTIME_NONZERO").strip()

def collect_urls(value):
    found = []
    if isinstance(value, dict):
        for v in value.values():
            found.extend(collect_urls(v))
    elif isinstance(value, list):
        for v in value:
            found.extend(collect_urls(v))
    elif isinstance(value, str):
        found.extend(re.findall(r"https?://[^\s\"'<>]+", value))
    return found

def collect_key_text(value, keys=("decision","conclusion","answer","result")):
    found = []
    if isinstance(value, dict):
        for k, v in value.items():
            if str(k).lower() in keys and isinstance(v, (str,int,float,bool)):
                found.append(str(v))
            found.extend(collect_key_text(v, keys))
    elif isinstance(value, list):
        for v in value:
            found.extend(collect_key_text(v, keys))
    return found

def independent_fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"ProjectBrain-SQLite-Independent-Oracle/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read(1500000)
        return {
            "requested_url": url,
            "final_url": r.geturl(),
            "status": int(getattr(r, "status", 200)),
            "content_type": str(r.headers.get("Content-Type") or ""),
            "body_excerpt": raw[:200000].decode("utf-8", "replace"),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }

def run_independent_sqlite_experiment():
    with tempfile.TemporaryDirectory() as td:
        src = pathlib.Path(td) / "source.db"
        dst = pathlib.Path(td) / "backup.db"
        c = sqlite3.connect(src)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("CREATE TABLE a(id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        c.execute("CREATE TABLE b(id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        rows=[(i, ("seed-%06d" % i) + "x"*1024) for i in range(1, 2501)]
        c.executemany("INSERT INTO a VALUES(?,?)", rows)
        c.executemany("INSERT INTO b VALUES(?,?)", rows)
        c.commit()
        c.close()

        stop = threading.Event()
        started = threading.Event()
        writer_stats={"commits":0,"last_id":2500}
        def writer():
            conn=sqlite3.connect(src, timeout=5)
            i=2501
            started.set()
            try:
                while not stop.is_set() and i < 2900:
                    payload=("live-%06d" % i) + "y"*1024
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute("INSERT INTO a VALUES(?,?)",(i,payload))
                    conn.execute("INSERT INTO b VALUES(?,?)",(i,payload))
                    conn.commit()
                    writer_stats["commits"] += 1
                    writer_stats["last_id"] = i
                    i += 1
                    time.sleep(0.002)
            finally:
                conn.close()

        t=threading.Thread(target=writer, daemon=True)
        t.start()
        started.wait(5)
        source_conn=sqlite3.connect(src, timeout=5)
        dest_conn=sqlite3.connect(dst)
        backup_started=time.time()
        source_conn.backup(dest_conn, pages=4, sleep=0.002)
        backup_finished=time.time()
        stop.set()
        t.join(5)
        source_conn.close()
        dest_conn.close()

        check=sqlite3.connect(dst)
        integrity=check.execute("PRAGMA integrity_check").fetchone()[0]
        ca=check.execute("SELECT COUNT(*) FROM a").fetchone()[0]
        cb=check.execute("SELECT COUNT(*) FROM b").fetchone()[0]
        mismatch=check.execute("SELECT COUNT(*) FROM a LEFT JOIN b USING(id) WHERE b.id IS NULL OR a.payload<>b.payload").fetchone()[0]
        max_a=check.execute("SELECT COALESCE(MAX(id),0) FROM a").fetchone()[0]
        contiguous=check.execute("SELECT COUNT(*) FROM a").fetchone()[0] == max_a
        check.close()
        return {
            "sqlite_version": sqlite3.sqlite_version,
            "writer_commits_during_window": writer_stats["commits"],
            "writer_last_id": writer_stats["last_id"],
            "backup_duration_s": round(backup_finished-backup_started, 6),
            "destination_integrity_check": integrity,
            "destination_a_rows": ca,
            "destination_b_rows": cb,
            "destination_pair_mismatch_count": mismatch,
            "destination_ids_contiguous_from_1": contiguous,
            "oracle_consistent": integrity=="ok" and ca==cb and mismatch==0 and contiguous,
        }

report={
    "schema":"PROJECT_BRAIN_SQLITE_OPENENDED_TASKA_TERMINAL_V1",
    "brain_main":BRAIN_MAIN,
    "runner_main":RUNNER_MAIN,
    "mission_id":MISSION_ID,
    "execution_count":0,
    "task_executed":False,
    "incremental_spend_usd":0,
    "model_dependency_count":0,
    "canonical_runtime_entrypoint":"canonical/runtime/astra_runtime.py",
    "same_task_replay_forbidden":True,
}

for rel, expected in EXPECTED_BLOBS.items():
    p=ROOT/rel
    observed=blob_sha(p) if p.is_file() else None
    if observed != expected:
        report.update({"status":"CARRIER_CLOSURE_FAIL","path":rel,"expected_blob":expected,"observed_blob":observed,"replay_allowed":True})
        emit(report); raise SystemExit(1)

if not (ROOT/ARM_REL).is_file():
    report.update({"status":"NOT_ARMED","replay_allowed":True})
    emit(report); raise SystemExit(1)

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    report.update({"status":"CARRIER_POLICY_FAIL","first_causal_blocker":"MODEL_PLANNER_NOT_DISABLED","replay_allowed":True})
    emit(report); raise SystemExit(1)

mission=safe_json(ROOT/MISSION_REL)
task=safe_json(ROOT/TASK_REL)
if not isinstance(mission,dict) or mission.get("mission_id") != MISSION_ID or not isinstance(task,dict) or task.get("task_id") != MISSION_ID:
    report.update({"status":"CARRIER_POLICY_FAIL","first_causal_blocker":"TASK_OR_MISSION_ID_INVALID","replay_allowed":True})
    emit(report); raise SystemExit(1)

state_path=ROOT/"canonical/astra_runtime/state"/(MISSION_ID+".json")
if state_path.exists():
    report.update({"status":"FRESHNESS_FAIL_PRESTART","first_causal_blocker":"PREEXISTING_PARENT_STATE","replay_allowed":False})
    emit(report); raise SystemExit(1)

report["execution_count"]=1
report["task_executed"]=True
proc=subprocess.run(
    [sys.executable, str(ROOT/"canonical/runtime/astra_runtime.py"), MISSION_REL],
    cwd=ROOT, text=True, capture_output=True, timeout=600,
    env={**os.environ,"ASTRA_DISABLE_MODEL_PLANNER":"1"},
)
report["producer_returncode"]=int(proc.returncode)
report["producer_stdout_tail"]=proc.stdout[-16000:]
report["producer_stderr_tail"]=proc.stderr[-16000:]
state=safe_json(state_path) if state_path.is_file() else None
report["producer_state"]=state

if proc.returncode != 0:
    report.update({
        "status":"FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed":False,
        "independent_oracle_executed":False,
        "parent_capability_credit_authorized":False,
        "replay_allowed":False,
        "first_causal_stage":"CANONICAL_RUNTIME",
        "first_causal_blocker":first_blocker(state,proc),
    })
    emit(report); raise SystemExit(2)

if not isinstance(state,dict) or state.get("status")!="COMPLETE":
    report.update({
        "status":"FAIL_FIRST_CAUSAL_GAP","parent_task_completed":False,
        "independent_oracle_executed":False,"parent_capability_credit_authorized":False,
        "replay_allowed":False,"first_causal_stage":"CANONICAL_RUNTIME_STATE",
        "first_causal_blocker":"RUNTIME_RETURNED_ZERO_WITHOUT_COMPLETE_STATE",
    })
    emit(report); raise SystemExit(3)

urls=sorted(set(collect_urls(state) + collect_urls(proc.stdout)))
primary=[]
fetches=[]
for u in urls[:20]:
    try:
        f=independent_fetch(u)
        fetches.append({k:v for k,v in f.items() if k!="body_excerpt"})
        host=re.sub(r"^www\.","",re.sub(r"^https?://","",f["final_url"]).split("/")[0].lower())
        body=f["body_excerpt"].lower()
        if (host=="sqlite.org" or host.endswith(".sqlite.org")) and ("backup" in body or "online backup" in body):
            primary.append(f["final_url"])
    except Exception as exc:
        fetches.append({"requested_url":u,"error":type(exc).__name__+":"+str(exc)})

oracle_exp=run_independent_sqlite_experiment()
decision_text="\n".join(collect_key_text(state)).lower()
semantic_compare={
    "producer_decision_fields_found": bool(decision_text.strip()),
    "producer_decision_mentions_concurrent": "concurrent" in decision_text,
    "producer_decision_mentions_consistent": "consistent" in decision_text,
}
oracle_ok=bool(primary) and oracle_exp["oracle_consistent"] and semantic_compare["producer_decision_fields_found"]

report["independent_oracle"]={
    "producer_cited_urls":urls,
    "producer_cited_primary_sqlite_urls":primary,
    "refetches":fetches,
    "sqlite_experiment":oracle_exp,
    "semantic_compare":semantic_compare,
}
if not oracle_ok:
    report.update({
        "status":"FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed":False,
        "independent_oracle_executed":True,
        "parent_capability_credit_authorized":False,
        "replay_allowed":False,
        "first_causal_stage":"INDEPENDENT_ORACLE",
        "first_causal_blocker":"PRIMARY_SOURCE_OR_EXPERIMENT_OR_PRODUCER_DECISION_VERIFICATION_INCOMPLETE",
    })
    emit(report); raise SystemExit(4)

report.update({
    "status":"PASS_PRODUCER_AND_INDEPENDENT_ORACLE",
    "parent_task_completed":True,
    "independent_oracle_executed":True,
    "independent_oracle_verified":True,
    "incremental_spend_usd":0,
    "model_dependency_count":0,
    "replay_allowed":False,
    "parent_capability_credit_authorized":False,
    "next_required_action":"RECONCILE_EXACT_RECEIPT_IN_CANONICAL_BRAIN_BEFORE_ANY_CAPABILITY_CREDIT_OR_PROMOTION",
})
emit(report)
