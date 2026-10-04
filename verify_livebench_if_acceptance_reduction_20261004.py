#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, json, urllib.request

RUN_ID=37238525973
JOB_ID=111542366567
RUN_HEAD="da386e81a634397a3051361ba2736279c9cc8c48"
RECEIPT_BLOB="165192ffa20e052f094371c04d15da6c9147a146"
RECEIPT_URL="https://raw.githubusercontent.com/moxnixmdj/verification-capsule-runner/verify-legacy15-direct-exact-20261004-v1/receipts/legacy15_joint_public_exact_v1.json"
API_RUN=f"https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/{RUN_ID}"
API_JOBS=f"https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/{RUN_ID}/jobs"
SOURCES={
 "candidate_livebench_legacy_visible_constraint_compiler_v1.py":"e986035ff68b53c0dc7a7eb478f6e3d8882214aa",
 "candidate_livebench_legacy_visible_constraint_compiler_v4.py":"011ad29ee7ca9ab27856608b3f43d2a62618dff8",
 "candidate_livebench_frozen_active_legacy15_v1.py":"34440ee69322e9d519cbe656cb03c55683a8b9c6",
 "candidate_livebench_legacy15_joint_witness_v1.py":"45d1412e9d0b23b98417e4477dd4b07d953d1c20",
 "verify_legacy15_joint_public_exact_v1.py":"9a97054aea456adb573bc009a08a83abb5ed97cc",
}
BASE="https://raw.githubusercontent.com/moxnixmdj/verification-capsule-runner/"+RUN_HEAD+"/"

def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-livebench-acceptance-verifier","Accept":"application/vnd.github+json"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read()

def blob_sha(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

# Bind to the successful public Actions execution.
run=json.loads(get(API_RUN))
assert run["status"]=="completed"
assert run["conclusion"]=="success"
assert run["head_sha"]==RUN_HEAD
jobs=json.loads(get(API_JOBS))["jobs"]
job=next(x for x in jobs if int(x["id"])==JOB_ID)
assert job["status"]=="completed" and job["conclusion"]=="success"
steps={x["name"]:x for x in job["steps"]}
for required in (
 "Set up wheel-compatible Python",
 "Install exact scorer dependencies in isolated venv",
 "Checkout exact frozen legacy scorer and NLTK assets",
 "Download exact public 200-case population",
 "Execute repaired deterministic candidate on exact public Root1",
):
    assert steps[required]["conclusion"]=="success", required

# Bind exact public receipt bytes.
rb=get(RECEIPT_URL)
assert blob_sha(rb)==RECEIPT_BLOB, (blob_sha(rb),RECEIPT_BLOB)
r=json.loads(rb)
assert r["schema"]=="PROJECT_BRAIN_LEGACY15_DETERMINISTIC_EXACT_PUBLIC_ROOT1_V1"
assert r["status"]=="PASS"
assert r["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
assert r["selected_release"]=="2026-06-25"
assert int(r["public_population"]["count"])==200
assert r["public_population"]["legacy_ifeval_only"] is True
assert r["public_population"]["parquet_sha256"]=="a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
assert r["public_population"]["task_counts"]=={"paraphrase":50,"simplify":50,"story_generation":50,"summarize":50}
assert int(r["public_population"]["terminal_or_hidden_case_count"])==0
assert r["scorer"]["family"]=="LEGACY_IFEVAL_STRICT"
assert r["scorer"]["livebench_commit"]=="8f8e5c381a16e3f24257776edd53471fe86f8091"
score=float(r["results"]["exact_four_task_mean_percent"])
exact_floor=float(r["results"]["opus_5_5_public_equal_task_mean_floor_percent"])
registry_floor=65.7
assert score==84.40416666666667
assert exact_floor==65.73775
assert score>=exact_floor>registry_floor
assert int(r["terminal_cases_consumed"])==0
assert float(r["incremental_spend_usd"])==0.0
assert r["candidate"]["hidden_ids_or_kwargs_used_by_candidate"] is False
assert int(r["candidate"]["model_dependency_count"])==0
assert r["candidate"]["network_dependency_at_runtime"] is False

# Independently bind exact candidate/verifier source and reject runtime I/O escape hatches.
allowed_import_roots={"__future__","ast","dataclasses","re","typing","hashlib","json","candidate_livebench_legacy_visible_constraint_compiler_v1","candidate_livebench_legacy_visible_constraint_compiler_v4","candidate_livebench_frozen_active_legacy15_v1"}
for path,expected in SOURCES.items():
    b=get(BASE+path)
    assert blob_sha(b)==expected,(path,blob_sha(b),expected)
    if path.startswith("candidate_"):
        tree=ast.parse(b.decode())
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                for n in node.names:
                    assert n.name.split(".")[0] in allowed_import_roots,(path,n.name)
            if isinstance(node,ast.ImportFrom):
                root=(node.module or "").split(".")[0]
                assert root in allowed_import_roots,(path,node.module)
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
                assert node.func.id not in {"open","exec","eval","compile","__import__"},(path,node.func.id)

out={
 "schema":"PROJECT_BRAIN_LIVEBENCH_IF_ACCEPTANCE_REDUCTION_PUBLIC_VERIFICATION_V1",
 "status":"PASS__EXACT_PUBLIC_THRESHOLD_RECEIPT_AND_PROMPT_ONLY_CANDIDATE_INDEPENDENTLY_VERIFIED",
 "predicate_id":"LIVEBENCH_IF_GE_65_7",
 "registry_floor_percent":registry_floor,
 "exact_comparator_floor_percent":exact_floor,
 "brain_exact_percent":score,
 "margin_over_registry_percentage_points":score-registry_floor,
 "population_count":200,
 "receipt_git_blob_sha":RECEIPT_BLOB,
 "workflow_run_id":RUN_ID,
 "workflow_job_id":JOB_ID,
 "run_head_sha":RUN_HEAD,
 "hidden_runtime_metadata_used":False,
 "model_dependency_count":0,
 "runtime_network_dependency":False,
 "terminal_or_hidden_cases_used":0,
 "incremental_spend_usd":0,
 "conclusion":"PREDICATE_PROVED_TRUE",
 "family_promotion_authorized":False,
}
print(json.dumps(out,sort_keys=True))
