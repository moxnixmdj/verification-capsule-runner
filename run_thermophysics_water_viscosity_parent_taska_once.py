#!/usr/bin/env python3
import hashlib, json, math, os, pathlib, re, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
MISSION_REL = "canonical/astra_runtime/missions/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
TASK_REL = "canonical/tasks/PARENT_THERMOPHYSICS_WATER_VISCOSITY_OPEN_RESEARCH_TASK_A_20260930_002.json"
MISSION_ID = "PARENT-THERMOPHYSICS-WATER-VISCOSITY-OPEN-RESEARCH-TASK-A-20260930-002"
RESULT_REL = "canonical/astra_runtime/tmp/PARENT_THERMOPHYSICS_WATER_VISCOSITY_RESULT.json"
REPORT_REL = "thermophysics-water-viscosity-parent-taska-terminal.json"
BRAIN_MAIN = "fc07395c387563cbb2b3dfdc3b14fd80239a080b"
RUNNER_BASE = "eff796468741f509650904cd7fbaf8eab3958ff1"

EXPECTED_BLOBS = {
    "canonical/runtime/astra_runtime.py": "6cb668bcc5a00665ea541fc5b6adf494f37ad1c9",
    "canonical/runtime/goal_compiler.py": "4b61fe911471854ec15c7900816f61e9e55f602e",
    "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json": "a22761070ba4d45d3eae7b684d5c66cfb0601669",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/auto_apt_cli_acquisition.py": "0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
    "canonical/runtime/auto_pypi_library_acquisition.py": "6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
    "canonical/runtime/python_codec_probe.py": "fc8b5005a9888422e3cb61f6cf0bd147c740ec84",
    "canonical/runtime/verify_pending_cli_binding.py": "a6b028c25d79d2dff59c87e3b3ad91d9fe934dae",
    "canonical/runtime/promote_pending_binding.py": "f100c0d1ce5a4b07af0175035c3122d816459b0b",
    "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py": "6385b469f1287c971217dcac58af2ffebd81f9fd",
    "canonical/runtime/bound_capabilities/grounded_executable_composition.py": "8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
    "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py": "ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
    MISSION_REL: "982b883b353b937d8500bd9b70c1929c33313393",
    TASK_REL: "dc92f7b8e76889c754576dd1a5036e7a7c62b8eb",
}

REPORT_PATH = ROOT / REPORT_REL
MISSION_PATH = ROOT / MISSION_REL
TASK_PATH = ROOT / TASK_REL
RESULT_PATH = ROOT / RESULT_REL
STATE_PATH = ROOT / "canonical/astra_runtime/state" / (MISSION_ID + ".json")

def git_blob_sha(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def safe_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def emit(report):
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))

def prestart_fail(report, code, detail=None):
    report.update({
        "status": "PRESTART_FAIL_NOT_SPENT",
        "first_causal_blocker": code,
        "detail": detail,
        "execution_count": 0,
        "task_executed": False,
        "replay_allowed": True,
        "replay_reason": "PRESTART_FAILURE_NO_PRODUCER_EXECUTION",
        "parent_capability_credit_authorized": False,
    })
    emit(report)
    raise SystemExit(1)

def nested_urls(v):
    out=[]
    if isinstance(v, dict):
        for x in v.values(): out.extend(nested_urls(x))
    elif isinstance(v, list):
        for x in v: out.extend(nested_urls(x))
    elif isinstance(v, str):
        out.extend(re.findall(r"https?://[^\\s<>\"']+", v))
    return out

def numeric(v):
    if isinstance(v,(int,float)) and not isinstance(v,bool):
        return float(v)
    if isinstance(v,dict):
        for k in ("value","numeric_value","mean","estimate"):
            if k in v:
                q=numeric(v[k])
                if q is not None: return q
    if isinstance(v,str):
        m=re.search(r"[-+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][-+]?\\d+)?",v)
        return float(m.group(0)) if m else None
    return None

report = {
    "schema": "PROJECT_BRAIN_THERMOPHYSICS_PARENT_TASK_A_TERMINAL_V1",
    "brain_main": BRAIN_MAIN,
    "runner_base": RUNNER_BASE,
    "mission_id": MISSION_ID,
    "mission_path": MISSION_REL,
    "task_path": TASK_REL,
    "execution_count": 0,
    "task_executed": False,
    "incremental_spend_usd": 0,
    "model_planner_disabled": os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") == "1",
    "canonical_runtime_entrypoint": "canonical/runtime/astra_runtime.py",
    "same_task_replay_forbidden": True,
    "parent_capability_credit_authorized": False,
}

for rel, expected in EXPECTED_BLOBS.items():
    p=ROOT/rel
    observed=git_blob_sha(p) if p.is_file() else None
    if observed != expected:
        prestart_fail(report,"CARRIER_CLOSURE_BLOB_MISMATCH",{"path":rel,"expected":expected,"observed":observed})

