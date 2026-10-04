#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT=pathlib.Path(__file__).resolve().parent
FROZEN=ROOT/"subject"/"livebench_frozen_runtime_closure_v1"
CANDIDATE=ROOT/"subject"/"livebench_exact_literal_routing_v1"/"goal_compiler.py"
EXPECTED_CANDIDATE_BLOB="bf0dd1cdb2869a0e7834c04978369998fd724fb8"

def git_blob_sha(path: pathlib.Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

assert FROZEN.is_dir()
assert CANDIDATE.is_file()
assert git_blob_sha(CANDIDATE)==EXPECTED_CANDIDATE_BLOB

source=CANDIDATE.read_text(encoding="utf-8")
helper=source[source.index("def _compile_exact_literal_response_goal"):source.index("def _compile_verified_browser_interaction")]
assert "LIVEBENCH" not in helper.upper()
assert "SYNTHETIC_OK" not in helper

with tempfile.TemporaryDirectory() as td:
    subject=pathlib.Path(td)/"subject"
    shutil.copytree(FROZEN,subject)
    runtime=subject/"canonical"/"runtime"
    shutil.copy2(CANDIDATE,runtime/"goal_compiler.py")

    probe=r'''
import json
import pathlib
import sys

subject=pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0,str(subject))
sys.path.insert(0,str(subject/"canonical"/"runtime"))

from canonical.runtime import goal_compiler
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as adapter

compiled=goal_compiler.compile_goal(
    "Reply with exactly SYNTHETIC_OK.",
    {},
    subject,
)
assert compiled["compiler_mode"]=="DETERMINISTIC_EXACT_LITERAL_RESPONSE"
assert compiled["controller_actions"]==[
    {"type":"finish","args":{"summary":"SYNTHETIC_OK."}}
]
assert compiled["clause_coverage_verified"] is True

for goal,want in [
    ('Respond exactly "alpha beta".',"alpha beta"),
    ("Answer exactly cedar","cedar"),
    ("Output exactly 12345","12345"),
]:
    c=goal_compiler.compile_goal(goal,{},subject)
    assert c["controller_actions"][0]["args"]["summary"]==want

request={
    "benchmark_id":"LIVEBENCH_IF_2026_06_25",
    "task_id":"SYNTHETIC_ZERO_CASE_INFERENCE",
    "allowed_tools":[],
    "task_payload":{"instruction":"Reply with exactly SYNTHETIC_OK."},
}
out=adapter.infer(request)
assert out["status"]=="PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",out
assert out["answer"]=="SYNTHETIC_OK.",out
assert out["cognition_dependency_class"]=="MODEL_INDEPENDENT",out
assert int(out.get("model_dependency_count") or 0)==0,out
print("SYNTHETIC_PASS="+json.dumps(out,sort_keys=True))
'''
    p=subprocess.run(
        [sys.executable,"-c",probe,str(subject)],
        cwd=subject,
        text=True,
        capture_output=True,
        timeout=60,
    )
    if p.returncode!=0:
        print(p.stdout)
        print(p.stderr,file=sys.stderr)
        raise SystemExit(p.returncode)

receipt={
    "schema":"PROJECT_BRAIN_LIVEBENCH_EXACT_LITERAL_ROUTING_PUBLIC_VERIFICATION_V1",
    "status":"PASS",
    "candidate_goal_compiler_git_blob":EXPECTED_CANDIDATE_BLOB,
    "frozen_parent_subject":"subject/livebench_frozen_runtime_closure_v1",
    "synthetic_instruction":"Reply with exactly SYNTHETIC_OK.",
    "synthetic_answer":"SYNTHETIC_OK.",
    "full_adapter_inference_pass":True,
    "model_dependency_count":0,
    "terminal_case_content_read":False,
    "terminal_cases_consumed":0,
    "incremental_spend_usd":0,
    "benchmark_specific_logic_in_new_helper":False,
    "acceptance_credit":False,
}
(ROOT/"livebench_exact_literal_routing_v1_receipt.json").write_text(
    json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(receipt,sort_keys=True))
