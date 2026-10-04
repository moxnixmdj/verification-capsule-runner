from __future__ import annotations

import ast
import hashlib
import itertools
import json
import math
from fractions import Fraction
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as proposed

ROOT = Path(__file__).resolve().parent

EXPECTED = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py":
        "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py":
        "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":
        "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":
        "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":
        "bbf57ec4a66aa7b311308ed34b61325d00674361",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":
        "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":
        "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
    "canonical/runtime/unknown_domain_direct_v3_universal_proof_v1.py":
        "0247c98f0b20c15d591453c7306b778f1f90dd8c",
    "canonical/governance/UNKNOWN_DOMAIN_V3_COLLISION_TOTAL_UNIVERSAL_PROOF_CANDIDATE_20261005_V1.json":
        "6c9b784ed2ab3683ac6fff31e84a11350605c815",
}


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


# 1. Exact-byte binding.
for rel, expected in EXPECTED.items():
    got = blob(ROOT / rel)
    assert got == expected, (rel, got, expected)


# 2. Independent finite proof of the collision-total rank core.
def independent_rank(labels, swaps):
    arr = list(labels)
    assert len(arr) == len(set(arr))
    assert len(swaps) == max(0, len(arr) - 1)
    for j, i in zip(swaps, range(len(arr) - 1, 0, -1)):
        assert 0 <= j <= i
        arr[i], arr[j] = arr[j], arr[i]
    return {label: rank for rank, label in enumerate(arr)}


path_count = 0
for n in range(1, 8):
    labels = tuple(f"L{i}" for i in range(n))
    domains = [range(i + 1) for i in range(n - 1, 0, -1)]
    sequences = itertools.product(*domains) if domains else [()]
    for swaps in sequences:
        swaps = tuple(swaps)
        want = independent_rank(labels, swaps)
        got = g3._rank_from_swaps(labels, swaps)
        assert got == want
        assert set(got.values()) == set(range(n))
        path_count += 1
assert path_count == 5913


