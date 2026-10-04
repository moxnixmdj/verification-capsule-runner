from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject" / "typed_minimum_certificate_basis_20261004_sol" / "terminal_typed_minimum_certificate_basis_v1.py"
EXPECTED_BLOB = "b42c81e04109e1ff081517672b397390bb3749e0"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

assert git_blob_sha(SUB) == EXPECTED_BLOB

spec = importlib.util.spec_from_file_location("typed_basis_subject", SUB)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

assert m.current_counts_are_exact() is True
assert m.ROOT2_ONLY.isdisjoint(m.ROOT3_ONLY)
assert m.ROOT2_ONLY.isdisjoint(m.ROOT2_AND_ROOT3)
assert m.ROOT3_ONLY.isdisjoint(m.ROOT2_AND_ROOT3)
assert len(m.UNRESOLVED) == 26

basis = m.compile_basis()
assert basis["predicate_count"] == 26
assert basis["root2_only_count"] == 16
assert basis["root3_only_count"] == 7
assert basis["root2_and_root3_count"] == 3
assert basis["typed_obligation_count"] == 29
assert basis["execution_authority"] is False
assert basis["promotion_authority"] is False
assert basis["fresh_reality_authority"] is False
assert basis["acceptance_credit_authorized"] is False

obs = basis["obligations"]
assert len({x["obligation_id"] for x in obs}) == 29
assert sum(x["dimension"] == m.COMPARATOR_STRENGTH for x in obs) == 19
assert sum(x["dimension"] == m.SCOPE_COMPLETENESS for x in obs) == 10
assert all(x["state"] == "OPEN" and x["credit"] == 0 for x in obs)

assert m.required_dimensions("LIVEBENCH_IF_GE_65_7") == (m.COMPARATOR_STRENGTH,)
assert m.required_dimensions("FINANCE_UNCOVERED_SCOPE_AUDIT") == (m.SCOPE_COMPLETENESS,)
assert m.required_dimensions("AGENCY_MATCHED_SUCCESS_NONINFERIOR") == (
    m.COMPARATOR_STRENGTH, m.SCOPE_COMPLETENESS
)

ok, reason = m.route_admissible("PROWORK_GDPVAL_GE_1846", "FORMAL_ENTAILMENT")
assert ok is False
assert reason == "PURE_ABSOLUTE_ROUTE_CANNOT_TRANSPORT_TO_FIXED_RELATIVE_ELO"

ok, _ = m.route_admissible(
    "PROWORK_GDPVAL_GE_1846",
    "FORMAL_ENTAILMENT",
    explicit_relative_score_bridge=True,
)
assert ok is True

ok, reason = m.route_admissible(
    "LIVEBENCH_IF_GE_65_7",
    "MATCHED_EMPIRICAL_COMPARISON",
)
assert ok is False
assert reason == "FRESH_REALITY_CURRENTLY_NOT_AUTHORIZED"

base = {
    "target_contract_sha256": "a" * 64,
    "semantic_implication_proved": True,
    "metric_threshold_implication_proved": True,
    "scope_relation": "SUPERSET",
    "scope_completeness_proved": True,
    "independent_verification_pass": True,
    "source_content_addressed": True,
    "route_kind": "EXISTING_CONTENT_ADDRESSED_COMPARATOR_EVIDENCE",
}

c = dict(base)
c.update({
    "target_predicate": "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "proved_dimensions": [m.COMPARATOR_STRENGTH, m.SCOPE_COMPLETENESS],
})
assert m.check_typed_certificate(c)["typed_certificate_mechanically_complete"] is True

c2 = dict(base)
c2.update({
    "target_predicate": "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "proved_dimensions": [m.COMPARATOR_STRENGTH],
})
v2 = m.check_typed_certificate(c2)
assert v2["typed_certificate_mechanically_complete"] is False
assert "MISSING_REQUIRED_DIMENSION:SCOPE_COMPLETENESS" in v2["reasons"]

print(json.dumps({
    "status": "PASS",
    "subject_git_blob_sha": EXPECTED_BLOB,
    "predicates": 26,
    "typed_obligations": 29,
    "comparator_strength_obligations": 19,
    "scope_completeness_obligations": 10,
    "execution_authority": False,
    "promotion_authority": False,
    "fresh_reality_authority": False,
    "acceptance_credit_authorized": False,
}, sort_keys=True))
