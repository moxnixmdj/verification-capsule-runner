from __future__ import annotations
import copy, hashlib, json
from pathlib import Path
from canonical.runtime import unknown_domain_direct_execution_lease_v1 as lease

ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_CANDIDATE_V1.json"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

candidate = json.loads(CANDIDATE.read_text())
assert candidate["schema"] == "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_CANDIDATE_V1"
assert candidate["status"].startswith("CANDIDATE__DETERMINISTIC_NONCE_FREE_ONE_USE_LEASE__TRANSITIVE_DEPENDENCY_CLOSED")

subjects = candidate["subjects"]
expected_files = {
    "runtime_git_blob_sha": "canonical/runtime/unknown_domain_direct_execution_lease_v1.py",
    "tests_git_blob_sha": "canonical/tests/test_unknown_domain_direct_execution_lease_v1.py",
    "activation_git_blob_sha": "canonical/governance/UNKNOWN_DOMAIN_DIRECT_PREDICATE_LOCAL_ACTIVATION_V1.json",
    "qualification_receipt_git_blob_sha": "canonical/verification/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
    "production_precommit_git_blob_sha": "canonical/governance/UNKNOWN_DOMAIN_DIRECT_PRODUCTION_PRECOMMIT_V1.json",
    "generator_v1_git_blob_sha": "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py",
}
for key, rel in expected_files.items():
    got = git_blob_sha(ROOT / rel)
    assert got == subjects[key], (key, got, subjects[key])

payload = lease.canonical_lease_payload()
assert payload["exact_execution_subject"]["generator_v1"] == subjects["generator_v1_git_blob_sha"]
assert payload["activation_git_blob_sha"] == subjects["activation_git_blob_sha"]
assert payload["qualification_receipt_git_blob_sha"] == subjects["qualification_receipt_git_blob_sha"]
assert payload["production_precommit_git_blob_sha"] == subjects["production_precommit_git_blob_sha"]
assert payload["claim_repository"] == "moxnixmdj/verification-capsule-runner"
assert payload["claim_namespace"] == "refs/heads/unknown-domain-direct-claims/"
assert payload["production_budget"]["production_populations_allowed"] == 1
assert payload["production_budget"]["production_cases_allowed"] == 27
assert payload["resource_boundary"]["persistent_learned_bytes"] == 0
assert payload["global_fresh_reality"] is False

serialized = json.dumps(payload, sort_keys=True).lower()
for forbidden in ("nonce", "timestamp", "run_label", "run-label"):
    assert forbidden not in serialized, forbidden

base = lease.lease_digest_sha256(payload)
seen = {base}

# Every load-bearing subject must change identity if mutated.
for key in sorted(payload["exact_execution_subject"]):
    alt = copy.deepcopy(payload)
    alt["exact_execution_subject"][key] = "0" * 40
    d = lease.lease_digest_sha256(alt)
    assert d != base, key
    seen.add(d)

# Every outer execution-bound field must also change identity.
mutations = [
    ("activation_git_blob_sha", "0" * 40),
    ("qualification_receipt_git_blob_sha", "0" * 40),
    ("production_precommit_git_blob_sha", "0" * 40),
    ("claim_repository", "example/other"),
    ("claim_namespace", "refs/heads/other/"),
    ("global_fresh_reality", True),
]
for key, value in mutations:
    alt = copy.deepcopy(payload)
    alt[key] = value
    d = lease.lease_digest_sha256(alt)
    assert d != base, key
    seen.add(d)

alt = copy.deepcopy(payload)
alt["production_budget"]["production_cases_allowed"] = 28
assert lease.lease_digest_sha256(alt) != base

alt = copy.deepcopy(payload)
alt["resource_boundary"]["persistent_learned_bytes"] = 1
assert lease.lease_digest_sha256(alt) != base

# Point-of-use firewall must reject the newly bound transitive dependency if altered.
state = {
    "target_predicate": lease.TARGET,
    "authorized_leaves": list(lease.AUTHORIZED_LEAVES),
    "activation_git_blob_sha": lease.ACTIVATION_BLOB,
    "qualification_receipt_git_blob_sha": lease.QUALIFICATION_RECEIPT_BLOB,
    "production_precommit_git_blob_sha": lease.PRODUCTION_PRECOMMIT_BLOB,
    "exact_execution_subject": dict(lease.EXACT_SUBJECTS),
    "qualification_independent_pass": True,
    "activation_independent_pass": True,
    "exact_subject_blobs_rechecked": True,
    "production_cases_consumed": 0,
    "production_populations_generated": 0,
    "persistent_learned_bytes": 0,
    "external_frontier_model_calls": 0,
    "external_learned_capability_calls": 0,
    "incremental_spend_usd": 0,
    "production_beacon_generated": False,
    "candidate_mutated_after_qualification": False,
    "global_fresh_reality": False,
    "execution_started": False,
}
ready = lease.verify_point_of_use_state(state)
assert ready["ready_for_atomic_claim_only"] is True, ready
assert ready["case_generation_authority"] is False
assert ready["execution_authority"] is False
assert ready["claim_ref"] == lease.expected_claim_ref()

bad = copy.deepcopy(state)
bad["exact_execution_subject"]["generator_v1"] = "0" * 40
failed = lease.verify_point_of_use_state(bad)
assert failed["ready_for_atomic_claim_only"] is False
assert "EXACT_EXECUTION_SUBJECT_MISMATCH" in failed["reasons"]

print(json.dumps({
    "status": "INDEPENDENT_TRANSITIVE_EXECUTION_LEASE_PASS",
    "lease_digest_sha256": base,
    "claim_ref": lease.expected_claim_ref(),
    "exact_subject_count": len(payload["exact_execution_subject"]),
    "mutation_identities_checked": len(seen),
    "generator_v1_transitively_bound": True,
    "production_cases_generated": 0,
    "acceptance_credit": 0,
    "global_fresh_reality": False,
}, sort_keys=True))
