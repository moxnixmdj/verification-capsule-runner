from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = (
    ROOT
    / "subject"
    / "terminal_shadow_reality_v1_20261004"
    / "terminal_state_compression_scheduler_v1.py"
)
EXPECTED_GIT_BLOB_SHA = "20068f6ce8966f0c7d981d678b0ebe2ebfe4acf6"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


assert git_blob_sha(SUBJECT) == EXPECTED_GIT_BLOB_SHA

spec = importlib.util.spec_from_file_location("shadow_subject", SUBJECT)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

# Unknown probabilities remain unknown; deterministic and falsified states are exact.
assert m.classify_probability_state() == "UNKNOWN__NO_POINT_ESTIMATE"
assert m.classify_probability_state(
    deterministic_entailment=True
) == "ONE"
assert m.classify_probability_state(
    falsified_until_wake=True
) == "ZERO_UNTIL_MATERIAL_WAKE"
assert m.classify_probability_state(
    calibrated_bernoulli_history=True
) == "CALIBRATED_EXTERNALLY__USE_BOUND_POSTERIOR_RECEIPT"

try:
    m.classify_probability_state(
        deterministic_entailment=True,
        falsified_until_wake=True,
    )
    raise AssertionError("mutually exclusive probability states were accepted")
except ValueError:
    pass

# A decisive probe with no calibrated success probability can still rank > 0
# because deletion/information are guaranteed under all outcomes.
score = m.robust_state_compression_priority(
    guaranteed_progress=0,
    guaranteed_deletion=1,
    guaranteed_information=1,
    critical_path_seconds=2,
)
assert score == 1.0

base = m.robust_state_compression_priority(
    guaranteed_progress=1,
    guaranteed_deletion=1,
    guaranteed_information=1,
    critical_path_seconds=3,
    correlation_penalty=0,
)
penalized = m.robust_state_compression_priority(
    guaranteed_progress=1,
    guaranteed_deletion=1,
    guaranteed_information=1,
    critical_path_seconds=3,
    correlation_penalty=1,
)
assert penalized < base

for bad in (-1,):
    try:
        m.robust_state_compression_priority(
            guaranteed_progress=bad,
            guaranteed_deletion=0,
            guaranteed_information=0,
            critical_path_seconds=1,
        )
        raise AssertionError("negative priority term accepted")
    except ValueError:
        pass

receipt = {
    "generic_isolation_kernel_pass": True,
    "benchmark_thin_adapter_pass": True,
    "candidate_frozen": True,
    "executor_independent": True,
    "executed_hashes_equal_precommit": True,
    "outputs_bound_to_precommit": True,
    "outputs_escrowed": True,
    "outputs_hidden_from_candidate": True,
    "unrelated_work_cannot_mutate_candidate": True,
    "zero_incremental_spend_guard": True,
    "route_result_not_used_for_acceptance_before_fixed_point": True,
    "acceptance_credit_before_fixed_point": False,
    "promotion_before_fixed_point": False,
    "candidate_can_read_shadow_outputs": False,
}

# Generic isolation and a thin adapter are insufficient by themselves.
out = m.verify_shadow_reality_lease(receipt)
assert out["shadow_collection_ready"] is False
assert "explicit_shadow_reality_authority" in out["missing"]
assert out["fresh_reality_authority_granted_by_this_module"] is False
assert out["acceptance_credit_authorized"] is False
assert out["promotion_authority"] is False

# Authority alone is also insufficient if any isolation premise fails.
receipt["explicit_shadow_reality_authority"] = True
bad = dict(receipt)
bad["outputs_hidden_from_candidate"] = False
out = m.verify_shadow_reality_lease(bad)
assert out["shadow_collection_ready"] is False
assert "outputs_hidden_from_candidate" in out["missing"]

bad = dict(receipt)
bad["candidate_can_read_shadow_outputs"] = True
out = m.verify_shadow_reality_lease(bad)
assert out["shadow_collection_ready"] is False
assert "candidate_can_read_shadow_outputs_must_be_false" in out["missing"]

bad = dict(receipt)
bad["acceptance_credit_before_fixed_point"] = True
out = m.verify_shadow_reality_lease(bad)
assert out["shadow_collection_ready"] is False
assert "acceptance_credit_before_fixed_point_must_be_false" in out["missing"]

# Only the complete externally-authorized lease can become collection-ready,
# while still granting zero acceptance/promotion authority itself.
out = m.verify_shadow_reality_lease(receipt)
assert out["shadow_collection_ready"] is True
assert out["missing"] == []
assert out["fresh_reality_authority_granted_by_this_module"] is False
assert out["acceptance_credit_authorized"] is False
assert out["promotion_authority"] is False

# Overlap has the expected critical-path algebra but does not assert that
# prerequisites for overlap exist.
bound = m.makespan_bound(120, 80)
assert bound == {
    "serial_seconds": 200,
    "overlapped_lower_bound_seconds": 120,
    "maximum_structural_seconds_saved": 80,
}
bound = m.makespan_bound(80, 120)
assert bound["overlapped_lower_bound_seconds"] == 120
assert bound["maximum_structural_seconds_saved"] == 80

print("PASS: terminal shadow-reality scheduler is fail-closed and blob-pinned")
