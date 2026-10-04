#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, shutil, subprocess, sys, tempfile, traceback
import execute_livebench_if_threshold_v2 as runner

ROOT=pathlib.Path(__file__).resolve().parent
PROMPTS=[
  "Write exactly three words.",
  "Write one concise paragraph about a tree.",
  "Summarize this sentence in simpler language: The cat sat on the mat.",
]

def one(prompt:str)->dict:
    with tempfile.TemporaryDirectory(prefix="lb-generic-zero-") as td:
        base=pathlib.Path(td)
        template=runner.build_runtime_template(base)
        case=base/"case"
        shutil.copytree(template,case)
        env=dict(__import__("os").environ)
        env["PYTHONPATH"]=str(case)
        req={
          "benchmark_id":runner.BENCHMARK_ID,
          "task_id":"SYNTHETIC_GENERIC_GOAL",
          "task_payload":{"instruction":prompt},
          "allowed_tools":[],
        }
        cp=subprocess.run(
          [sys.executable,"-c",runner.CASE_DRIVER],
          input=json.dumps(req),text=True,capture_output=True,cwd=case,env=env,timeout=45
        )
        return {
          "prompt":prompt,
          "returncode":cp.returncode,
          "stdout":cp.stdout[-4000:],
          "stderr":cp.stderr[-8000:],
        }

out={"schema":"PROJECT_BRAIN_LIVEBENCH_GENERIC_GOAL_ZERO_CASE_DIAGNOSTIC_V1",
     "terminal_case_content_read":False,"terminal_cases_consumed":0,
     "fresh_reality_consumed":False,"results":[]}
for p in PROMPTS:
    try: out["results"].append(one(p))
    except Exception as exc:
        out["results"].append({"prompt":p,"diagnostic_exception":type(exc).__name__+":"+str(exc),"traceback":traceback.format_exc()[-8000:]})
print(json.dumps(out,indent=2,sort_keys=True))
