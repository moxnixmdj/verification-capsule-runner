#!/usr/bin/env python3
import json,pathlib,subprocess
B=pathlib.Path("subject/synthesis_current_root_projection_20261004_sol")
F={"root":B/"ROOT_STATE.json","act":B/"ACTIVATION.json","ver":B/"VERIFICATION.json"}
E={"root":"10ce2c7e755ee784d832a2ff273ac52b5fd35faa","act":"300fb663e6b598b389961ddf663d88abcd206545","ver":"e13360b7aba2756f0eb97cac977515c07f3bcbdc"}
for k,p in F.items():
 g=subprocess.check_output(["git","rev-parse",f"HEAD:{p.as_posix()}"],text=True).strip()
 assert g==E[k],(k,g,E[k])
o={k:json.loads(p.read_text()) for k,p in F.items()}; r=o["root"]; a=o["act"]; v=o["ver"]
assert r["current_acceptance"]=={"accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False}
q=r["current_residual_root_partition"]; assert (q["root1_positive_gap_count"],q["root2_only_count"],q["root3_only_count"],q["root2_and_root3_count"])==(0,16,7,3)
ctl=r["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]; assert ctl["current_frontier_path"].endswith("V11.json") and ctl["effective_scheduling_authority"] is True and ctl["fresh_reality_authority"] is False
assert r["root3_current_execution_state"]["currently_runnable_event_count"]==0
p=r["scheduler_policy"]["synthesis_dimension_scorers_and_strict_reducer"]
assert p["activation_git_blob_sha"]==E["act"] and p["verification_git_blob_sha"]==E["ver"]
assert p["deleted_residuals"]==["FIVE_CASE_SPECIFIC_QUALITY_DIMENSION_SCORER_BINDINGS_UNSPECIFIED","PORTFOLIO_LEVEL_CONSERVATIVE_MATCHED_NONINFERIORITY_REDUCER_UNSPECIFIED"]
assert len(p["remaining"])==4
assert v["independent_runner"]["conclusion"]=="success" and v["independent_runner"]["workflow_run_id"]==37178304916
assert a["effects"]["sufficient_route"]=="STRICT_PAIRED_POINTWISE_DOMINANCE_V1"
assert a["effects"]["failure_semantics"]=="FAILURE_OF_STRICT_ROUTE_DOES_NOT_PROVE_INFERIORITY"
assert a["authority"]=={"scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}
assert r["accounting"]=={"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,"new_reality_units_consumed":0,"incremental_spend_usd":0}
print("PASS synthesis current-root projection exact; two pre-exposure residuals deleted; terminal truth unchanged")
