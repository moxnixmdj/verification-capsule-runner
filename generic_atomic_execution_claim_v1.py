from __future__ import annotations
import hashlib,json,re
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_GENERIC_ATOMIC_EXECUTION_CLAIM_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_GENERIC_ATOMIC_EXECUTION_CLAIM_RECEIPT_V1"
HEX40=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")

def binding_sha256(subject: Mapping[str,Any]) -> str:
    raw=json.dumps(subject,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def expected_claim_ref(subject: Mapping[str,Any]) -> str:
    return "refs/heads/execution-claims/"+binding_sha256(subject)

def verify(subject: Mapping[str,Any], receipt: Mapping[str,Any]) -> dict[str,Any]:
    reasons=[]
    for k in ("benchmark_id","target_predicate","epoch_id","candidate_identity","activation_identity","root_identity"):
        if not isinstance(subject.get(k),str) or not subject[k]:
            reasons.append("SUBJECT_FIELD_INVALID:"+k)
    if receipt.get("schema")!=RECEIPT_SCHEMA:
        reasons.append("RECEIPT_SCHEMA_MISMATCH")
    digest=binding_sha256(subject)
    if receipt.get("subject_binding_sha256")!=digest:
        reasons.append("SUBJECT_BINDING_MISMATCH")
    ref=expected_claim_ref(subject)
    if receipt.get("claim_ref")!=ref:
        reasons.append("CLAIM_REF_MISMATCH")
    if receipt.get("create_http_status")!=201:
        reasons.append("CREATE_NOT_201")
    if receipt.get("reference_created") is not True:
        reasons.append("REFERENCE_NOT_CREATED")
    if receipt.get("response_ref")!=ref:
        reasons.append("RESPONSE_REF_MISMATCH")
    if not isinstance(receipt.get("response_object_sha"),str) or not HEX40.fullmatch(receipt["response_object_sha"]):
        reasons.append("OBJECT_SHA_INVALID")
    if receipt.get("uniqueness_source")!="ATOMIC_GIT_REF_CREATE_RESPONSE":
        reasons.append("UNIQUENESS_SOURCE_INVALID")
    for k in ("case_read_before_claim","execution_started_before_claim","output_exists_before_claim"):
        if receipt.get(k) is not False:
            reasons.append("PRECLAIM_GATE_FAILED:"+k)
    passed=not reasons
    return {
      "schema":SCHEMA,
      "pass":passed,
      "reasons":sorted(set(reasons)),
      "subject_binding_sha256":digest,
      "claim_ref":ref,
      "execution_authority_for_exact_epoch":passed,
      "authority_scope":"EXACT_SUBJECT_EPOCH_ONLY" if passed else "NONE",
      "terminal_cases_consumed_by_verifier":0,
      "global_fresh_reality_authority":False,
      "promotion_authority":False,
      "acceptance_credit_authority":False,
    }
