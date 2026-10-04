#!/usr/bin/env python3
import json, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
w=json.loads((ROOT/"subject/livebench_local_root1_20261004/root_transport_witness.json").read_text())
assert w["schema"]=="PROJECT_BRAIN_LIVEBENCH_ROOT_STATE_TRANSPORT_WITNESS_V1"
assert w["root_state"]["git_blob_sha"]=="c624ca84adcc3585c9afeafe4d1c6f3ebbedee3a"
assert w["source_projection"]["git_blob_sha"]=="21dc5e07e18ba3e99a97ffef20a098833c684e99"
assert w["source_projection"]["verification_run_id"]==37196472583
assert w["source_projection"]["verification_job_id"]==111419310250
assert w["source_reclassification"]["git_blob_sha"]=="eef18a73b23db53082b934976bcbd05cab9c5684"
assert w["source_reclassification"]["verification_run_id"]==37196376134
assert w["source_reclassification"]["verification_job_id"]==111419008329
e=w["extracted"]; ca=e["current_acceptance"]
assert ca=={"accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False}
assert e["root1_positive_gap_count"]==1 and e["root1_only_count"]==1
assert e["root1_only"]==["LIVEBENCH_IF_GE_65_7"]
assert e["root2_only_count"]==15 and "LIVEBENCH_IF_GE_65_7" not in e["root2_only"]
assert len(e["root2_only"])==15 and len(set(e["root2_only"]))==15
assert e["root3_only_count"]==7 and len(e["root3_only"])==7
assert e["root2_and_root3_count"]==3 and len(e["root2_and_root3"])==3
sets=[set(e["root1_only"]),set(e["root2_only"]),set(e["root3_only"]),set(e["root2_and_root3"])]
for i in range(len(sets)):
  for j in range(i+1,len(sets)):
    assert sets[i].isdisjoint(sets[j])
assert sum(map(len,sets))==e["unresolved_total"]==26
assert e["scheduler_root1_currently_active"] is True
assert e["root2_controller_effective_scheduling_authority"] is False
assert e["root2_threshold_dag_scheduling_authority"] is False
assert w["execution_authority"] is False and w["promotion_authority"] is False and w["fresh_reality_authority"] is False
assert all(v==0 for v in w["accounting"].values())
print("PASS:LIVEBENCH_ROOT_STATE_TRANSPORT_WITNESS_V1")
