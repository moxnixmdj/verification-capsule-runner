#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib

BASE=pathlib.Path("subject/root2_19_reactivation_20261004_sol")
FILES={
 "reactivation":"ROOT2_19_PREDICATE_POST_LIVEBENCH_REVOCATION_REACTIVATION_V1.json",
 "root":"TERMINAL_ROOT_CAUSE_STATE_V1.json",
 "manifest":"ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V1.json",
 "activation":"ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_ACTIVATION_V1.json",
 "dag_ver":"ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
 "act_ver":"ROOT2_OUTPUT_ONLY_THRESHOLD_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
 "revocation":"LIVEBENCH_FORCED_FAIL_ROOT1_REVOCATION_20261004_V1.json",
 "scope":"LIVEBENCH_TERMINAL_SCORER_SCOPE_ACTIVATION_V1.json",
}
EXPECTED={
 "reactivation":"2290a4e553cc0d685fc2a0ecaefe8621fea1c206",
 "root":"e8371418ed39b83b14df874c8eb5e0bdb6a2e603",
 "manifest":"1fba51d15bcfdf6accd90948155517f7c9b98bbb",
 "activation":"7ea4dd4edb59c8526bd3993e02f4a8fb53c65085",
 "dag_ver":"553602570334f39003708e52d781b8c59f27eb7c",
 "act_ver":"eef494009e47b758a99ab48649e050c332e4988a",
 "revocation":"bbbe29ec26b1f96ba5538ca159f899e316b167e7",
 "scope":"f64fe4a10c3b7f8a8a95819fb79c898d17a2bae4",
}
def blob(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(k):
    p=BASE/FILES[k]
    got=blob(p)
    assert got==EXPECTED[k],(k,got,EXPECTED[k])
    return json.loads(p.read_text())
O={k:load(k) for k in FILES}
r=O["reactivation"]; root=O["root"]; m=O["manifest"]; a=O["activation"]
dv=O["dag_ver"]; av=O["act_ver"]; rev=O["revocation"]; scope=O["scope"]

# Exact current partition from canonical root state.
part=root["current_residual_root_partition"]
assert part["unresolved_total"]==26
assert part["root1_positive_gap_count"]==0
assert part["root2_only_count"]==16
assert part["root3_only_count"]==7
assert part["root2_and_root3_count"]==3
assert part["root1_only_count"]==0
root2=set(part["root2_only"])|set(part["root2_and_root3"])
assert len(root2)==19
assert "LIVEBENCH_IF_GE_65_7" in set(part["root2_only"])
assert "LIVEBENCH_IF_GE_65_7" not in set(part["root1_only"])

# Candidate is bound to exact current root blob and projects the same 19-set.
assert r["current_root_binding"]["git_blob_sha"]==EXPECTED["root"]
cand=set(r["current_root_binding"]["exact_root2_touching_predicates"])
assert cand==root2
assert r["current_root_binding"]["root2_touching_count"]==19
assert r["current_root_binding"]["root1_positive_gap_count"]==0

# Reused DAG domain is exactly the same set and has already passed independent verification.
dag_ids={x["id"] for x in m["predicates"]}
assert len(dag_ids)==19
assert dag_ids==root2
assert r["reused_verified_controller"]["subject_manifest_git_blob_sha"]==EXPECTED["manifest"]
assert r["reused_verified_controller"]["activation_git_blob_sha"]==EXPECTED["activation"]
assert r["reused_verified_controller"]["subject_verification_git_blob_sha"]==EXPECTED["dag_ver"]
assert r["reused_verified_controller"]["prior_activation_verification_git_blob_sha"]==EXPECTED["act_ver"]
assert dv["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert dv["subject"]["manifest_git_blob_sha"]==EXPECTED["manifest"]
assert dv["verified"]["predicate_count"]==19
assert dv["verified"]["execution_authority"] is False
assert dv["verified"]["promotion_authority"] is False
assert dv["verified"]["fresh_reality_authority"] is False
assert av["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert av["subjects"]["activation_git_blob_sha"]==EXPECTED["activation"]
assert av["verified"]["root2_touching_predicates"]==19
assert av["verified"]["root1_positive_gaps"]==0
assert av["verified"]["fresh_reality_block_preserved"] is True

# LiveBench truth repair is Root2-only and scorer surface is legacy IFEval only.
assert r["livebench_truth_repair"]["revocation_git_blob_sha"]==EXPECTED["revocation"]
assert r["livebench_truth_repair"]["scorer_scope_activation_git_blob_sha"]==EXPECTED["scope"]
assert rev["corrected_current_projection"]["livebench_class"]=="ROOT2_ONLY__MEASUREMENT_OR_COMPARATOR_UNCERTAINTY"
assert rev["corrected_current_projection"]["root1_positive_gap_count"]==0
assert scope["activated_scheduler_truth"]["active_scorer_family"]=="LEGACY_IFEVAL_ONLY"
assert scope["activated_scheduler_truth"]["active_population_count"]==200
assert scope["activated_scheduler_truth"]["load_bearing_checker_registry_count"]==25
assert scope["activated_scheduler_truth"]["modern_ifbench_checker_count_on_exact_frozen_critical_path"]==0

# Reactivation itself remains scheduling-only until this exact projection check passes.
assert r["authority"]=={
 "scheduling":False,"execution":False,"promotion":False,
 "fresh_reality":False,"acceptance_credit":False
}
assert all(r["accounting"][k]==0 for k in r["accounting"])
assert "INDEPENDENT_EXACT_ROOT_PROJECTION_VERIFICATION_REQUIRED_BEFORE_SCHEDULING_AUTHORITY_TRUE" in r["hard_rules"]

print("ROOT2_19_REACTIVATION_PROJECTION=PASS")
print("root2_touching=19")
print("root1_positive_gap_count=0")
print("livebench_class=ROOT2_ONLY")
print("livebench_scorer=LEGACY_IFEVAL_ONLY")
print("verified_dag_domain_identity=EXACT")
print("fresh_reality_authority=false")
print("acceptance_credit_delta=0")
