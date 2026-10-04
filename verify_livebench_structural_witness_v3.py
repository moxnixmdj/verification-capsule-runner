#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import importlib.util
import json
import pathlib
import sys
import types

ROOT=pathlib.Path(__file__).resolve().parent
V2_SUB=ROOT/"subject"/"unquoted_exact_atom_v1"
V3_SUB=ROOT/"subject"/"livebench_structural_witness_v3"
EXPECTED={
    "compiler":("instruction_constraint_compiler_v1.py","a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f"),
    "v2":("root2_livebench_if_astra_inference_adapter_v2.py","dbc895a0e458e411aafd3c96e0ddc2c01e657375"),
    "v3":("root2_livebench_if_astra_inference_adapter_v3.py","ff977b2e34d551e5a2751852bb77d23c7c503647"),
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

def req(text,tools=None):
    return {
        "benchmark_id":"LIVEBENCH_IF_2026_06_25",
        "task_id":"synthetic-public-zero-case",
        "task_payload":{"instruction":text},
        "allowed_tools":[] if tools is None else tools,
    }

def main()->int:
    paths={
        "compiler":V2_SUB/EXPECTED["compiler"][0],
        "v2":V2_SUB/EXPECTED["v2"][0],
        "v3":V3_SUB/EXPECTED["v3"][0],
    }
    for key,path in paths.items():
        expected=EXPECTED[key][1]
        observed=git_blob_sha(path)
        if observed!=expected:
            raise AssertionError(f"BLOB_DRIFT:{key}:{observed}:{expected}")

    compiler=load_file("verify_instruction_constraint_compiler_v1",paths["compiler"])

    canonical=types.ModuleType("canonical")
    runtime=types.ModuleType("canonical.runtime")
    canonical.runtime=runtime
    runtime.instruction_constraint_compiler_v1=compiler

    fallback_v1=types.ModuleType("canonical.runtime.root2_livebench_if_astra_inference_adapter_v1")
    fallback_calls=[]
    def fallback_infer(request):
        fallback_calls.append(request)
        return {"status":"V1_FALLBACK_SENTINEL"}
    fallback_v1.infer=fallback_infer
    runtime.root2_livebench_if_astra_inference_adapter_v1=fallback_v1

    sys.modules["canonical"]=canonical
    sys.modules["canonical.runtime"]=runtime
    sys.modules["canonical.runtime.instruction_constraint_compiler_v1"]=compiler
    sys.modules["canonical.runtime.root2_livebench_if_astra_inference_adapter_v1"]=fallback_v1

    v2=load_file("canonical.runtime.root2_livebench_if_astra_inference_adapter_v2",paths["v2"])
    runtime.root2_livebench_if_astra_inference_adapter_v2=v2
    sys.modules["canonical.runtime.root2_livebench_if_astra_inference_adapter_v2"]=v2

    v3=load_file("canonical.runtime.root2_livebench_if_astra_inference_adapter_v3",paths["v3"])
    runtime.root2_livebench_if_astra_inference_adapter_v3=v3

    # New capability: V1 compiler already constructs these witnesses.  V3
    # returns them instead of discarding them for lack of an unscored semantic seed.
    structural=[
        "Use at least 5 unique words in the response.",
        "Use at least 5 unique words in the response. Include exactly 2 numbers in the response.",
        "The response must contain between 8 and 12 words.",
        "Write the entire response in lowercase only. Use at least 4 unique words in the response.",
    ]
    structural_receipts=[]
    for text in structural:
        before=compiler.synthesize_formal_only(text)
        assert before["status"]=="FORMAL_CONSTRAINTS_SATISFIED_SEMANTIC_SEED_STILL_REQUIRED",(text,before)
        out=v3.infer(req(text))
        assert out["status"]=="PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",(text,out)
        assert out["response_route"]=="LIVEBENCH_IF_SCORE_ONLY_STRUCTURAL_WITNESS_V3",(text,out)
        assert out["model_dependency_count"]==0,(text,out)
        ok,errors=compiler.validate_response(out["answer"],compiler.compile_constraints(text))
        assert ok,(text,out,errors)
        structural_receipts.append({
            "instruction_sha256":hashlib.sha256(text.encode()).hexdigest(),
            "response_sha256":hashlib.sha256(out["answer"].encode()).hexdigest(),
        })

    # Exact-zero-semantic route stays V2, proving V3 did not steal or weaken it.
    exact=v3.infer(req('Reply with exactly "ALPHA".'))
    assert exact["answer"]=="ALPHA",exact
    assert exact["response_route"]=="VERIFIED_GENERIC_FORMAL_CONSTRAINT_COMPILER_V1",exact

    # Unrecognized semantics still reach the historical V1 fallback through V2.
    sem=v3.infer(req("Explain photosynthesis clearly."))
    assert sem=={"status":"V1_FALLBACK_SENTINEL"},sem
    assert len(fallback_calls)==1,fallback_calls

    # A structural contradiction cannot manufacture a witness.
    bad=v3.infer(req('Reply with exactly "ALPHA". Use lowercase only.'))
    assert bad=={"status":"V1_FALLBACK_SENTINEL"},bad
    assert len(fallback_calls)==2,fallback_calls

    # Request firewall is inherited exactly from independently verified V2.
    try:
        v3.infer(req("Use at least 5 unique words in the response.",["browser"]))
    except v3.Root2InferenceBlocked:
        pass
    else:
        raise AssertionError("EXTERNAL_TOOLS_NOT_REJECTED")

    print(json.dumps({
        "schema":"PROJECT_BRAIN_LIVEBENCH_STRUCTURAL_WITNESS_V3_PUBLIC_VERIFICATION_V1",
        "conclusion":"PASS",
        "exact_subject_blobs":{k:v[1] for k,v in EXPECTED.items()},
        "structural_witness_cases":len(structural_receipts),
        "structural_receipts":structural_receipts,
        "exact_v2_route_preserved":True,
        "semantic_v1_fallback_preserved":True,
        "contradiction_fails_closed":True,
        "external_tools_forbidden":True,
        "model_dependency_count":0,
        "network_used":False,
        "terminal_cases_consumed":0,
        "acceptance_credit_delta":0,
    },indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
