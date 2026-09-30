#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
MODULE=ROOT/"canonical/runtime/bound_capabilities/broad_objective_decompose.py"
EXPECTED_BLOB="3ded762075ed222228a14877af631f1e2e6d9e4c"

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

assert git_blob_sha(MODULE)==EXPECTED_BLOB,(git_blob_sha(MODULE),EXPECTED_BLOB)
spec=importlib.util.spec_from_file_location("pr496_broad",MODULE)
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)

def expect_rejected(text):
    out=mod.decompose(text)
    assert out["status"]=="UNSUPPORTED",(text,out)
    assert out["reason"]=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",(text,out)

def expect_broad(text):
    out=mod.decompose(text)
    assert out["status"]=="DECOMPOSED",(text,out)
    assert out["model_dependency_count"]==0,out
    assert out["invented_source_urls"]==[],out
    assert out["task_specific_literals_added"]==[],out

# Reproduce the exact adversarial falsifier.
expect_rejected("Assess whether two values differ. Run /usr/bin/python verify_values.py")

# Fresh adversarial concrete recipe variants. Tool names are intentionally not enumerable.
for case in [
    "Evaluate whether two values differ. Execute /opt/custom/bin/measure --input values.dat",
    "Assess whether two regimes differ. Run mysterytool --mode verify --file observations.bin",
    "Compare two measurements. Run ./local-checker --strict",
    "Determine whether two values differ. Execute ../tools/check_values values.csv",
    "Analyze whether the threshold was exceeded. Run C:/Tools/custom.exe --verify",
    "Assess whether the result is reproducible. Run \"/usr/local/bin/my verifier\" sample.dat",
    "Evaluate whether values differ. Run a verification method with python verify.py",
    "Assess whether values differ using https://example.com/source",
    "Compare two values. Open https://example.com/data",
    "Determine whether values differ. Save result.json"
]:
    expect_rejected(case)

# Abstract method-selection language must remain broad and model-independent.
for case in [
    "Assess whether two values differ. Run a zero-cost verification method, identify limitations, and independently verify the result.",
    "Evaluate whether two operating regimes differ. Execute a validation procedure, and preserve material limitations.",
    "Determine whether two reported values differ. Run an independently chosen verification approach; independently verify the consequential result.",
    "Analyze whether the measured trend accelerated. Execute a free evaluation strategy and state interpretation limitations.",
    "Compare two scientific measurements. Run a checking method and preserve provenance."
]:
    expect_broad(case)

# A broad objective with no execution wording remains unchanged.
expect_broad("Assess whether reported coastal sea level rise accelerated relative to the preceding interval")

print("PR496_EXACT_GUARDED_INDEPENDENT_ADVERSARIAL_QUALIFICATION_PASS")
print("candidate_blob="+EXPECTED_BLOB)