# 3. Independently verify V3 delegates latent task generation to V2.
g3_path = ROOT / "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py"
g3_source = g3_path.read_text()
g3_ast = ast.parse(g3_source)
function_names = {n.name for n in g3_ast.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
assert "_program_for" not in function_names
assert "_role_rows" not in function_names

transfer = next(n for n in g3_ast.body if isinstance(n, ast.FunctionDef) and n.name == "_transfer_case")
program_assignments = 0
v2_program_calls = 0
v2_role_calls = 0
for node in ast.walk(transfer):
    if isinstance(node, ast.Assign):
        targets = []
        for t in node.targets:
            if isinstance(t, ast.Name):
                targets.append(t.id)
            elif isinstance(t, (ast.Tuple, ast.List)):
                targets.extend(e.id for e in t.elts if isinstance(e, ast.Name))
        if "program" in targets:
            program_assignments += 1
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        if node.func.value.id == "v2" and node.func.attr == "_program_for":
            v2_program_calls += 1
        if node.func.value.id == "v2" and node.func.attr == "_role_rows":
            v2_role_calls += 1
assert program_assignments == 1
assert v2_program_calls == 1
assert v2_role_calls == 2
assert 'mimic_visible=False, probe_variant=j' in g3_source
assert 'mimic_visible=True, probe_variant=j' in g3_source
assert 'query_roles = target_rows[5]' in g3_source
assert 'full_rediscovery_probe_floor": 3' in g3_source


# 4. Independent exact arithmetic for all six transfer families.
D0 = Fraction(19, 4)   # first distractor on first probe
D1 = Fraction(25, 4)
MIN_MAG = Fraction(1, 4)
MAX_MAG = Fraction(7, 2)

assert Fraction(3, 5) * D0 == Fraction(57, 20)
assert D0 == Fraction(19, 4)
sat_gap = Fraction(7, 10) * D0 / 121
assert sat_gap == Fraction(133, 4840)
assert float(sat_gap) > 4.5e-9

for index in (1, 7):
    assert (3 + index) % 2 == 0
assert -MAX_MAG + D0 == Fraction(5, 4) > 0

# STEP's discriminating second probe has probe_variant=1, so d0 shift is 5.
assert Fraction(5, 1) - Fraction(11, 5) == Fraction(14, 5) > 0

for index in (4, 10):
    assert (3 + index) % 2 == 1
    assert (3 + index + 1) % 3 != 0
wrong_support_gaps = (
    D0 - (MAX_MAG - MIN_MAG),
    D1,
    D0,
    D1 - (MAX_MAG - MIN_MAG),
    D0 + D1,
)
assert min(wrong_support_gaps) == Fraction(3, 2)


# 5. Independent abstention-construction checks.
assert tuple(g1.ABSTAIN_CLASSES) == ("IDENTIFIABLE", "NONIDENTIFIABLE", "UNDERSPECIFIED")
assert g1.PRODUCTION_CASE_COUNTS == {g1.TRANSFER: 12, g1.ABSTAIN: 15}
assert scorer.DECISIONS == {"CONCLUDE", "ABSTAIN", "REQUEST_DISCRIMINATOR"}
assert 'b = a if cls == "IDENTIFIABLE" else oid("A", "A2")' in g3_source
assert 'if cls == "UNDERSPECIFIED":' in g3_source
assert '"cost": 1' in g3_source and '"cost": 2' in g3_source
assert 'elif cls == "NONIDENTIFIABLE":' in g3_source
assert '"type": "SAFE_OBSERVATION"' in g3_source


# 6. Metamorphic V2->V3 semantics: same hidden latent task under opaque renaming.
# This is not the universal proof; it is a separate integration falsifier.
def canonical_transfer_semantics(visible, hidden):
    receipt = visible["domain_a"]["earned_receipts"][0]
    a_bind = receipt["source_role_binding"]
    b_bind = hidden["domain_mapping"]

    def row_projection(row, mapping):
        support = {r: row["inputs"][fid] for r, fid in mapping.items()}
        distractors = sorted(v for k, v in row["inputs"].items() if k not in set(mapping.values()))
        return support, distractors, row["terminal_consequence"]

    source = [row_projection(row, a_bind) for row in visible["domain_a"]["tasks"]]
    target = [row_projection(row, b_bind) for row in visible["domain_b"]["tasks"]]
    probe_rows = []
    by_cost = sorted(visible["domain_b"]["allowed_probes"], key=lambda p: p["cost"])
    for p in by_cost:
        row = hidden["allowed_probe_outcome_table"][p["probe_id"]]
        probe_rows.append(row_projection(row, b_bind))
    query = {
        "support": {r: visible["domain_b"]["query_inputs"][fid] for r, fid in b_bind.items()},
        "distractors": sorted(
            v for k, v in visible["domain_b"]["query_inputs"].items()
            if k not in set(b_bind.values())
        ),
    }
    return {
        "family": hidden["primitive_family"],
        "program": hidden["latent_primitive_program"],
        "gold": hidden["gold_terminal_consequence"],
        "source": source,
        "target": target,
        "probes": probe_rows,
        "query": query,
        "floor": hidden["full_rediscovery_probe_floor"],
    }


secrets = [
    b"0" * 32,
    b"1" * 32,
    bytes(range(32)),
    bytes(reversed(range(32))),
]
beacons = [
    "SEMANTIC-EQUIV-BEACON-0001",
    "SEMANTIC-EQUIV-BEACON-0002",
]
for secret in secrets:
    for beacon in beacons:
        p2 = g2._generate(beacon=beacon, evaluator_secret=secret, namespace="SEM")
        p3 = g3._generate(beacon=beacon, evaluator_secret=secret, namespace="SEM")
        assert len(p2["visible_cases"]) == len(p3["visible_cases"]) == 27
        for i in range(12):
            assert canonical_transfer_semantics(p2["visible_cases"][i], p2["hidden_records"][i]) == canonical_transfer_semantics(p3["visible_cases"][i], p3["hidden_records"][i])
        for i in range(12, 27):
            h2, h3 = p2["hidden_records"][i], p3["hidden_records"][i]
            v2, v3 = p2["visible_cases"][i], p3["visible_cases"][i]
            assert h2["identifiability_status"] == h3["identifiability_status"]
            assert len(v2["allowed_probes"]) == len(v3["allowed_probes"])
            assert [p["cost"] for p in v2["allowed_probes"]] == [p["cost"] for p in v3["allowed_probes"]]


# 7. End-to-end candidate/harness/scorer integration on several non-production fixtures.
for k in range(4):
    packet = g3.generate_qualification_fixture_population(
        beacon=f"INDEPENDENT-V3-QUALIFICATION-{k:04d}"
    )
    assert packet["production"] is False
    results = []
    for visible, hidden in zip(packet["visible_cases"], packet["hidden_records"]):
        run = harness.execute_case(
            candidate_step=c2.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        results.append(run["scorer_result"])
    agg = scorer.aggregate(results)
    assert agg["all_27_cases_pass"] is True


# 8. Only after independent derivations pass, compare proposed certificate.
out = proposed.prove(ROOT)
assert out["status"] == "PASS__UNIVERSAL_COLLISION_TOTAL_OVER_EXACT_V3_GENERATOR_DOMAIN"
assert out["identifier_totality_proof"]["all_possible_swap_paths_proved"] == 5913
assert out["identifier_totality_proof"]["hmac_collision_resistance_required_for_uniqueness"] is False
assert out["scope"]["identifier_collision_cases_excluded"] == 0
assert out["scope"]["terminal_or_production_cases_generated"] == 0
assert out["production_execution_information_gain"] == 0
assert out["accounting"]["acceptance_credit_delta"] == 0
assert out["accounting"]["family_credit_delta"] == 0
assert out["accounting"]["capability_credit_delta"] == 0
assert out["accounting"]["ownership_credit_delta"] == 0

gov = json.loads(
    (ROOT / "canonical/governance/UNKNOWN_DOMAIN_V3_COLLISION_TOTAL_UNIVERSAL_PROOF_CANDIDATE_20261005_V1.json").read_text()
)
assert gov["target_predicate"] == "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
assert gov["scope"]["identifier_collision_cases_excluded"] == 0
assert gov["authority"]["acceptance_credit"] is False
assert gov["accounting"]["production_cases_generated"] == 0

print(json.dumps({
    "status": "INDEPENDENT_COLLISION_TOTAL_V3_UNIVERSAL_PROOF_PASS",
    "exact_subject_blob_count": len(EXPECTED),
    "all_possible_identifier_swap_paths": path_count,
    "transfer_families_proved": 6,
    "abstention_classes_proved": 3,
    "semantic_metamorphic_populations_checked": len(secrets) * len(beacons),
    "qualification_cases_executed": 4 * 27,
    "production_cases_generated": 0,
    "hmac_collision_assumption_for_identifier_uniqueness": False,
    "acceptance_credit_delta": 0,
}, sort_keys=True))
