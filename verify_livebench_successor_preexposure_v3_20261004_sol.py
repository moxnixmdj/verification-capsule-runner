#!/usr/bin/env python3
import importlib.util, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parent
PLAN=ROOT/"subject/livebench_successor_preexposure_v3_20261004_sol/LIVEBENCH_IF_SHADOW_PREEXPOSURE_PLAN_V3.json"
PRE=ROOT/"subject/livebench_successor_precommit_v2_20261004/LIVEBENCH_IF_EXECUTION_PRECOMMIT_V2.json"
VER=ROOT/"subject/shadow_lease_v2_20261004/pre_exposure_isolation_plan_v1.py"

spec=importlib.util.spec_from_file_location("pre_exposure_v1",VER)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
plan=json.loads(PLAN.read_text())
pre=json.loads(PRE.read_text())
out=mod.verify_pre_exposure_plan(plan)
assert out["pre_exposure_plan_pass"] is True,out
assert out["case_reveal_authority"] is False
assert out["execution_authority"] is False
assert out["fresh_reality_authority"] is False
assert out["acceptance_credit_authorized"] is False

for k in ("candidate","harness","scorer","environment","policy"):
    assert plan[f"{k}_sha256"]==pre["component_sha256"][k],k
    assert plan[f"pre_reveal_observed_{k}_sha256"]==pre["component_sha256"][k],k

assert plan["plan_sha256"]=="9608157e7ef52fab08bc387bb19ccfb10001cbb5367849a9806d6b0e7df34b31"
assert plan["commitment_sha256"]=="58ee189b9c035e3e7e96897193c2b6b9fa5b612a0394ca70d55bd0c562be5bca"
assert plan["case_reveal_has_occurred"] is False
assert plan["execution_has_started"] is False
assert plan["evaluation_output_exists"] is False
print(json.dumps({"status":"PASS","plan_sha256":plan["plan_sha256"],"component_count":5,"terminal_cases_consumed":0,"case_reveal_authority":False},sort_keys=True))
