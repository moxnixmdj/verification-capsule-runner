#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

expect_blob() {
  local path="$1" expected="$2"
  local actual
  actual="$(git hash-object "$path")"
  test "$actual" = "$expected" || {
    echo "BLOB_MISMATCH $path expected=$expected actual=$actual" >&2
    exit 11
  }
}

expect_blob verification/canonical/runtime/certificate_gated_selected_route_router_v1.py 4b99ef1e95e033badfb21ab7af7355122933224a
expect_blob verification/canonical/tests/test_certificate_gated_selected_route_router_v1.py b33717611b21f01f11d570d894aeee7f010231fc
expect_blob verification/canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_ROUTER_RUNTIME_20261007_V1.json 4bb599a386ee23908155069235b4f754c0f1cb90

python3 -m py_compile verification/canonical/runtime/certificate_gated_selected_route_router_v1.py

PYTHONPATH=verification python3 - <<'PY'
import json
from pathlib import Path
from canonical.runtime.certificate_gated_selected_route_router_v1 import (
    AdmissionReceipt, RouterFailClosed, select_certified_route,
)

def receipt(*, admitted=True, context="ctx", cell="c1", route="r1", a="1", q="2", r="3"):
    return AdmissionReceipt(
        context_digest=context,
        cell_id=cell,
        route_id=route,
        route_blob_sha=r * 40,
        adequacy_certificate_blob_sha=q * 40,
        admission_certificate_blob_sha=a * 40,
        admitted=admitted,
    )

x = select_certified_route(
    actual_context_digest="ctx",
    receipts=[
        receipt(admitted=False, a="0"),
        receipt(admitted=True, a="2", route="r2"),
        receipt(admitted=True, a="1", route="r1"),
    ],
)
assert x.admitted is True and x.context_digest == "ctx" and x.route_id == "r1"

try:
    select_certified_route(
        actual_context_digest="ctx",
        receipts=[receipt(context="other"), receipt(admitted=False)],
    )
except RouterFailClosed as exc:
    assert str(exc) == "NO_CERTIFIED_ROUTE_FOR_ACTUAL_CONTEXT"
else:
    raise AssertionError("uncovered context did not fail closed")

rs = [
    receipt(a="b", q="1", r="1", route="later"),
    receipt(a="a", q="f", r="f", route="earlier"),
]
x1 = select_certified_route(actual_context_digest="ctx", receipts=rs)
x2 = select_certified_route(actual_context_digest="ctx", receipts=reversed(rs))
assert x1 == x2 and x1.route_id == "earlier"

bad = AdmissionReceipt("ctx", "c", "r", "not-a-sha", "2" * 40, "3" * 40, True)
try:
    select_certified_route(actual_context_digest="ctx", receipts=[bad])
except RouterFailClosed as exc:
    assert str(exc) == "ROUTE_BLOB_SHA_INVALID"
else:
    raise AssertionError("malformed SHA did not fail closed")

good = receipt()
try:
    select_certified_route(actual_context_digest="ctx", receipts=[good, good])
except RouterFailClosed as exc:
    assert str(exc) == "DUPLICATE_RECEIPT"
else:
    raise AssertionError("duplicate receipt did not fail closed")

try:
    select_certified_route(actual_context_digest="ctx", receipts=[receipt(admitted="false")])
except RouterFailClosed as exc:
    assert str(exc) == "ADMISSION_MUST_BE_LITERAL_BOOL"
else:
    raise AssertionError("non-boolean admission did not fail closed")

gov = json.loads(Path("verification/canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_ROUTER_RUNTIME_20261007_V1.json").read_text())
assert gov["truth_effect"]["terminal"] is False
assert gov["truth_effect"]["abc_closed"] is False
assert gov["truth_effect"]["d_finality_closed"] is False

print(json.dumps({
    "status": "PASS",
    "exact_brain_runtime_blob": "4b99ef1e95e033badfb21ab7af7355122933224a",
    "exact_brain_test_blob": "b33717611b21f01f11d570d894aeee7f010231fc",
    "exact_brain_governance_blob": "4bb599a386ee23908155069235b4f754c0f1cb90",
    "positive_context_bound_selection": True,
    "deterministic_tie_break": True,
    "uncovered_context_fail_closed": True,
    "malformed_and_duplicate_fail_closed": True,
    "non_boolean_admission_fail_closed": True,
    "terminal_claim_preserved_false": True
}, sort_keys=True))
PY
