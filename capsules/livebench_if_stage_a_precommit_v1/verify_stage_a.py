from __future__ import annotations
import hashlib,json,os,shutil,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CAP=Path(__file__).resolve().parent
MANIFEST=CAP/"MANIFEST.json"

def git_blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def canonical_sha256(value)->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

m=json.loads(MANIFEST.read_text())
assert m["schema"]=="PROJECT_BRAIN_LIVEBENCH_IF_STAGE_A_PRECOMMIT_V1"
assert m["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
assert m["stage_a"]["terminal_case_content_read"] is False
assert m["stage_a"]["terminal_dataset_download"] is False
assert m["stage_a"]["terminal_cases_consumed"]==0
assert m["policy"]["fresh_reality_authority"] is False
assert m["policy"]["execution_authority"] is False
assert m["policy"]["promotion_authority"] is False

capsule=ROOT/m["candidate"]["public_capsule_root"]
for rel,expected in m["candidate"]["exact_blobs"].items():
    got=git_blob_sha(capsule/rel)
    assert got==expected,(rel,got,expected)

response=ROOT/m["candidate"]["response_adapter_path"]
assert git_blob_sha(response)==m["candidate"]["response_adapter_blob_sha"]

assert os.environ.get("RUNNER_OS")=="Linux"
assert m["environment"]["runner"]=="ubuntu-24.04"
assert m["environment"]["runner_class"]=="STANDARD_GITHUB_HOSTED"
assert m["environment"]["paid_or_larger_runner_allowed"] is False
assert m["policy"]["external_model_or_learned_capability_provider_allowed"] is False
assert m["policy"]["optional_model_planner_allowed"] is False
assert m["policy"]["required_cognition_dependency_class"]=="MODEL_INDEPENDENT"
assert m["policy"]["external_tools_allowed"]==[]
assert m["policy"]["case_reveal_before_precommit_forbidden"] is True
assert m["policy"]["adaptive_case_selection"] is False
assert m["policy"]["case_replacement"] is False
assert m["policy"]["tuning_replay"] is False
assert m["policy"]["retry_after_scored_failure"] is False
assert m["policy"]["result_feedback_to_committed_components"] is False
assert m["policy"]["unrelated_work_mutation_of_committed_components"] is False
assert m["policy"]["results_bound_to_commitment_required"] is True
assert m["policy"]["result_escrow_until_full_wave_finalization"] is True

components=("candidate","harness","scorer","environment","policy")
hashes={name+"_sha256":canonical_sha256(m[name]) for name in components}
commitment=canonical_sha256(hashes)

mem_kib=0
try:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            mem_kib=int(line.split()[1]); break
except Exception:
    pass
disk=shutil.disk_usage("/")

out={
  "schema":"PROJECT_BRAIN_LIVEBENCH_IF_STAGE_A_PRECOMMIT_RESULT_V1",
  "status":"PASS__PREEXPOSURE_FIVE_COMPONENT_COMMITMENT__ZERO_CASES__ZERO_CREDIT",
  **hashes,
  "commitment_sha256":commitment,
  "manifest_git_blob_sha":git_blob_sha(MANIFEST),
  "runner_snapshot":{
    "runner_os":os.environ.get("RUNNER_OS"),
    "cpu_count":os.cpu_count(),
    "memory_total_bytes":mem_kib*1024,
    "disk_total_bytes":disk.total,
    "disk_free_bytes":disk.free,
    "python_version":sys.version.split()[0],
  },
  "synthetic_astra_capsule_preflight_required":True,
  "synthetic_58_checker_preflight_required":True,
  "terminal_case_content_read":False,
  "terminal_dataset_downloaded":False,
  "terminal_cases_consumed":0,
  "new_reality_units_consumed":0,
  "generic_isolation_instantiation_proved":False,
  "fresh_reality_authority":False,
  "execution_authority":False,
  "promotion_authority":False,
  "acceptance_credit_delta":0,
}
print("PRECOMMIT_RESULT_JSON="+json.dumps(out,sort_keys=True,separators=(",",":")))