if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER") != "1":
    prestart_fail(report,"MODEL_PLANNER_NOT_DISABLED")

mission=safe_json(MISSION_PATH)
task=safe_json(TASK_PATH)
if not isinstance(mission,dict) or mission.get("mission_id") != MISSION_ID:
    prestart_fail(report,"MISSION_INVALID_OR_ID_MISMATCH")
if not isinstance(task,dict) or task.get("task_id") != MISSION_ID:
    prestart_fail(report,"TASK_INVALID_OR_ID_MISMATCH")
if mission.get("goal") != task.get("goal_text"):
    prestart_fail(report,"MISSION_TASK_GOAL_DRIFT")
if (task.get("execution_constraints") or {}).get("required_execution_entrypoint") != "canonical/runtime/astra_runtime.py <canonical mission path>":
    prestart_fail(report,"CANONICAL_ENTRYPOINT_NOT_REQUIRED")
if (task.get("execution_constraints") or {}).get("direct_goal_compiler_harness_forbidden") is not True:
    prestart_fail(report,"DIRECT_COMPILER_HARNESS_NOT_FORBIDDEN")
if (task.get("execution_constraints") or {}).get("exactly_one_execution") is not True:
    prestart_fail(report,"EXACTLY_ONE_EXECUTION_NOT_REQUIRED")
if (task.get("execution_constraints") or {}).get("stop_on_first_causal_gap") is not True:
    prestart_fail(report,"STOP_ON_FIRST_GAP_NOT_REQUIRED")
anti=task.get("anti_leakage") or {}
if any(anti.get(k) is not False for k in (
    "authority_name_preprovided","authority_domain_preprovided","source_url_preprovided",
    "dataset_identifier_preprovided","json_or_table_path_preprovided",
    "quantitative_formula_preprovided","controller_action_graph_preprovided",
    "expected_answer_precommitted"
)):
    prestart_fail(report,"ANTI_LEAKAGE_CONTRACT_INVALID",anti)

if STATE_PATH.exists() or RESULT_PATH.exists():
    prestart_fail(report,"FRESHNESS_FAIL_PREEXISTING_OUTPUT",{"state":STATE_PATH.exists(),"result":RESULT_PATH.exists()})
evid_dir=ROOT/"canonical/astra_runtime/evidence"
preexisting=list(evid_dir.glob(MISSION_ID+"*")) if evid_dir.is_dir() else []
if preexisting:
    prestart_fail(report,"FRESHNESS_FAIL_PREEXISTING_EVIDENCE",[str(x.relative_to(ROOT)) for x in preexisting])

closure=subprocess.run(
    [sys.executable,"-c","import sys;sys.path.insert(0,'canonical/runtime');import python_codec_probe,verify_pending_cli_binding,promote_pending_binding;print('VERIFIER_CLOSURE_OK')"],
    cwd=ROOT,text=True,capture_output=True
)
if closure.returncode != 0 or "VERIFIER_CLOSURE_OK" not in closure.stdout:
    prestart_fail(report,"VERIFIER_CLOSURE_IMPORT_FAIL",{"stdout":closure.stdout[-2000:],"stderr":closure.stderr[-2000:]})

# Irreversible spend starts here.
report["execution_count"]=1
report["task_executed"]=True
proc=subprocess.run(
    [sys.executable,str(ROOT/"canonical/runtime/astra_runtime.py"),MISSION_REL],
    cwd=ROOT,text=True,capture_output=True,timeout=600,
    env={**os.environ,"ASTRA_DISABLE_MODEL_PLANNER":"1"}
)
report["producer_returncode"]=int(proc.returncode)
report["producer_stdout_tail"]=proc.stdout[-16000:]
report["producer_stderr_tail"]=proc.stderr[-16000:]
state=safe_json(STATE_PATH) if STATE_PATH.is_file() else None
report["producer_state"]=state
report["observed_mission_path"]=(state or {}).get("mission_path") if isinstance(state,dict) else None

if proc.returncode != 0 or not isinstance(state,dict) or state.get("status") != "COMPLETE":
    blocker=None
    if isinstance(state,dict):
        blocker=state.get("blocker") or state.get("error")
    report.update({
        "status":"FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed":False,
        "independent_oracle_executed":False,
        "replay_allowed":False,
        "first_causal_stage":"CANONICAL_RUNTIME",
        "first_causal_blocker": blocker or proc.stderr[-5000:] or proc.stdout[-5000:] or "CANONICAL_RUNTIME_NONZERO_OR_INCOMPLETE",
    })
    emit(report)
    raise SystemExit(2)

if report["observed_mission_path"] != MISSION_REL:
    report.update({
        "status":"FAIL_FIRST_CAUSAL_GAP",
        "parent_task_completed":False,
        "independent_oracle_executed":False,
        "replay_allowed":False,
        "first_causal_stage":"MISSION_IDENTITY",
        "first_causal_blocker":"RUNTIME_MISSION_PATH_DRIFT",
    })
    emit(report); raise SystemExit(3)

