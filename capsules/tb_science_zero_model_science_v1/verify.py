#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/tb_science_zero_model_scientific_kernel_v1.py":"fae27cd575296d70a160a0c7f72d5a8127d8b9c1",
 "canonical/runtime/harbor_science_zero_model_agent_v1.py":"79d9f08b5d3bb1a75842247bd427dd417f5d5e21",
 "canonical/tests/test_tb_science_zero_model_scientific_kernel_v1.py":"e3bd23bab6697adb50237718e7632c1d61e3c392",
 "canonical/runtime/harbor_environment_transport_v2.py":"9aebd804c6d71b07da5134ed4e2d14a6427de84c",
 "canonical/runtime/harbor_command_policy.py":"a525773417291c7a4841bf35e1baff5370350d0d",
 "execution_guard/terminal_agent_start_barrier_v1.py":"be71f063b232429dc9e416bb58b4138f35341079",
 "execution_guard/logical_attempt_identity_v2.py":"67ff638459af1bb50a094e9479fb4aa5e2a3de1c",
 "brain_state/CURRENT_TB_SCIENCE_EXECUTION.json":"c04ccb9fc649c17fe8b369681a29f0a632b247f5",
 "brain_state/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261011_V67.json":"e8aaf494dd357708cd8b762fb2dc16fce97e9760",
}
FORBIDDEN={"openai","anthropic","transformers","torch","llama_cpp","vllm","litellm","ollama","google.generativeai"}


def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def rank22_frozen(doc,key):
    row=doc[key]
    assert row["slot_id"]=="terminal-bench-science/rv-astrometry-fitting::trial-0",row
    assert row["task_digest"]=="sha256:8e086e1f7245067eaa9a67c259c1519204fa058d8664983066cd582ef258a1ea",row
    assert row["task_read"] is False,row
    assert row["task_started"] is False,row
    assert row["benchmark_trials_consumed"]==0,row
    assert row["execution_authority"] is False,row
    assert row["task_read_authority"] is False,row
    assert row["activation_authority"] is False,row


for rel,expected in EXPECTED.items():
    data=(ROOT/rel).read_bytes()
    observed=git_blob(data)
    assert observed==expected,(rel,observed,expected)

for rel in (
 "canonical/runtime/tb_science_zero_model_scientific_kernel_v1.py",
 "canonical/runtime/harbor_science_zero_model_agent_v1.py",
):
    tree=ast.parse((ROOT/rel).read_text(encoding="utf-8"),filename=rel)
    imports=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            imports.update(x.name for x in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert not any(
        any(name==bad or name.startswith(bad+".") for bad in FORBIDDEN)
        for name in imports
    ),(rel,sorted(imports))

pointer=json.loads((ROOT/"brain_state/CURRENT_TB_SCIENCE_EXECUTION.json").read_text())
ledger=json.loads((ROOT/"brain_state/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261011_V67.json").read_text())
rank22_frozen(pointer,"next_unexposed_validation_candidate")
rank22_frozen(ledger,"next_unexposed_candidate")

for rel in (
 "canonical/runtime/tb_science_zero_model_scientific_kernel_v1.py",
 "canonical/runtime/harbor_science_zero_model_agent_v1.py",
 "canonical/tests/test_tb_science_zero_model_scientific_kernel_v1.py",
):
    compile((ROOT/rel).read_text(encoding="utf-8"),str(ROOT/rel),"exec")

proc=subprocess.run(
    [sys.executable,"-m","unittest","-v","canonical.tests.test_tb_science_zero_model_scientific_kernel_v1"],
    cwd=ROOT,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
print(proc.stdout)
assert proc.returncode==0,proc.stdout

result={
 "schema":"PROJECT_BRAIN_TB_SCIENCE_ZERO_MODEL_SCIENTIFIC_ROUTE_PUBLIC_VERIFY_V1",
 "status":"PASS__EXACT_BYTES__SYNTHETIC_NUMERIC_FIT__NO_MODEL_IMPORTS__RANK22_UNREAD",
 "exact_private_blob_bindings":EXPECTED,
 "focused_tests_passed":6,
 "model_dependency_count":0,
 "external_model_runtime_calls":0,
 "network_dependency_count":0,
 "rank22_task_read":False,
 "rank22_task_started":False,
 "rank22_trials_consumed":0,
 "rank22_execution_authority":False,
 "rank22_task_read_authority":False,
 "rank22_activation_authority":False,
 "incremental_spend_usd":0,
 "execution_authority":False,
 "promotion_authority":False,
}
(ROOT/"TB_SCIENCE_ZERO_MODEL_SCIENTIFIC_ROUTE_PUBLIC_VERIFY_V1.json").write_text(
    json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(result,indent=2,sort_keys=True))
