#!/usr/bin/env python3
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
import types

ROOT=pathlib.Path(__file__).resolve().parent
FILES={
 "input":("subjects/tool_discovery_multilingual_retrieval_input_v1.json","a244205a759144bbe01f25c2c9101ef6045efd79"),
 "benchmark":("subjects/tool_discovery_retrieval_false_negative_benchmark_v1.py","0e8779e7acdf7a5a64c55403e7db795165027f6d"),
 "tests":("subjects/test_tool_discovery_retrieval_false_negative_benchmark_v1.py","ecd53d3e3d7cad22ee247a35b574330d4d791139"),
 "compiler":("subjects/residual_witness_retrieval_compiler_v1.py","9daa8d590f3356b3fc51eccf75c56cbf515239e4")
}

def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

for name,(rel,expected) in FILES.items():
    actual=blob(ROOT/rel)
    assert actual==expected,(name,actual,expected)

# Build only the package namespace required by the exact benchmark subject.
canonical=types.ModuleType("canonical")
runtime=types.ModuleType("canonical.runtime")
canonical.runtime=runtime
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime

cspec=importlib.util.spec_from_file_location(
    "canonical.runtime.residual_witness_retrieval_compiler_v1",
    ROOT/FILES["compiler"][0],
)
compiler=importlib.util.module_from_spec(cspec)
sys.modules[cspec.name]=compiler
cspec.loader.exec_module(compiler)
runtime.residual_witness_retrieval_compiler_v1=compiler

bspec=importlib.util.spec_from_file_location(
    "canonical.runtime.tool_discovery_retrieval_false_negative_benchmark_v1",
    ROOT/FILES["benchmark"][0],
)
benchmark=importlib.util.module_from_spec(bspec)
sys.modules[bspec.name]=benchmark
bspec.loader.exec_module(benchmark)

source=json.loads((ROOT/FILES["input"][0]).read_text(encoding="utf-8"))
out=benchmark.evaluate(source)
assert out["pass"] is True,out
assert out["finite_supported_fixture_recall"]==1.0,out
assert out["supported_fixture_count"]==24,out
assert out["supported_fixture_found_count"]==24,out
assert out["supported_fixture_missed_count"]==0,out
assert out["unsupported_boundary_count"]==5,out
assert all(x["nonexistence_claim_authorized"] is False for x in out["unsupported_boundaries"]),out
for key in ("zh","ar","ru","ja","ko","es","fr","de","pt","hi","tr","id","vi"):
    assert key in out["explicit_language_variant_keys"],(key,out["explicit_language_variant_keys"])
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0,out
assert out["execution_authority"] is False and out["promotion_authority"] is False,out

# Falsification sensitivity: remove Chinese variants.
mut=copy.deepcopy(source)
mut["language_variants"].pop("zh")
zh=benchmark.evaluate(mut)
assert zh["pass"] is False,zh
assert zh["finite_supported_fixture_recall"]<1.0,zh
assert "ZH_METADATA_ONLY" in {x["fixture_id"] for x in zh["missed_fixtures"]},zh

# Falsification sensitivity: remove route identifier from every compiled source.
mut=copy.deepcopy(source)
mut["aliases"]=[x for x in mut["aliases"] if "valid_route_top1" not in x]
mut["required_capabilities"]=[x for x in mut["required_capabilities"] if "valid_route_top1" not in x]
mut["observables"]["api_symbols"]=[x for x in mut["observables"]["api_symbols"] if x!="valid_route_top1"]
route=benchmark.evaluate(mut)
assert route["pass"] is False,route
assert "DESCRIPTIONLESS_CODE_IDENTIFIER" in {x["fixture_id"] for x in route["missed_fixtures"]},route

print("TOOL_DISCOVERY_RETRIEVAL_RECALL_V1_VERIFIED")
print(json.dumps({
 "exact_blobs":{k:v[1] for k,v in FILES.items()},
 "supported_fixture_count":out["supported_fixture_count"],
 "finite_supported_fixture_recall":out["finite_supported_fixture_recall"],
 "unsupported_boundary_count":out["unsupported_boundary_count"],
 "chinese_mutation_detected":True,
 "route_identifier_mutation_detected":True,
 "zero_credit":True,
},sort_keys=True))