result=safe_json(RESULT_PATH) if RESULT_PATH.is_file() else None
required=(task.get("required_output") or {}).get("fields") or []
missing=[k for k in required if not isinstance(result,dict) or k not in result]
if missing:
    report.update({
        "status":"FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed":False,
        "independent_oracle_executed":True,
        "replay_allowed":False,
        "first_causal_stage":"RESULT_CONTRACT",
        "first_causal_blocker":"REQUIRED_RESULT_FIELDS_MISSING",
        "missing_fields":missing,
    })
    emit(report); raise SystemExit(4)

if result.get("model_dependency_count") != 0:
    report.update({
        "status":"FAIL_INDEPENDENT_VERIFICATION","parent_task_completed":False,
        "independent_oracle_executed":True,"replay_allowed":False,
        "first_causal_stage":"COGNITION_PROVENANCE","first_causal_blocker":"MODEL_DEPENDENCY_NONZERO"
    })
    emit(report); raise SystemExit(5)

v20=numeric(result.get("viscosity_20c")); v40=numeric(result.get("viscosity_40c")); ratio=numeric(result.get("ratio_40c_to_20c"))
if not all(x is not None and math.isfinite(x) and x>0 for x in (v20,v40,ratio)):
    report.update({"status":"FAIL_INDEPENDENT_VERIFICATION","parent_task_completed":False,"independent_oracle_executed":True,"replay_allowed":False,"first_causal_blocker":"NUMERIC_RESULT_UNPARSABLE"})
    emit(report); raise SystemExit(6)
recomputed=v40/v20
ratio_ok=abs(recomputed-ratio) <= max(1e-9,1e-6*abs(recomputed))

urls=sorted(set(nested_urls(result.get("source_provenance"))))[:5]
fetches=[]
for url in urls:
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-Independent-Thermophysics-Oracle/1.0"})
        with urllib.request.urlopen(req,timeout=25) as resp:
            raw=resp.read(2500000)
            fetches.append({"url":url,"final_url":resp.geturl(),"status":int(getattr(resp,"status",200)),"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"body":raw.decode("utf-8","replace")})
    except Exception as e:
        fetches.append({"url":url,"error":type(e).__name__+":"+str(e)})

source_ok=any(x.get("status",0) in range(200,400) and x.get("bytes",0)>0 for x in fetches)
combined="\n".join(x.get("body","") for x in fetches if x.get("body"))
def approximate_number_present(value):
    if not combined: return False
    candidates=set()
    for scale in (1,1000,0.001):
        z=value*scale
        for digits in (3,4,5,6):
            candidates.add(f"{z:.{digits}g}")
            candidates.add(f"{z:.{digits}f}".rstrip("0").rstrip("."))
    return any(c and c in combined for c in candidates)

source_values_corrob = approximate_number_present(v20) and approximate_number_present(v40)
expected_decision = (recomputed < 0.5)
d=result.get("decision")
if isinstance(d,bool):
    decision_ok=(d is expected_decision)
else:
    s=str(d).strip().lower()
    yes=any(k in s for k in ("yes","true","less than half","< 0.5","below half"))
    no=any(k in s for k in ("no","false","not less than half",">= 0.5","at least half"))
    decision_ok=(yes and expected_decision) or (no and not expected_decision)

report["independent_oracle"]={
    "urls_refetched":[{k:v for k,v in x.items() if k!="body"} for x in fetches],
    "source_fetch_success":source_ok,
    "producer_viscosity_20c":v20,
    "producer_viscosity_40c":v40,
    "producer_ratio":ratio,
    "recomputed_ratio":recomputed,
    "ratio_match":ratio_ok,
    "source_numeric_values_correlated":source_values_corrob,
    "expected_decision_from_recomputed_ratio":expected_decision,
    "producer_decision":d,
    "decision_match":decision_ok,
}
if not (source_ok and source_values_corrob and ratio_ok and decision_ok):
    report.update({
        "status":"FAIL_INDEPENDENT_VERIFICATION",
        "parent_task_completed":False,
        "independent_oracle_executed":True,
        "replay_allowed":False,
        "first_causal_stage":"INDEPENDENT_ORACLE",
        "first_causal_blocker":"SOURCE_OR_CALCULATION_ORACLE_DID_NOT_CLOSE",
    })
    emit(report); raise SystemExit(7)

report.update({
    "status":"PRODUCER_SUCCESS_INDEPENDENT_ORACLE_PASS__CANONICAL_PARENT_ADJUDICATION_REQUIRED",
    "parent_task_completed":True,
    "independent_oracle_executed":True,
    "replay_allowed":False,
    "parent_capability_credit_authorized":False,
})
emit(report)
