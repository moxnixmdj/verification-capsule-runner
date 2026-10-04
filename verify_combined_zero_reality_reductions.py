#!/usr/bin/env python3
import json,pathlib,subprocess
B=pathlib.Path("subject/combined_zero_reality_reductions_20261004_sol")
F={"root":B/"ROOT_STATE.json","ra":B/"RELATIVE_ACTIVATION.json","rv":B/"RELATIVE_VERIFICATION.json","sa":B/"SYNTHESIS_ACTIVATION.json","sv":B/"SYNTHESIS_VERIFICATION.json"}
E={"root":"9ac3c636b2ed76c7f4b1c7cfd8e2762bc7230d0c","ra":"5edaf436becf45c8d8f3477ac7a53a1e8ac3a63a","rv":"b6daf8b1892a8dc11020b6c5a4102b1fed256240","sa":"300fb663e6b598b389961ddf663d88abcd206545","sv":"e13360b7aba2756f0eb97cac977515c07f3bcbdc"}
for k,p in F.items():
 g=subprocess.check_output(["git","rev-parse",f"HEAD:{p.as_posix()}"],text=True).strip(); assert g==E[k],(k,g,E[k])
o={k:json.loads(p.read_text()) for k,p in F.items()}; r=o["root"]
assert r["current_acceptance"]=={"accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False}
q=r["current_residual_root_partition"]; assert (q["root1_positive_gap_count"],q["root2_only_count"],q["root3_only_count"],q["root2_and_root3_count"])==(0,16,7,3)
ctl=r["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert ctl["current_frontier_path"].endswith("V11.json") and ctl["effective_scheduling_authority"] is True and ctl["fresh_reality_authority"] is False
assert r["root3_current_execution_state"]["currently_runnable_event_count"]==0 and r["root3_current_execution_state"]["fresh_reality_authority"] is False
sp=r["scheduler_policy"]
rel=sp["relative_elo_absolute_proof_nontransport"]; syn=sp["synthesis_dimension_scorers_and_strict_reducer"]
assert rel["activation_git_blob_sha"]==E["ra"] and rel["verification_git_blob_sha"]==E["rv"] and rel["affected_predicate_count"]==3
assert syn["activation_git_blob_sha"]==E["sa"] and syn["verification_git_blob_sha"]==E["sv"] and len(syn["deleted_residuals"])==2
assert o["rv"]["independent_runner"]["conclusion"]=="success"; assert o["sv"]["independent_runner"]["conclusion"]=="success"
assert "MATCHED_EMPIRICAL_COMPARISON" in o["ra"]["scheduler_effect"]["preserve"]
assert o["sa"]["effects"]["sufficient_route"]=="STRICT_PAIRED_POINTWISE_DOMINANCE_V1"
assert o["sa"]["effects"]["failure_semantics"]=="FAILURE_OF_STRICT_ROUTE_DOES_NOT_PROVE_INFERIORITY"
for z in (rel,syn):
 assert z["execution_authority"] is False and z["promotion_authority"] is False and z["fresh_reality_authority"] is False
assert r["accounting"]=={"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,"new_reality_units_consumed":0,"incremental_spend_usd":0}
assert sp["structural_breakthrough_overlay"]["status"].startswith("ACTIVE__")
print("PASS combined current-main projection; terminal truth unchanged; two verified zero-reality reductions active; structural overlay preserved")
