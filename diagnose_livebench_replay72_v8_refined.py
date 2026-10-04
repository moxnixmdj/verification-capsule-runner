#!/usr/bin/env python3
from __future__ import annotations

import collections
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
V7 = ROOT / "diagnose_livebench_replay72_v7_sanitized.py"
CLASSIFIER = ROOT / "livebench_v8_refined_classifier.py"
EXPECTED_V7_BLOB = "55d4b961f58dc45c1513f9c9282a63773444773d"
REPLAY_LIMIT = 72

CASE_DRIVER = r'''
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
    raise LiveBenchPostPromptAcquisitionForbidden(
        "LIVEBENCH_POLICY_POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN"
    )
astra_runtime._load_auto_capability_acquisition=_deny_auto_capability_acquisition

import diagnostic_classifier
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as adapter
source_codes=diagnostic_classifier.source_code_vocabulary([
    pathlib.Path(astra_runtime.__file__),
    pathlib.Path(adapter.__file__),
])
req=json.loads(sys.stdin.read())
try:
    adapter.infer(req)
except Exception as exc:
    cls=diagnostic_classifier.classify_exception(exc,source_codes)
    print(json.dumps({"status":"CLASSIFIED_EXCEPTION",**cls},sort_keys=True))
else:
    print(json.dumps({"status":"VALID_RESPONSE"},sort_keys=True))
'''


def git_blob_sha(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def load_v7():
    if git_blob_sha(V7) != EXPECTED_V7_BLOB:
        raise RuntimeError("V7_DIAGNOSTIC_BLOB_DRIFT")
    spec=importlib.util.spec_from_file_location("livebench_v8_v7base",V7)
    if spec is None or spec.loader is None:
        raise RuntimeError("V7_IMPORT_SPEC")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_template(base,v7):
    mod=v7.load_base()
    mod.install_scorer_deps()
    mod.prepare_nltk(base)
    template=mod.build_runtime_template(base)
    shutil.copy2(CLASSIFIER,template/"diagnostic_classifier.py")
    return mod,template


def classify_one(template,q,benchmark_id):
    with tempfile.TemporaryDirectory(prefix="lb-v8-case-") as td:
        root=pathlib.Path(td)/"root"
        shutil.copytree(template,root,dirs_exist_ok=True)
        env=os.environ.copy()
        env["PYTHONPATH"]=str(root)
        req={
          "benchmark_id":benchmark_id,
          "task_id":"REDACTED",
          "task_payload":{"instruction":q["turns"][0]},
          "allowed_tools":[],
        }
        try:
            cp=subprocess.run(
                [sys.executable,"-c",CASE_DRIVER],
                input=json.dumps(req),text=True,capture_output=True,
                cwd=root,env=env,timeout=45,
            )
            if cp.returncode!=0:
                return "UNCLASSIFIED_RUNTIME:PROCESS_EXIT_NONZERO"
            obj=json.loads(cp.stdout)
            if obj.get("status")=="VALID_RESPONSE":
                return "VALID_RESPONSE"
            kind=str(obj.get("kind") or "UNCLASSIFIED_RUNTIME")
            code=str(obj.get("code") or "UNCLASSIFIED")
            allowed={
              "STATIC_BLOCKER","STATIC_ADAPTER_BLOCKER","POLICY_BLOCK",
              "COMPOSITION_SUBBLOCKER","ARCHITECTURAL_GAP","UNCLASSIFIED_RUNTIME",
            }
            if kind not in allowed:
                return "UNCLASSIFIED_RUNTIME:CLASSIFIER_KIND_INVALID"
            if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,160}",code):
                return "UNCLASSIFIED_RUNTIME:CLASSIFIER_CODE_INVALID"
            return kind+":"+code
        except Exception:
            return "UNCLASSIFIED_RUNTIME:DRIVER_EXCEPTION"


def main(*,authorized=False,activation_blob=None):
    if authorized is not True:
        raise SystemExit("FAIL_CLOSED:VERIFIED_V8_DIAGNOSTIC_LAUNCHER_REQUIRED")
    if not isinstance(activation_blob,str) or re.fullmatch(r"[0-9a-f]{40}",activation_blob) is None:
        raise SystemExit("FAIL_CLOSED:VERIFIED_V8_ACTIVATION_BLOB_REQUIRED")
    if os.environ.get("GITHUB_ACTIONS")!="true" or str(os.environ.get("REPOSITORY_PRIVATE","")).lower()!="false":
        raise SystemExit("FAIL_CLOSED:PUBLIC_STANDARD_GITHUB_RUNNER_REQUIRED")
    v7=load_v7()
    with tempfile.TemporaryDirectory(prefix="lb-v8-diagnostic-") as td:
        base=pathlib.Path(td)
        mod,template=build_template(base,v7)

        synthetic={"question_id":"SYNTHETIC_ZERO_CASE","turns":["Reply with exactly SYNTHETIC_OK."]}
        synth=classify_one(template,synthetic,mod.BENCHMARK_ID)
        if not (
            synth=="VALID_RESPONSE"
            or synth.startswith("STATIC_BLOCKER:")
            or synth.startswith("STATIC_ADAPTER_BLOCKER:")
            or synth.startswith("POLICY_BLOCK:")
            or synth.startswith("COMPOSITION_SUBBLOCKER:")
            or synth.startswith("ARCHITECTURAL_GAP:")
        ):
            raise SystemExit("FAIL_CLOSED:V8_SYNTHETIC_CLASSIFIER:"+synth)

        # Only the exact previously exposed prefix may be read.
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
        unclassified=sum(v for k,v in hist.items() if k.startswith("UNCLASSIFIED_RUNTIME:"))
        out={
          "schema":"PROJECT_BRAIN_LIVEBENCH_V8_REFINED_CAUSAL_DIAGNOSTIC_RESULT_V1",
          "status":"DIAGNOSTIC_COMPLETE",
          "benchmark_id":mod.BENCHMARK_ID,
          "activation_blob_sha":activation_blob,
          "v7_diagnostic_git_blob_sha":EXPECTED_V7_BLOB,
          "replay_prefix_limit":REPLAY_LIMIT,
          "terminal_cases_consumed":REPLAY_LIMIT,
          "new_case_exposure":False,
          "case_ids_emitted":False,
          "prompt_text_emitted":False,
          "response_text_emitted":False,
          "raw_exception_text_emitted":False,
          "classification_histogram":hist,
          "unclassified_runtime_count":unclassified,
          "acceptance_credit_authority":False,
          "promotion_authority":False,
        }
        print("LIVEBENCH_V8_REFINED_DIAGNOSTIC="+json.dumps(out,sort_keys=True),flush=True)
        return 0


if __name__=="__main__":
    raise SystemExit("FAIL_CLOSED:VERIFIED_V8_DIAGNOSTIC_LAUNCHER_REQUIRED")
