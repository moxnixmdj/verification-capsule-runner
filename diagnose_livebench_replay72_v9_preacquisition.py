#!/usr/bin/env python3
from __future__ import annotations
import collections,concurrent.futures,hashlib,importlib.util,json,os,pathlib,re,shutil,subprocess,sys,tempfile

ROOT=pathlib.Path(__file__).resolve().parent
BASE_EXEC=ROOT/"execute_livebench_if_replay72_v4_candidate.py"
EXPECTED_BASE_EXEC_BLOB="2a57ce896ddbd6819246aab8b44d17a00f36b61e"
REPLAY_LIMIT=72

def git_blob_sha(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load_base():
    if git_blob_sha(BASE_EXEC)!=EXPECTED_BASE_EXEC_BLOB:
        raise RuntimeError("BASE_EXECUTOR_BLOB_DRIFT")
    spec=importlib.util.spec_from_file_location("livebench_v9_base",BASE_EXEC)
    if spec is None or spec.loader is None:
        raise RuntimeError("BASE_EXECUTOR_IMPORT_SPEC")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    if mod.REPLAY_LIMIT!=72 or len(mod.RUNTIME_FILES)!=24:
        raise RuntimeError("BASE_EXECUTOR_SCOPE_DRIFT")
    return mod

CASE_DRIVER=r"""
import json,sys,re
def _audit(event,args):
    if event=="socket.connect":
        raise RuntimeError("V9_POLICY_NETWORK_FORBIDDEN")
    if event=="subprocess.Popen":
        exe=args[0] if len(args)>0 else ""
        argv=args[1] if len(args)>1 else ()
        parts=[str(exe)]
        if isinstance(argv,(list,tuple)): parts.extend(str(x) for x in argv)
        else: parts.append(str(argv))
        t=" "+" ".join(parts).lower()
        if any(x in t for x in (" pip install"," -m pip install","npm install","apt install","apt-get install","git clone","curl ","wget ")):
            raise RuntimeError("V9_POLICY_ACQUISITION_FORBIDDEN")
sys.addaudithook(_audit)

from canonical.runtime import astra_runtime
req=json.loads(sys.stdin.read())
goal=str((req.get("task_payload") or {}).get("instruction") or "")
mission={"mission_id":"V9_REDACTED","goal":goal}
compile_class="OTHER"
acquisition_goal=goal
try:
    astra_runtime._compile_plain_goal(goal)
except BaseException as exc:
    err=str(exc)
    marker="GOAL_COMPILATION_FAILED:GOAL_COMPILATION_SUBGOAL_UNRESOLVED:"
    if "GOAL_COMPILATION_FAILED:GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH" in err:
        compile_class="NO_MATCH"
    elif marker in err:
        compile_class="UNRESOLVED_SUBGOAL"
        raw=err.split(marker,1)[1]
        try:
            acquisition_goal=str(json.loads(raw).get("subgoal") or "").strip() or goal
        except BaseException:
            acquisition_goal=goal
    else:
        compile_class="OTHER"
else:
    compile_class="COMPILES"

try:
    gap=str(astra_runtime._classify_plain_goal_gap(acquisition_goal))
except BaseException:
    gap="GAP_CLASSIFICATION_FAILED"

try:
    _,grounding=astra_runtime._ground_plain_goal_to_bound_capabilities(mission,goal)
    clauses=grounding.get("clauses") or []
    unresolved=[x for x in clauses if str(x.get("status") or "")=="UNRESOLVED"]
    grounded_count=int(grounding.get("grounded_clause_count") or 0)
    total=len(clauses)
    if not unresolved:
        unresolved_reason="NONE"
    else:
        flags=[]
        for x in unresolved:
            flags.append(bool(x.get("rejected_unbindable_candidates")))
        if flags and all(flags):
            unresolved_reason="ALL_UNBINDABLE"
        elif flags and any(flags):
            unresolved_reason="MIXED_UNBINDABLE_AND_NO_MATCH"
        else:
            unresolved_reason="NO_MATCH"
    if total==0:
        grounding_shape="NO_CLAUSES"
    elif grounded_count==0:
        grounding_shape="ZERO_GROUNDED"
    elif grounded_count==total:
        grounding_shape="ALL_GROUNDED"
    else:
        grounding_shape="PARTIAL_GROUNDED"
    broad=grounding.get("broad_objective_decomposition")
    broad_class="DECOMPOSED" if isinstance(broad,dict) and broad.get("status")=="DECOMPOSED" else "NONE"
except BaseException:
    grounding_shape="GROUNDING_FAILED"
    unresolved_reason="GROUNDING_FAILED"
    broad_class="UNKNOWN"

safe=lambda s: re.sub(r"[^A-Z0-9_]+","_",str(s).upper())[:80]
label="|".join([
    "COMPILE_"+safe(compile_class),
    "GAP_"+safe(gap),
    "GROUND_"+safe(grounding_shape),
    "UNRESOLVED_"+safe(unresolved_reason),
    "BROAD_"+safe(broad_class),
])
print(json.dumps({"label":label},sort_keys=True))
"""

def build_template(base,mod):
    return mod.build_runtime_template(base)

def classify_one(template,q,benchmark_id):
    with tempfile.TemporaryDirectory(prefix="lb-v9-case-") as td:
        root=pathlib.Path(td)/"root"
        shutil.copytree(template,root,dirs_exist_ok=True)
        env=os.environ.copy();env["PYTHONPATH"]=str(root)
        req={"benchmark_id":benchmark_id,"task_id":"REDACTED","task_payload":{"instruction":q["turns"][0]},"allowed_tools":[]}
        try:
            cp=subprocess.run([sys.executable,"-c",CASE_DRIVER],input=json.dumps(req),text=True,capture_output=True,cwd=root,env=env,timeout=45)
            if cp.returncode!=0:
                return "V9_DRIVER_FAILURE"
            obj=json.loads(cp.stdout)
            label=str(obj.get("label") or "V9_LABEL_MISSING")
            if not re.fullmatch(r"[A-Z0-9_|]{3,400}",label):
                return "V9_LABEL_INVALID"
            return label
        except Exception:
            return "V9_DRIVER_EXCEPTION"

def main(*,authorized=False,activation_blob=None):
    if authorized is not True:
        raise SystemExit("FAIL_CLOSED:VERIFIED_V9_DIAGNOSTIC_LAUNCHER_REQUIRED")
    if not isinstance(activation_blob,str) or re.fullmatch(r"[0-9a-f]{40}",activation_blob) is None:
        raise SystemExit("FAIL_CLOSED:VERIFIED_V9_ACTIVATION_BLOB_REQUIRED")
    if os.environ.get("GITHUB_ACTIONS")!="true" or str(os.environ.get("REPOSITORY_PRIVATE","")).lower()!="false":
        raise SystemExit("FAIL_CLOSED:PUBLIC_STANDARD_GITHUB_RUNNER_REQUIRED")
    mod=load_base()
    with tempfile.TemporaryDirectory(prefix="lb-v9-diagnostic-") as td:
        base=pathlib.Path(td)
        mod.install_scorer_deps()
        mod.prepare_nltk(base)
        template=build_template(base,mod)
        parquet=mod.download_dataset(base)
        questions=mod.parse_population(base,parquet)
        classes=[]
        batch=8
        for start in range(0,REPLAY_LIMIT,batch):
            current=questions[start:start+batch]
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(batch,os.cpu_count() or 2)) as ex:
                classes.extend(ex.map(lambda q:classify_one(template,q,mod.BENCHMARK_ID),current))
        if len(classes)!=REPLAY_LIMIT:
            raise RuntimeError("REPLAY_PREFIX_COUNT_MISMATCH")
        hist=dict(sorted(collections.Counter(classes).items()))
        out={
          "schema":"PROJECT_BRAIN_LIVEBENCH_V9_PREACQUISITION_STATIC_RESULT_V1",
          "status":"DIAGNOSTIC_COMPLETE",
          "benchmark_id":mod.BENCHMARK_ID,
          "activation_blob_sha":activation_blob,
          "replay_prefix_limit":REPLAY_LIMIT,
          "replayed_already_exposed_cases":REPLAY_LIMIT,
          "new_case_exposure":False,
          "case_ids_emitted":False,
          "prompt_text_emitted":False,
          "response_text_emitted":False,
          "raw_exception_text_emitted":False,
          "classification_histogram":hist,
          "acceptance_credit_authority":False,
          "promotion_authority":False,
        }
        print("LIVEBENCH_V9_STATIC_REFINEMENT="+json.dumps(out,sort_keys=True),flush=True)
        return 0

if __name__=="__main__":
    raise SystemExit("FAIL_CLOSED:VERIFIED_V9_DIAGNOSTIC_LAUNCHER_REQUIRED")
