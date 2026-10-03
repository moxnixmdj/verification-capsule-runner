import hashlib, json, os, urllib.request
from pathlib import Path

ROOT=Path("capsules/science_canary_v2")
CAND=ROOT/"TB_SCIENCE_ONE_SLOT_CANARY_CANDIDATE_V2.json"
OVER=ROOT/"TB_SCIENCE_CURRENT_TARGET_EXECUTION_OVERLAY_V1.json"
MAN=ROOT/"TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json"

def gblob(p: Path) -> str:
    b=p.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()

def get_json(url: str):
    headers={"User-Agent":"project-brain-science-canary-verifier/1"}
    tok=os.environ.get("GITHUB_TOKEN")
    if tok and "api.github.com" in url:
        headers["Authorization"]="Bearer "+tok
        headers["X-GitHub-Api-Version"]="2022-11-28"
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=40) as r:
        return json.loads(r.read().decode())

c=json.loads(CAND.read_text())
o=json.loads(OVER.read_text())
m=json.loads(MAN.read_text())

# Exact candidate/overlay/manifest binding.
assert c["schema"]=="PROJECT_BRAIN_TB_SCIENCE_ONE_SLOT_CANARY_CANDIDATE_V2"
assert c["execution_authority"] is False and c["promotion_authority"] is False
assert gblob(OVER)==c["current_target_overlay"]["git_blob_sha"]
assert gblob(MAN)==c["exact_route"]["manifest_blob"]
assert gblob(MAN)=="6dfa880b1f68881531afbba6ca211681801fd19b"
assert m["frozen_dataset"]["source_commit"]=="f81afac4f11048e77a15dfc8fb1dbfb897fea0ce"
assert m["frozen_dataset"]["task_count"]==70
assert m["frozen_dataset"]["trials_per_task"]==3
assert m["frozen_dataset"]["slot_count"]==210
assert len(m["slots"])==210

# Re-derive the current Opus 5.5 target from public checked provenance.
atlas=get_json("https://aicharts.io/data/benchmark-atlas/terminal-bench-science")
ds=atlas["dataset"]
assert ds["version"]=="0.1.0"
assert ds["source"]["revision"]=="f81afac4f11048e77a15dfc8fb1dbfb897fea0ce"
rows=[p for p in ds["points"] if p.get("model")=="Opus 5.5" and p.get("harness")=="Claude Code" and p.get("effort")=="max"]
assert len(rows)==1
row=rows[0]
assert row["id"]=="cb24f3a2-82ab-4f97-be88-92a28118bf1c"
assert abs(float(row["score"])-(133/210*100)) < 1e-12
assert "/terminal-bench-science/terminal-bench-science/0.1.0/" in row["sourceUrl"]

tag=get_json("https://api.github.com/repos/harbor-framework/terminal-bench-science/git/ref/tags/v0.1.0")
assert tag["object"]["sha"]=="f81afac4f11048e77a15dfc8fb1dbfb897fea0ce"
assert o["current_comparator"]["exact_percent"]==row["score"]
assert o["current_comparator"]["required_successes"]==133
assert o["current_comparator"]["fail_lock_failures"]==78
assert o["current_comparator"]["verification_git_blob_sha"]=="3bff4c8ec68bba45d0538812101fbbfed7b9b2ec"
assert c["current_target_overlay"]["required_successes"]==133
assert c["current_target_overlay"]["fail_lock_failures"]==78

# Reconstruct the actually consumed tranche from the public execution run.
run_id=37101712032
jobs=get_json(f"https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/{run_id}/jobs?per_page=100")["jobs"]
assert len(jobs)==3
assert all(j["status"]=="completed" and j["conclusion"]=="success" for j in jobs)
art=get_json(f"https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/{run_id}/artifacts?per_page=100")["artifacts"]
names={a["name"] for a in art}
assert names=={
  "tb-science-genomic-model-ranking-trial-0",
  "tb-science-mri-harmonization-trial-0",
  "tb-science-navigation-sensor-calibration-trial-0",
}, names
consumed=c["permanently_consumed_slots"]
assert consumed==[
  "terminal-bench-science/genomic-model-ranking::trial-0",
  "terminal-bench-science/mri-harmonization::trial-0",
  "terminal-bench-science/navigation-sensor-calibration::trial-0",
]

# First untouched slot is mechanically selected from frozen schedule.
ordered=sorted(m["slots"],key=lambda x:x["schedule_order"])
remaining=[x for x in ordered if x["slot_id"] not in set(consumed)]
assert remaining
first=remaining[0]
cand=c["authorized_slot_candidate"]
assert first["schedule_order"]==3
for k in ("slot_id","schedule_order","attempt_index","task_rank","task_name","task_digest","standard_public_storage_feasible"):
    assert cand[k]==first[k], (k,cand[k],first[k])
assert cand["slot_id"] not in set(consumed)

# Exact current repaired route bytes already preserved in public verifier repo.
runtime=Path("capsules/tb_science_local_qwen_planner_repair_v1/canonical/runtime")
assert gblob(runtime/"harbor_science_agent_v1.py")==c["exact_route"]["controller_blob"]=="5557efd21f1a433ad16766def3775a79c459784b"
assert gblob(runtime/"harbor_science_planner_v1.py")==c["exact_route"]["planner_blob"]=="879887984e2ca8abacac486d687f519f5d0d78a5"
assert gblob(runtime/"harbor_command_policy.py")==c["exact_route"]["command_policy_blob"]=="a525773417291c7a4841bf35e1baff5370350d0d"
assert gblob(runtime/"harbor_environment_transport.py")==c["exact_route"]["environment_transport_blob"]=="ec46f648214a37bb16025d5ef2593efdf59f0d79"
sg=Path("canonical/runtime/acceptance_capability_source_gate_v2.py")
assert gblob(sg)==c["exact_route"]["source_gate_blob"]=="b168b131f6383e158bdc0d931439d14e61f2a5de"

sem=c["execution_semantics"]
assert sem=={
 "slots_authorized_if_promoted":1,
 "retries_per_slot":0,
 "slot_replacement":False,
 "denominator_shrink":False,
 "duplicate_slot_credit":False,
 "exact_success_rule":"reward >= 1.0",
 "auto_revoke_after_slot_finalization":True,
 "stop_after_canary":True,
}

assert o["reduction"]["finalized_slots"]==3
assert o["reduction"]["successes"]==0
assert o["reduction"]["finalized_failures"]==3
assert o["reduction"]["successes_remaining_for_pass_lock"]==133
assert o["reduction"]["failures_remaining_before_fail_lock"]==75

print(json.dumps({
 "schema":"PROJECT_BRAIN_TB_SCIENCE_ONE_SLOT_CANARY_V2_INDEPENDENT_CHECK",
 "status":"PASS",
 "candidate_blob":gblob(CAND),
 "overlay_blob":gblob(OVER),
 "manifest_blob":gblob(MAN),
 "current_target_percent":row["score"],
 "required_successes":133,
 "fail_lock_failures":78,
 "consumed_slots":consumed,
 "first_untouched_slot":cand["slot_id"],
 "first_untouched_schedule_order":cand["schedule_order"],
 "exact_route_blobs_pass":True,
 "execution_authority":False,
 "promotion_authority":False,
 "capability_credit_delta":0,
 "family_credit_delta":0
},sort_keys=True))
