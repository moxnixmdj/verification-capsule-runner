from __future__ import annotations
import importlib.util,json,pathlib,sys
P=pathlib.Path("generic_atomic_execution_claim_v1.py")
spec=importlib.util.spec_from_file_location("claim",P); assert spec and spec.loader
m=importlib.util.module_from_spec(spec);sys.modules["claim"]=m;spec.loader.exec_module(m)
subject={
 "benchmark_id":"TEST_BENCH",
 "target_predicate":"TEST_PREDICATE",
 "epoch_id":"epoch-001",
 "candidate_identity":"candidate-sha",
 "activation_identity":"activation-sha",
 "root_identity":"root-sha",
}
ref=m.expected_claim_ref(subject)
base={
 "schema":m.RECEIPT_SCHEMA,
 "subject_binding_sha256":m.binding_sha256(subject),
 "claim_ref":ref,
 "create_http_status":201,
 "reference_created":True,
 "response_ref":ref,
 "response_object_sha":"1"*40,
 "uniqueness_source":"ATOMIC_GIT_REF_CREATE_RESPONSE",
 "case_read_before_claim":False,
 "execution_started_before_claim":False,
 "output_exists_before_claim":False,
}
ok=m.verify(subject,base);assert ok["pass"] and ok["execution_authority_for_exact_epoch"]
for mutation in (
 {"create_http_status":422,"reference_created":False},
 {"subject_binding_sha256":"0"*64},
 {"case_read_before_claim":True},
 {"claim_ref":"refs/heads/execution-claims/wrong"},
):
 r=dict(base);r.update(mutation);assert not m.verify(subject,r)["pass"],mutation
print(json.dumps({
 "status":"PASS",
 "generic_subject_binding":True,
 "first_create_201_required":True,
 "duplicate_422_fails_closed":True,
 "preclaim_case_read_rejected":True,
 "exact_epoch_scope":True,
 "terminal_cases_consumed":0,
 "acceptance_credit":0,
},sort_keys=True))
