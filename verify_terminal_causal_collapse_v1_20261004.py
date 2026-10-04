from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"terminal_causal_collapse_v1_20261004"
RUNTIME=SUB/"typed_minimum_certificate_basis_v1.py"
GOV=SUB/"TERMINAL_TYPED_MINIMUM_CERTIFICATE_BASIS_V1.json"
ARENA=SUB/"ARENA_COMPARATOR_PUBLIC_EVIDENCE_CORRECTION_20261004_V1.json"

EXPECTED_RUNTIME="c46dbe13b1ba38fed088272db0d8d89e273efdbd"
EXPECTED_GOV="768115e47787a801b972b475675396032c17eeab"
EXPECTED_ARENA="5a2d2b3ac44927bbe7295369b775c46605fe540c"

def git_blob_sha(path: Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

assert git_blob_sha(RUNTIME)==EXPECTED_RUNTIME
assert git_blob_sha(GOV)==EXPECTED_GOV
assert git_blob_sha(ARENA)==EXPECTED_ARENA

spec=importlib.util.spec_from_file_location("typed_basis_subject",RUNTIME)
assert spec and spec.loader
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)

# Exact set-cover behavior: shared certificate wins.
preds=[
 {"predicate_id":"A","admissible_proof_types":["ABSOLUTE"]},
 {"predicate_id":"B","admissible_proof_types":["ABSOLUTE"]},
]
certs=[
 {"certificate_id":"a","proof_type":"ABSOLUTE","closes":["A"],"critical_path_cost":1},
 {"certificate_id":"b","proof_type":"ABSOLUTE","closes":["B"],"critical_path_cost":1},
 {"certificate_id":"shared","proof_type":"ABSOLUTE","closes":["A","B"],"critical_path_cost":1.5},
]
out=m.solve(preds,certs)
assert out["complete_basis_exists"] is True
assert out["selected_certificate_ids"]==["shared"]
assert out["minimum_total_declared_cost"]==1.5

# The load-bearing safety property: absolute proof cannot cross into relative-Elo.
preds=[{"predicate_id":"GDPVAL","admissible_proof_types":[
 "RELATIVE_SCORE_BRIDGE_STRONGER_PROOF",
 "EXISTING_CONTENT_ADDRESSED_COMPARATOR_EVIDENCE",
 "OWNER_RESULT",
 "MATCHED_EMPIRICAL_COMPARISON",
]}]
certs=[
 {"certificate_id":"illegal_absolute","proof_type":"ABSOLUTE","closes":["GDPVAL"],"critical_path_cost":0},
 {"certificate_id":"relative","proof_type":"RELATIVE_SCORE_BRIDGE_STRONGER_PROOF","closes":["GDPVAL"],"critical_path_cost":2},
]
out=m.solve(preds,certs)
assert out["selected_certificate_ids"]==["relative"]
assert any(x["certificate_id"]=="illegal_absolute" and x["reason"]=="PROOF_TYPE_NOT_ADMISSIBLE"
           for x in out["rejected_candidates"])

# No admissible cover fails closed.
out=m.solve(
 [{"predicate_id":"X","admissible_proof_types":["MATCHED"]}],
 [{"certificate_id":"bad","proof_type":"ABSOLUTE","closes":["X"],"critical_path_cost":1}],
)
assert out["complete_basis_exists"] is False
assert out["structurally_uncoverable_predicates"]==["X"]
assert out["acceptance_credit_authorized"] is False
assert out["execution_authority"] is False
assert out["promotion_authority"] is False
assert out["fresh_reality_authority"] is False

gov=json.loads(GOV.read_text())
assert gov["schema"]=="PROJECT_BRAIN_TERMINAL_TYPED_MINIMUM_CERTIFICATE_BASIS_V1"
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False
assert gov["fresh_reality_authority"] is False
assert gov["independent_verification_required"] is True
assert set(gov["relative_elo_binding"]["affected"])=={
 "PROWORK_GDPVAL_GE_1846","PROWORK_AA_BRIEFCASE_GE_1822","ARTIFACT_AA_BRIEFCASE_GE_1822"
}
assert "RELATIVE_SCORE_BRIDGE_STRONGER_PROOF" in gov["relative_elo_binding"]["admissible_route_classes"]
assert gov["existing_isolation_mechanism"]["runtime"]=="canonical/runtime/generic_precommit_isolation_theorem_v1.py"
assert gov["existing_isolation_mechanism"]["shadow_lease_policy"]=="canonical/governance/SHADOW_REALITY_LEASE_POLICY_V1.json"

arena=json.loads(ARENA.read_text())
assert arena["schema"]=="PROJECT_BRAIN_ARENA_COMPARATOR_PUBLIC_EVIDENCE_CORRECTION_20261004_V1"
assert arena["execution_authority"] is False
assert arena["promotion_authority"] is False
assert arena["fresh_reality_authority"] is False
for needed in [
 "GET_V1_MODELS_SEMANTICS",
 "DIRECT_API_MODEL_PARAMETER_ROUTING_SEMANTICS",
 "FALLBACK_DISABLE_OR_CONTROL_SEMANTICS",
 "X_ARENA_RESOLVED_MODEL_HEADER_SEMANTICS",
 "EXACT_OPUS55_AVAILABILITY_IN_THIS_ACCOUNT",
 "ZERO_INCREMENTAL_SPEND_API_ENTITLEMENT",
 "EFFORT_AND_HARNESS_EQUIVALENCE",
]:
    assert needed in arena["not_publicly_verified_in_this_refresh"]

# Independent public-network check: unauthenticated API-doc requests must not
# yield authoritative document content. A WorkOS auth redirect is accepted.
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener=urllib.request.build_opener(NoRedirect())
for url in [
 "https://portal.api.preview.arena.ai/docs/api-reference",
 "https://portal.api.preview.arena.ai/docs/routing",
]:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 verification-capsule"})
    try:
        resp=opener.open(req,timeout=20)
        code=resp.getcode()
        body=resp.read(4096).decode("utf-8","ignore").lower()
        # If it ever becomes public, this candidate must be revisited rather
        # than silently treating old login-gated semantics as current.
        assert code in (301,302,303,307,308), (url,code,body[:200])
    except urllib.error.HTTPError as e:
        assert e.code in (301,302,303,307,308), (url,e.code)
        loc=e.headers.get("Location","")
        assert "workos" in loc.lower() or "authorize" in loc.lower(), loc

print(json.dumps({
 "status":"PASS",
 "runtime_git_blob_sha":EXPECTED_RUNTIME,
 "governance_git_blob_sha":EXPECTED_GOV,
 "arena_correction_git_blob_sha":EXPECTED_ARENA,
 "typed_relative_elo_guard":True,
 "minimum_basis_shared_certificate_test":True,
 "fail_closed_uncoverable_test":True,
 "arena_login_gate_independently_observed":True,
 "acceptance_credit_authorized":False,
 "execution_authority":False,
 "promotion_authority":False,
 "fresh_reality_authority":False,
},sort_keys=True))
