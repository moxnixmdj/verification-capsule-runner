#!/usr/bin/env python3
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

P={
 "candidate":ROOT/"canonical/governance/ROOT2_PROOF_HYPERGRAPH_CURRENT_REBIND_V6.json",
 "inventory":ROOT/"canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json",
 "vector":ROOT/"canonical/governance/ROOT2_FROZEN_COMPARATOR_VECTOR_V1.json",
 "cut":ROOT/"canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json",
 "adapter_activation":ROOT/"canonical/governance/CHARTOGRAPHY_BRAIN_INSPECT_ADAPTER_ACTIVATION_V1.json",
 "adapter_verification":ROOT/"canonical/verification/CHARTOGRAPHY_BRAIN_INSPECT_ADAPTER_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
}
EXPECTED_BLOBS={
 "candidate":"0f7f1cb62fcd6b340de59e824443372391f4e935",
 "inventory":"1938a8715387d22be8f8825a5779951e27993f11",
 "vector":"77357de9d84113cba4e5e6ce2a7cabffe2e8e7f0",
 "cut":"ca921a834b3ad59c24b793ae94bf732f9b1957eb",
 "adapter_activation":"5e756d2e2e564bc9a7c15838876c2dec1400a19f",
 "adapter_verification":"841fc40bd2f54b451e01d32afd9a79a32aaafa0b",
}

def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

actual={k:blob(v) for k,v in P.items()}
assert actual==EXPECTED_BLOBS,(actual,EXPECTED_BLOBS)
o={k:json.loads(v.read_text()) for k,v in P.items()}
c=o["candidate"]; inv=o["inventory"]; vec=o["vector"]; cut=o["cut"]
act=o["adapter_activation"]; ver=o["adapter_verification"]

assert c["current_inputs"]["route_inventory_git_blob_sha"]==EXPECTED_BLOBS["inventory"]
assert c["current_inputs"]["comparator_vector_git_blob_sha"]==EXPECTED_BLOBS["vector"]
assert c["current_inputs"]["zero_reality_cut_git_blob_sha"]==EXPECTED_BLOBS["cut"]
assert vec["authority"]["route_inventory_git_blob_sha"]==EXPECTED_BLOBS["inventory"]

assert act["status"].startswith("ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS__INSPECT_ADAPTER_DISCHARGED")
assert ver["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__INSPECT_AI_0_3_276__11_OF_11")
assert ver["independent_runner"]["workflow_run_id"]==37165446413
assert ver["independent_runner"]["workflow_job_id"]==111327285044

routes=inv["routes"]
surfaces=vec["surfaces"]
assert len(routes)==14,len(routes)
assert len(surfaces)==14,len(surfaces)
assert sum(len(x["predicate_ids"]) for x in routes)==15
assert sum(len(x["predicates"]) for x in surfaces)==15

inv_norm={x["surface"]:(tuple(x["predicate_ids"]),x["target"]) for x in routes}
vec_norm={x["surface"]:(tuple(x["predicates"]),x["target"]) for x in surfaces}
assert inv_norm==vec_norm,(inv_norm,vec_norm)

expected={
 "Terminal-Bench 4.0":(("CODING_TB4_GE_66_4",),">=66.4%"),
 "FrontierCode v1.1 Main":(("CODING_FRONTIERCODE_GE_54_4",),">=54.4%"),
 "CursorBench 4.0":(("CODING_CURSORBENCH_GE_57_8",),">=57.8%"),
 "GDPval-AA v2.1":(("PROWORK_GDPVAL_GE_1846",),">=1846 Elo"),
 "AA-Briefcase v1.1":(("PROWORK_AA_BRIEFCASE_GE_1822","ARTIFACT_AA_BRIEFCASE_GE_1822"),">=1822 Elo"),
 "AutomationBench":(("AUTOMATIONBENCH_GE_40",),">=40%"),
 "Humanity's Last Exam with tools":(("HLE_TOOLS_GE_67_7",),">=67.7%"),
 "Terminal-Bench-Science 0.1":(("TB_SCIENCE_GE_58_7",),">=58.7%"),
 "Chartography with tools":(("CHARTOGRAPHY_TOOLS_GE_89",),">=89%"),
 "OSWorld 2.1 partial":(("OSWORLD_2_1_PARTIAL_GE_81_8",),">=81.8%"),
 "Finance & Accounting Index":(("FINANCE_ACCOUNTING_INDEX_GE_61",),">=61 represented scope"),
 "Finance Agent v2":(("FINANCE_AGENT_V2_GE_58_59",),">=58.59%"),
 "LiveBench Instruction Following":(("LIVEBENCH_IF_GE_65_7",),">=65.7%"),
 "Vals MysteryMechanism":(("MYSTERYMECHANISM_GE_49_55",),">=49.55%"),
}
assert inv_norm==expected,(inv_norm,expected)

