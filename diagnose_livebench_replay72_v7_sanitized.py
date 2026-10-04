#!/usr/bin/env python3
from __future__ import annotations
import collections,concurrent.futures,hashlib,importlib.util,json,os,pathlib,re,shutil,subprocess,sys,tempfile

ROOT=pathlib.Path(__file__).resolve().parent
BASE_EXEC=ROOT/"execute_livebench_if_replay72_v4_candidate.py"
CLASSIFIER=ROOT/"livebench_v7_sanitized_classifier.py"
EXPECTED_BASE_EXEC_BLOB="2a57ce896ddbd6819246aab8b44d17a00f36b61e"
REPLAY_LIMIT=72

def git_blob_sha(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load_base():
    if git_blob_sha(BASE_EXEC)!=EXPECTED_BASE_EXEC_BLOB:
        raise RuntimeError("BASE_EXECUTOR_BLOB_DRIFT")
    spec=importlib.util.spec_from_file_location("livebench_v7_base",BASE_EXEC)
    if spec is None or spec.loader is None:
        raise RuntimeError("BASE_EXECUTOR_IMPORT_SPEC")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    if mod.REPLAY_LIMIT!=72 or len(mod.RUNTIME_FILES)!=24:
        raise RuntimeError("BASE_EXECUTOR_SCOPE_DRIFT")
    return mod

CASE_DRIVER=r'''
import json,pathlib,sys
def _audit(event,args):
    if event=="socket.connect":
        raise RuntimeError("LIVEBENCH_POLICY_EXTERNAL_NETWORK_FORBIDDEN")
    if event=="subprocess.Popen":
        exe=args[0] if len(args)>0 else ""
        argv=args[1] if len(args)>1 else ()
        parts=[str(exe)]
        if isinstance(argv,(list,tuple)): parts.extend(str(x) for x in argv)
        else: parts.append(str(argv))
        text=" ".join(parts).lower()
        padded=" "+text
        forbidden=(" pip install"," -m pip install","npm install","npm i ","apt-get install","apt install","git clone","curl ","wget ")
        if any(tok in padded for tok in forbidden):
            raise RuntimeError("LIVEBENCH_POLICY_POST_PROMPT_ACQUISITION_FORBIDDEN")
sys.addaudithook(_audit)

from canonical.runtime import astra_runtime
class LiveBenchPostPromptAcquisitionForbidden(RuntimeError): pass
def _deny_auto_capability_acquisition():
    raise LiveBenchPostPromptAcquisitionForbidden("LIVEBENCH_POLICY_POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN")
astra_runtime._load_auto_capability_acquisition=_deny_auto_capability_acquisition

import diagnostic_classifier
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as adapter
source_codes=diagnostic_classifier.source_code_vocabulary([
    pathlib.Path(astra_runtime.__file__),
    pathlib.Path(adapter.__file__),
])
req=json.loads(sys.stdin.read())
try:
    out=adapter.infer(req)
except Exception as exc:
    cls=diagnostic_classifier.classify_exception(exc,source_codes)
    print(json.dumps({"status":"CLASSIFIED_EXCEPTION",**cls},sort_keys=True))
else:
    # Deliberately do not emit answer, trace, prompt, task id, or case-specific text.
    print(json.dumps({"status":"VALID_RESPONSE"},sort_keys=True))
'''

def build_diagnostic_template(base,mod):
    template=mod.build_runtime_template(base)
    shutil.copy2(CLASSIFIER,template/"diagnostic_classifier.py")
    return template

def classify_one(template,q,benchmark_id):
    with tempfile.TemporaryDirectory(prefix="lb-v7-case-") as td:
        root=pathlib.Path(td)/"root"
        shutil.copytree(template,root,dirs_exist_ok=True)
        env=os.environ.copy();env["PYTHONPATH"]=str(root)
        req={"benchmark_id":benchmark_id,"task_id":"REDACTED","task_payload":{"instruction":q["turns"][0]},"allowed_tools":[]}
        try:
            cp=subprocess.run([sys.executable,"-c",CASE_DRIVER],input=json.dumps(req),text=True,capture_output=True,cwd=root,env=env,timeout=45)
            if cp.returncode!=0:
                return "UNCLASSIFIED_RUNTIME:PROCESS_EXIT_NONZERO"
            obj=json.loads(cp.stdout)
            if obj.get("status")=="VALID_RESPONSE":
                return "VALID_RESPONSE"
            kind=str(obj.get("kind") or "UNCLASSIFIED_RUNTIME")
            code=str(obj.get("code") or "UNCLASSIFIED")
            if kind not in {"STATIC_BLOCKER","STATIC_ADAPTER_BLOCKER","POLICY_BLOCK","UNCLASSIFIED_RUNTIME"}:
                return "UNCLASSIFIED_RUNTIME:CLASSIFIER_KIND_INVALID"
            if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,160}",code):
                return "UNCLASSIFIED_RUNTIME:CLASSIFIER_CODE_INVALID"
            return kind+":"+code
        except Exception:
            return "UNCLASSIFIED_RUNTIME:DRIVER_EXCEPTION"

