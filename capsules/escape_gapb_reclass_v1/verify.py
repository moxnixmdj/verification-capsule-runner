from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "reclassification.json":"c793b7f57b13a936646a2825cd67f26c28bf3744",
 "gdp_route.json":"c38ca6ee010a63d6dc218aa2c9d85831e39441ed",
 "gdp_info.json":"7bf8b2ffc8186e14380da080e5a9832a2fd9a2a8",
 "chart_activation.json":"d5b46fc2f784a206cda9bb7c6f1ee951300eccc0",
 "chart_preflight.json":"ea260cd10e29379fc148ec6f281e1006bf5bdbfa",
 "tb_reclass.json":"2639f4e58ef71502707ab6b2bb37efb592b1a234",
}

def blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(name):
    raw=(ROOT/"fixtures"/name).read_bytes()
    assert blob(raw)==EXPECTED[name], (name,blob(raw),EXPECTED[name])
    return json.loads(raw)

r=load("reclassification.json")
g=load("gdp_route.json")
gi=load("gdp_info.json")
ca=load("chart_activation.json")
cp=load("chart_preflight.json")
tb=load("tb_reclass.json")

cut=r["corrected_scheduler_cut"]
assert cut["active_gap_b_count"]==0
assert cut["active_gap_b_rows"]==[]
assert cut["effective_gap_a_active_count"]==12
assert cut["parked_unresolved_rows"]==["TB_SCIENCE_GE_58_7"]
assert r["accounting"]["row_credit_delta"]==0

assert g["measured_effect"]["v2_compilable_first_residuals"]==92
assert g["measured_effect"]["remaining_unresolved_first_residuals"]==128
assert "ROUTE_AVAILABILITY_NOT_CRITERION_SATISFACTION" in g["theorem_boundary"]["statement"]
assert any("WHEN_A_GDPVAL_CANDIDATE_OR_SCOPE_COMPLETE_CONSTRUCTIVE_PROOF_IS_AVAILABLE" in x for x in g["scheduler_effect"])
assert "PUBLIC_BOUND_FACTS_INSUFFICIENT_FOR_TARGET_RELATION" in gi["status"]
assert gi["minimum_separator_cut"]["required_form"].startswith("ONE_AUTHENTIC_FACT_OR_STRONGER_CERTIFICATE")

obs=cp["observed"]
for k in ["model_hash_match","projector_hash_match","llama_mtmd_cli_build_pass",
          "model_and_projector_loaded_without_oom","synthetic_multimodal_inference_exit_zero",
          "synthetic_answer_nonempty","synthetic_answer_identified_red_and_blue"]:
    assert obs[k] is True, k
assert obs["terminal_cases_consumed"]==0
assert obs["incremental_spend_usd"]==0
assert set(cp["still_open"])=={
 "NONTERMINAL_SCOPE_RELEVANT_CHART_REASONING_QUALIFICATION",
 "PROJECT_SPECIFIC_GEMINI_3_5_FLASH_JUDGE_CAPACITY_RECEIPT",
 "THIN_OFFICIAL_CHARTOGRAPHY_ADAPTER_END_TO_END_BINDING",
 "CHARTOGRAPHY_THRESHOLD_CERTIFICATE_GE_89",
}
preserve=set(ca["scheduler_delta"]["preserve"])
assert "NONTERMINAL_SCOPE_RELEVANT_CHART_IMAGE_REASONING_QUALIFICATION" in preserve
assert "CHARTOGRAPHY_THRESHOLD_CERTIFICATE_GE_89" in preserve

assert tb["current_truth"]["current_executable_internal_action"] is False
assert tb["scheduling_effect"]["remove_from_active_gap_b_internal_route_count"] is True

rows={x["obligation_id"]:x for x in r["row_reclassifications"]}
assert set(rows)=={"PROWORK_GDPVAL_GE_1846","CHARTOGRAPHY_TOOLS_GE_89"}
for row in rows.values():
    assert row["corrected_current_class"]=="GAP_A_ACQUISITION_TOTALITY"
    assert row["row_credit"] is False
    assert "gap_b_falsifier" in row

result={
 "schema":"PUBLIC_INDEPENDENT_ESCAPE_GAPB_RECLASS_VERIFY_V1",
 "pass":True,
 "active_gap_b_count_verified":0,
 "effective_gap_a_active_count_verified":12,
 "parked_unresolved_count_verified":1,
 "row_credit_delta":0,
 "terminal_credit_delta":0,
 "source_git_blobs":EXPECTED,
}
print(json.dumps(result,sort_keys=True))