chart=next(x for x in routes if x["surface"]=="Chartography with tools")
assert "BRAIN_INSPECT_ADAPTER_INDEPENDENTLY_VERIFIED" in chart["state"]
assert "INTERNAL_MULTIMODAL_BACKEND_BINDING" in chart["state"]
assert chart["brain_inspect_adapter"]["activation_git_blob_sha"]==EXPECTED_BLOBS["adapter_activation"]
assert chart["brain_inspect_adapter"]["verification_git_blob_sha"]==EXPECTED_BLOBS["adapter_verification"]
remaining=chart["zero_spend_guard"]["remaining"]
assert "BRAIN_EVALUATION_ADAPTER" not in remaining
assert "SEPARATELY_VERIFIED_INTERNAL_MULTIMODAL_BACKEND_BINDING" in remaining

osw=next(x for x in routes if x["surface"]=="OSWorld 2.1 partial")\nassert "PARTIAL_SCORING_SEMANTICS_RECONCILED" in osw["state"]\nassert osw["partial_metric_semantics"]["removed"]=="PARTIAL_MEANS_AN_UNIDENTIFIED_TASK_SUBSET"\n\nwork=next(x for x in cut["active_zero_reality_work"] if x["surface"]=="Chartography with tools")
assert "BRAIN_INSPECT_ADAPTER_VERIFIED" in work["work"]
assert "BIND_SEPARATELY_VERIFIED_INTERNAL_MULTIMODAL_BACKEND" in work["work"]
assert any(
 x["target"]=="CHARTOGRAPHY_TOOLS_GE_89"
 and x["delta"]=="BRAIN_INSPECT_ADAPTER_INDEPENDENT_PUBLIC_RUNNER_PASS"
 for x in cut["completed_zero_reality_deltas"]
)

for doc in (c,inv,vec,cut,act,ver):
    assert doc.get("acceptance_credit_delta",0)==0
    assert doc.get("family_credit_delta",0)==0
    assert doc.get("capability_credit_delta",0)==0
    assert doc.get("ownership_credit_delta",0)==0
    assert doc.get("terminal_cases_consumed",0)==0
    assert doc.get("incremental_spend_usd",0)==0

assert c["invariants"]["fixed_bar_predicates"]==15
assert c["invariants"]["unique_fixed_bar_surfaces"]==14
assert c["invariants"]["total_root2_involved_predicates"]==19
assert c["invariants"]["comparator_targets_changed"] is False
assert c["invariants"]["predicate_set_changed"] is False
assert c["invariants"]["surface_set_changed"] is False

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_HYPERGRAPH_CURRENT_REBIND_V6_PUBLIC_RUNNER_RESULT_V1",
 "pass":True,
 "status":"PASS__EXACT_CURRENT_INPUTS__15_PREDICATES__14_SURFACES__19_ROOT2_INVOLVED__TARGETS_UNCHANGED__OSWORLD_V5_PRESERVED__CHARTOGRAPHY_ADAPTER_DISCHARGED_BACKEND_OPEN__ZERO_CASES__ZERO_CREDIT"
},sort_keys=True))