def main(*,authorized=False,activation_blob=None):
    if authorized is not True:
        raise SystemExit("FAIL_CLOSED:VERIFIED_V7_DIAGNOSTIC_LAUNCHER_REQUIRED")
    if not isinstance(activation_blob,str) or re.fullmatch(r"[0-9a-f]{40}",activation_blob) is None:
        raise SystemExit("FAIL_CLOSED:VERIFIED_V7_ACTIVATION_BLOB_REQUIRED")
    if os.environ.get("GITHUB_ACTIONS")!="true" or str(os.environ.get("REPOSITORY_PRIVATE","")).lower()!="false":
        raise SystemExit("FAIL_CLOSED:PUBLIC_STANDARD_GITHUB_RUNNER_REQUIRED")
    mod=load_base()
    with tempfile.TemporaryDirectory(prefix="lb-v7-diagnostic-") as td:
        base=pathlib.Path(td)
        # Recreate the exact V6 pre-case dependency environment before any terminal dataset read.
        # This prevents the diagnostic from manufacturing new runtime exits that were absent in V6.
        mod.install_scorer_deps()
        mod.prepare_nltk(base)
        template=build_diagnostic_template(base,mod)
        # Synthetic check must produce only an allowed aggregate class, never raw text.
        synthetic={"question_id":"SYNTHETIC_ZERO_CASE","turns":["Reply with exactly SYNTHETIC_OK."]}
        synth=classify_one(template,synthetic,mod.BENCHMARK_ID)
        if not (
          synth=="VALID_RESPONSE"
          or synth.startswith("STATIC_BLOCKER:")
          or synth.startswith("STATIC_ADAPTER_BLOCKER:")
          or synth.startswith("POLICY_BLOCK:")
        ):
            raise SystemExit("FAIL_CLOSED:V7_SYNTHETIC_CLASSIFIER:"+synth)
        # Exact already-exposed population only.
        parquet=mod.download_dataset(base)
        questions=mod.parse_population(base,parquet)
        batch=8
        classes=[]
        for start in range(0,REPLAY_LIMIT,batch):
            current=questions[start:start+batch]
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(batch,os.cpu_count() or 2)) as ex:
                classes.extend(ex.map(lambda q:classify_one(template,q,mod.BENCHMARK_ID),current))
        if len(classes)!=REPLAY_LIMIT:
            raise RuntimeError("REPLAY_PREFIX_COUNT_MISMATCH")
        hist=dict(sorted(collections.Counter(classes).items()))
        valid=hist.get("VALID_RESPONSE",0)
        unclassified=sum(v for k,v in hist.items() if k.startswith("UNCLASSIFIED_RUNTIME:"))
        out={
          "schema":"PROJECT_BRAIN_LIVEBENCH_V7_SANITIZED_BLOCKER_DIAGNOSTIC_RESULT_V1",
          "status":"DIAGNOSTIC_COMPLETE",
          "benchmark_id":mod.BENCHMARK_ID,
          "activation_blob_sha":activation_blob,
          "base_executor_git_blob_sha":EXPECTED_BASE_EXEC_BLOB,
          "replay_prefix_limit":REPLAY_LIMIT,
          "terminal_cases_consumed":REPLAY_LIMIT,
          "new_case_exposure":False,
          "case_ids_emitted":False,
          "prompt_text_emitted":False,
          "response_text_emitted":False,
          "raw_exception_text_emitted":False,
          "valid_response_count":valid,
          "unclassified_runtime_count":unclassified,
          "classification_histogram":hist,
          "acceptance_credit_authority":False,
          "promotion_authority":False,
        }
        print("LIVEBENCH_V7_SANITIZED_DIAGNOSTIC="+json.dumps(out,sort_keys=True),flush=True)
        return 0

if __name__=="__main__":
    raise SystemExit("FAIL_CLOSED:VERIFIED_V7_DIAGNOSTIC_LAUNCHER_REQUIRED")
