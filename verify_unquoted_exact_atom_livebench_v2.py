#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import types

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"unquoted_exact_atom_v1"
EXPECTED={
  "instruction_constraint_compiler_v1.py":"a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
  "root2_livebench_if_astra_inference_adapter_v2.py":"dbc895a0e458e411aafd3c96e0ddc2c01e657375",
}

def git_blob_sha(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load_file(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("IMPORT_SPEC_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

def main()->int:
    for name,expected in EXPECTED.items():
        observed=git_blob_sha(SUB/name)
        if observed!=expected:
            raise AssertionError(f"BLOB_DRIFT:{name}:{observed}:{expected}")

    compiler=load_file("verify_instruction_constraint_compiler_v1",SUB/"instruction_constraint_compiler_v1.py")

    atom_cases=[
      ("Reply with exactly SYNTHETIC_OK.","SYNTHETIC_OK"),
      ("Answer exactly BETA_7.","BETA_7"),
      ("Output exactly TOKEN-3.","TOKEN-3"),
      ("Say exactly ns:value.","ns:value"),
      ('Reply with exactly "QUOTED_OK".',"QUOTED_OK"),
    ]
    for instruction,expected in atom_cases:
        out=compiler.synthesize_formal_only(instruction)
        assert out["status"]=="PASS",(instruction,out)
        assert out["response"]==expected,(instruction,out)
        assert out["semantic_seed_required"] is False,(instruction,out)
        ok,errors=compiler.validate_response(out["response"],compiler.compile_constraints(instruction))
        assert ok,(instruction,errors)

    blocked=[
      "Reply with exactly two words.",
      "Reply with exactly ALPHA. Then explain why.",
      "Explain photosynthesis clearly.",
    ]
    for instruction in blocked:
        out=compiler.synthesize_formal_only(instruction)
        assert out["status"]!="PASS",(instruction,out)

    canonical=types.ModuleType("canonical")
    runtime=types.ModuleType("canonical.runtime")
    canonical.runtime=runtime
    runtime.instruction_constraint_compiler_v1=compiler

    fallback=types.ModuleType("canonical.runtime.root2_livebench_if_astra_inference_adapter_v1")
    calls=[]
    def fallback_infer(request):
        calls.append(request)
        return {"status":"FALLBACK_SENTINEL"}
    fallback.infer=fallback_infer
    runtime.root2_livebench_if_astra_inference_adapter_v1=fallback

    sys.modules["canonical"]=canonical
    sys.modules["canonical.runtime"]=runtime
    sys.modules["canonical.runtime.instruction_constraint_compiler_v1"]=compiler
    sys.modules["canonical.runtime.root2_livebench_if_astra_inference_adapter_v1"]=fallback

    adapter=load_file(
      "canonical.runtime.root2_livebench_if_astra_inference_adapter_v2",
      SUB/"root2_livebench_if_astra_inference_adapter_v2.py"
    )
    runtime.root2_livebench_if_astra_inference_adapter_v2=adapter

    def req(text,tools=None):
        return {
          "benchmark_id":"LIVEBENCH_IF_2026_06_25",
          "task_id":"synthetic-public-zero-case",
          "task_payload":{"instruction":text},
          "allowed_tools":[] if tools is None else tools,
        }

    out=adapter.infer(req("Reply with exactly SYNTHETIC_OK."))
    assert out["status"]=="PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",out
    assert out["answer"]=="SYNTHETIC_OK",out
    assert out["model_dependency_count"]==0,out
    assert out["response_route"]=="VERIFIED_GENERIC_FORMAL_CONSTRAINT_COMPILER_V1",out
    assert calls==[],calls

    out=adapter.infer(req("Explain photosynthesis clearly."))
    assert out=={"status":"FALLBACK_SENTINEL"},out
    assert len(calls)==1,calls

    try:
        adapter.infer(req("Reply with exactly SAFE.",["browser"]))
    except adapter.Root2InferenceBlocked:
        pass
    else:
        raise AssertionError("EXTERNAL_TOOLS_NOT_REJECTED")

    print(json.dumps({
      "schema":"PROJECT_BRAIN_UNQUOTED_EXACT_ATOM_LIVEBENCH_V2_PUBLIC_VERIFICATION_V1",
      "conclusion":"PASS",
      "exact_subject_blobs":EXPECTED,
      "generic_unquoted_atom_cases":4,
      "quoted_regression_case":1,
      "fail_closed_cases":3,
      "canonical_public_synthetic_instruction":"PASS",
      "adapter_fast_path":"PASS",
      "semantic_fallback_preserved":True,
      "external_tools_forbidden":True,
      "network_used":False,
      "terminal_cases_consumed":0,
      "acceptance_credit_delta":0,
    },indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
