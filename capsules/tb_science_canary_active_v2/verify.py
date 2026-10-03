import json, pathlib, subprocess
P=pathlib.Path(__file__).with_name("AUTHORITY.json")
d=json.loads(P.read_text())
blob=subprocess.check_output(["git","hash-object",str(P)],text=True).strip()
assert blob=="741d6ca0cc4880e6cd9c76e3046272b1feb756f1", blob
assert d["schema"]=="PROJECT_BRAIN_TB_SCIENCE_ONE_SLOT_CANARY_AUTHORITY_V2"
assert d["execution_authority"] is True and d["promotion_authority"] is False
assert d["authorized_slot"]["slot_id"]=="terminal-bench-science/baseline-free-localization::trial-0"
assert d["execution_semantics"]["slots_authorized"]==1
assert d["execution_semantics"]["retries_per_slot"]==0
assert d["execution_semantics"]["slot_replacement"] is False
assert d["execution_semantics"]["denominator_shrink"] is False
assert d["execution_semantics"]["stop_after_canary"] is True
assert d["execution_semantics"]["auto_revoke_after_slot_finalization"] is True
assert d["current_parity"]["required_successes"]==133
assert d["current_parity"]["fail_lock_failures"]==78
assert d["current_parity"]["finalized_failures_before_canary"]==3
assert d["current_parity"]["remaining_failures_before_fail_lock"]==75
assert d["authority_basis"]["candidate_git_blob_sha"]=="ee36ce99dd39d1964180f2a780d3b9965a690b02"
assert d["authority_basis"]["candidate_verification_git_blob_sha"]=="e00e2e056912b589579cf29420cb557a11ff9e58"
assert d["authority_basis"]["current_target_overlay_git_blob_sha"]=="7c3b2d96cb76f2cb74e591b4257f737b77218959"
assert d["authority_basis"]["current_comparator_verification_git_blob_sha"]=="3bff4c8ec68bba45d0538812101fbbfed7b9b2ec"
assert d["authority_basis"]["local_qwen_harbor_composition_verification_git_blob_sha"]=="daf80d2c8e000ca25e722d4afa403be0ff153c4d"
cons=set(d["permanently_consumed_slots"])
assert len(cons)==3
assert d["authorized_slot"]["slot_id"] not in cons
assert d["exact_route"]["controller_blob"]=="5557efd21f1a433ad16766def3775a79c459784b"
assert d["exact_route"]["planner_blob"]=="879887984e2ca8abacac486d687f519f5d0d78a5"
assert d["exact_route"]["manifest_blob"]=="6dfa880b1f68881531afbba6ca211681801fd19b"
print("TB_SCIENCE_CANARY_ACTIVE_AUTHORITY_V2_PASS", blob)
