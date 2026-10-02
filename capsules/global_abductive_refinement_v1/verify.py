from __future__ import annotations
import importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def load(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

def load_runtime():
    spec=importlib.util.spec_from_file_location("abductive_runtime", ROOT/"abductive_runtime.py")
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

frontier=load("frontier.json")
sub=load("matched_subfrontier.json")
sched_v=load("scheduling_verification.json")
matched_v=load("matched_refinement_verification.json")
candidate=load("global_candidate.json")
refine=load("refinement_candidate.json")
registry=load("predicate_registry.json")
recon=load("deleted_private_reconciliation.json")
runtime=load_runtime()

assert sched_v["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert sched_v["exact_brain_blobs"]["canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"]=="4b5517dbd12978f8ffe481fb775e85592c7790c8"
assert matched_v["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert matched_v["exact_brain_blobs"]["canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json"]=="89162df13fae66edabaa53ac9c8d95a88829e3ec"

implications=[]
for cert in frontier["certificates"]:
    if cert["id"]=="MATCHED_SCOPE_BINDING_CERTIFICATE":
        continue
    implications.append({
        "edge_id":"GLOBAL::"+cert["id"],
        "if_all":cert["requires"],
        "then":cert["target_predicates"],
        "verified":True,
        "independent":True,
        "receipt":"canonical/verification/TERMINAL_SCHEDULING_ACTIVATION_V5_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    })
for cert in sub["certificates"]:
    implications.append({
        "edge_id":"MATCHED::"+cert["id"],
        "if_all":cert["requires"],
        "then":cert["target_predicates"],
        "verified":True,
        "independent":True,
        "receipt":"canonical/verification/MATCHED_SCOPE_HIERARCHICAL_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    })

out=runtime.evaluate({
    "targets":frontier["unresolved_predicates"],
    "baseline_facts":[],
    "implications":implications,
})
assert out["status"]=="EXACT_WEAKEST_SUFFICIENT_RESIDUALS_COMPUTED", out
assert out["target_count"]==31
assert out["verified_rule_count"]==27
assert out["atom_count"]==71
assert len(out["primitive_residual_facts"])==40
assert out["minimum_joint_residual_size"]==40
assert len(out["minimum_joint_residual_sets"])>=1

cr=candidate["result"]
assert cr["target_count"]==out["target_count"]
assert cr["verified_scheduling_rule_count"]==out["verified_rule_count"]
assert cr["atom_count"]==out["atom_count"]
assert cr["primitive_residual_fact_count"]==len(out["primitive_residual_facts"])
assert cr["minimum_joint_residual_size"]==out["minimum_joint_residual_size"]
assert cr["exact_further_joint_compression_found"] is False

shared={tuple(sorted(x["targets"])):x["minimum_residual_sets"] for x in out["shared_residual_groups"]}
expected_groups={
    tuple(sorted(["ARTIFACT_AA_BRIEFCASE_GE_1822","PROWORK_AA_BRIEFCASE_GE_1822"])),
    tuple(sorted(["AUTOMATIONBENCH_GE_40","LIVEBENCH_IF_GE_65_7","TB_SCIENCE_GE_58_7"])),
    tuple(sorted(["CODING_CURSORBENCH_GE_57_8","CODING_FRONTIERCODE_GE_54_4"])),
}
assert set(shared)==expected_groups, shared

parents={c["id"]:c for c in frontier["certificates"]}
preds={p["id"]:p for p in registry["predicates"]}

# Flatten deleted-private reconciliation to target-specific obligations.
recon_map={}
for row in recon["mappings"]:
    if "predicate_id" in row:
        recon_map[row["predicate_id"]]=row["replacement_obligation"]
    else:
        ids=row["predicate_ids"]; obs=row["replacement_obligations"]
        assert len(ids)==len(obs)
        for pid,ob in zip(ids,obs):
            recon_map[pid]=ob

expected_semantic_markers={
    "CODING_FRONTIERCODE_GE_54_4":("FRONTIERCODE","FROZEN_FRONTIERCODE"),
    "CODING_CURSORBENCH_GE_57_8":("CURSORBENCH","FROZEN_CURSORBENCH"),
    "PROWORK_AA_BRIEFCASE_GE_1822":("PROWORK_AA_BRIEFCASE","FROZEN_PROWORK_AA_BRIEFCASE"),
    "ARTIFACT_AA_BRIEFCASE_GE_1822":("ARTIFACT_AA_BRIEFCASE","FROZEN_ARTIFACT_AA_BRIEFCASE"),
}

for parent in refine["parents"]:
    p=parents[parent["certificate_id"]]
    child_targets=[]
    child_requires=[]
    for child in parent["children"]:
        assert len(child["target_predicates"])==1
        assert len(child["requires"])==1
        target=child["target_predicates"][0]
        req=child["requires"][0]
        assert target in preds
        assert preds[target]["kind"]=="PUBLIC_FIXED_BAR"
        assert target in recon_map
        req_marker, recon_marker=expected_semantic_markers[target]
        assert req_marker in req, (target,req)
        assert recon_marker in recon_map[target], (target,recon_map[target])
        child_targets.append(target)
        child_requires.append(req)
    assert sorted(child_targets)==sorted(p["target_predicates"])
    assert sorted(child_requires)==sorted(p["requires"])
    assert len(set(child_targets))==len(child_targets)
    assert len(set(child_requires))==len(child_requires)

assert refine["expected_effect"]["minimum_joint_residual_size_before"]==40
assert refine["expected_effect"]["minimum_joint_residual_size_after"]==40
assert refine["capability_credit_delta"]==0
assert refine["family_credit_delta"]==0
assert refine["execution_authority"] is False
assert refine["promotion_authority"] is False

print(json.dumps({
    "status":"PASS",
    "global_abductive":{
        "targets":out["target_count"],
        "rules":out["verified_rule_count"],
        "primitive_residuals":len(out["primitive_residual_facts"]),
        "minimum_joint_residual_size":out["minimum_joint_residual_size"],
        "shared_residual_groups":len(out["shared_residual_groups"]),
    },
    "target_refinement":{
        "parent_certificates_verified":len(refine["parents"]),
        "child_certificates_verified":sum(len(x["children"]) for x in refine["parents"]),
        "joint_residual_size_unchanged":True,
    },
    "credit_delta":0,
},indent=2,sort_keys=True))
