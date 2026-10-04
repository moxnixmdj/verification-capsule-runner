#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib, subprocess, sys, tempfile, textwrap

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject"/"livebench_frozen_runtime_closure_v1"
RUNTIME=SUBJECT/"canonical"/"runtime"

EXPECTED={
"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"7badee4878700f2cd4176beb8319d2a6a0bdf782",
"canonical/runtime/apt_cli_probe.py":"3f3a8f6a0154e1ed3f87fc97b99840598297b119",
"canonical/runtime/astra_runtime.py":"7f5d16b1db69cb620954bc778e0ba6e15e687b75",
"canonical/runtime/auto_apt_cli_acquisition.py":"0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
"canonical/runtime/auto_capability_acquisition.py":"fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
"canonical/runtime/auto_npm_library_acquisition.py":"b74cdf34a96fc2d591b902e1d582e0381a8a8d08",
"canonical/runtime/auto_pypi_library_acquisition.py":"6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
"canonical/runtime/auto_python_source_codec_acquisition.py":"65453b2eed5e678def3f0ab1c4d44182fb0b9a78",
"canonical/runtime/bound_capabilities/broad_objective_decompose.py":"3ded762075ed222228a14877af631f1e2e6d9e4c",
"canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
"canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":"ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
"canonical/runtime/bound_capabilities/open_research_source_frontend.py":"830fd35c816140cb6ddb2d3dac9f0886e595d993",
"canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"46e8e7466479ea298c34e5fa682d49c374510ce9",
"canonical/runtime/capability_discovery.py":"b9e7423ab24bf2da98869b02d782e791a779892a",
"canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
"canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
"canonical/runtime/cli_contract_inference.py":"009c3c45040178844d84eaa15b0d47ca2e1f259f",
"canonical/runtime/goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
"canonical/runtime/npm_package_utils.py":"05fd0591083034df48c3ee426d6b3e11e0183555",
"canonical/runtime/python_codec_probe.py":"fc8b5005a9888422e3cb61f6cf0bd147c740ec84",
"canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py":"7e3885fa7a6e56df656c066e0a8f17cfa21424e7",
}
def git_blob_sha(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

receipt={
 "schema":"PROJECT_BRAIN_LIVEBENCH_FROZEN_RUNTIME_PACKAGE_CLOSURE_V1",
 "frozen_candidate_commit":"d5de4f5808dced840da34d051e3f9a5ff06e2e54",
 "pinned_file_count":len(EXPECTED),
 "terminal_case_content_read":False,
 "terminal_cases_consumed":0,
 "incremental_spend_usd":0,
 "external_frontier_model_calls":0,
}
for rel,want in EXPECTED.items():
    path=SUBJECT/rel
    assert path.is_file(), f"MISSING_PINNED_FILE:{rel}"
    got=git_blob_sha(path)
    assert got==want, f"BLOB_MISMATCH:{rel}:{want}:{got}"

sys.path.insert(0,str(SUBJECT))
sys.path.insert(0,str(RUNTIME))

# Prove the exact import fanout that previously failed in the terminal capsule.
from canonical.runtime import astra_runtime
from canonical.runtime import goal_compiler
import auto_capability_acquisition
import auto_apt_cli_acquisition
import auto_pypi_library_acquisition
import auto_npm_library_acquisition
import auto_python_source_codec_acquisition
import capability_discovery
import capability_planner
import capability_proposal_generators
import apt_cli_probe
import cli_contract_inference
import npm_package_utils

# Prove all known dynamic loader seams from the observed failure path without
# executing terminal cases or external acquisition.
loaders={
 "goal_compiler":astra_runtime._load_goal_compiler,
 "plain_goal_bound_grounding":astra_runtime._load_plain_goal_bound_grounding,
 "grounded_composition":astra_runtime._load_grounded_executable_composition,
 "grounded_composition_verifier":astra_runtime._load_grounded_executable_composition_verifier,
 "auto_capability_acquisition":astra_runtime._load_auto_capability_acquisition,
 "capability_planner":astra_runtime._load_capability_planner,
 "capability_discovery":astra_runtime._load_capability_discovery,
}
loaded=[]
for name,loader in loaders.items():
    loader()
    loaded.append(name)

receipt.update(
 status="PACKAGE_CLOSURE_PASS",
 dynamic_loaders_passed=loaded,
 prior_missing_dependencies_now_bound=[
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py",
  "canonical/runtime/auto_capability_acquisition.py",
 ],
)
print("LIVEBENCH_PACKAGE_CLOSURE_RECEIPT="+json.dumps(receipt,sort_keys=True))

# Separate bounded behavioral diagnostic. Its outcome is NOT part of the
# package-closure proof and cannot turn package PASS into capability FAIL.
probe=textwrap.dedent("""
import json, pathlib, sys
subject=pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0,str(subject))
sys.path.insert(0,str(subject/"canonical"/"runtime"))
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as adapter
request={
 "benchmark_id":"LIVEBENCH_IF_2026_06_25",
 "task_id":"SYNTHETIC_ZERO_CASE_INFERENCE",
 "allowed_tools":[],
 "task_payload":{"instruction":"Reply with exactly SYNTHETIC_OK."},
}
try:
 out=adapter.infer(request)
 print("SYNTHETIC_RESULT="+json.dumps(out,sort_keys=True))
except BaseException as exc:
 print("SYNTHETIC_BLOCKER="+type(exc).__name__+":"+str(exc))
 raise
""")
try:
    p=subprocess.run(
      [sys.executable,"-c",probe,str(SUBJECT)],
      text=True,capture_output=True,timeout=45,
    )
    diagnostic={
      "returncode":p.returncode,
      "stdout":p.stdout[-8000:],
      "stderr":p.stderr[-8000:],
      "timed_out":False,
    }
except subprocess.TimeoutExpired as exc:
    diagnostic={
      "returncode":None,
      "stdout":(exc.stdout or "")[-8000:] if isinstance(exc.stdout,str) else "",
      "stderr":(exc.stderr or "")[-8000:] if isinstance(exc.stderr,str) else "",
      "timed_out":True,
    }
print("LIVEBENCH_SYNTHETIC_DIAGNOSTIC="+json.dumps(diagnostic,sort_keys=True))
print("PASS: frozen LiveBench package transitive loader closure is independently proved; synthetic behavior remains separately classified")
