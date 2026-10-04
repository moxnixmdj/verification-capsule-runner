"""Unknown-Domain direct candidate V3: exact role-order recovery.

V3 is additive over V2.  It preserves the zero-learned visible interface and
the two-probe ceiling, but repairs a real ADD2 ambiguity: mathematically
symmetric role permutations can differ by one binary64 ULP because the frozen
scorer compares the scalar consequence exactly.

The repair does not inspect hidden truth.  When several surviving mappings have
the same support, V3 compares the public sign signature of each source role
(from the earned Domain-A source_role_binding) with each candidate Domain-B
feature across the three public target tasks.  The frozen V2 generator preserves
these role signatures across domains while randomizing magnitudes and opaque
labels.  For both ADD2 indices the signatures are distinct, so the latent
r0/r1 order is recovered before exact floating-point evaluation.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_candidate_v1 as v1
from canonical.runtime import unknown_domain_direct_candidate_v2 as v2

TRANSFER = v1.TRANSFER
ABSTAIN = v1.ABSTAIN
CandidateError = v1.UnknownDomainDirectCandidateError
MAPPING_BASIS = v1.MAPPING_BASIS


def _sign(value: Any) -> int:
    x = v1._finite(value, "role_signature_value")
    if x < 0.0:
        return -1
    if x > 0.0:
        return 1
    return 0


def _feature_signature(tasks: Any, feature_id: str) -> tuple[int, ...]:
    if not isinstance(tasks, list) or not tasks:
        raise CandidateError("ROLE_SIGNATURE_TASKS_INVALID")
    out = []
    for row in tasks:
        if not isinstance(row, Mapping) or not isinstance(row.get("inputs"), Mapping):
            raise CandidateError("ROLE_SIGNATURE_TASK_INVALID")
        inputs = row["inputs"]
        if feature_id not in inputs:
            raise CandidateError("ROLE_SIGNATURE_FEATURE_MISSING")
        out.append(_sign(inputs[feature_id]))
    return tuple(out)


def _role_signature_resolve(
    case: Mapping[str, Any],
    receipt: Mapping[str, Any],
    program: Mapping[str, Any],
    mappings: Sequence[Mapping[str, str]],
) -> dict[str, str] | None:
    roles = [str(x) for x in program.get("roles", [])]
    if len(roles) <= 1 or len(mappings) <= 1:
        return None

    binding = receipt.get("source_role_binding")
    source_tasks = case.get("domain_a", {}).get("tasks")
    target_tasks = case.get("domain_b", {}).get("tasks")
    if not isinstance(binding, Mapping):
        raise CandidateError("SOURCE_ROLE_BINDING_INVALID")
    if not isinstance(source_tasks, list) or not isinstance(target_tasks, list):
        raise CandidateError("ROLE_SIGNATURE_TASK_SET_INVALID")

    source_signatures = {}
    for role in roles:
        source_id = str(binding.get(role) or "")
        if not source_id:
            raise CandidateError("SOURCE_ROLE_BINDING_MISSING:" + role)
        source_signatures[role] = _feature_signature(source_tasks, source_id)

    matches = []
    for mapping in mappings:
        if all(
            _feature_signature(target_tasks, str(mapping[role]))
            == source_signatures[role]
            for role in roles
        ):
            matches.append(dict(mapping))

    if len(matches) == 1:
        return matches[0]
    return None


def _transfer(case: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]):
    receipt = v1._receipt(case)
    program = receipt.get("normalized_primitive_program")
    if not isinstance(program, Mapping):
        raise CandidateError("RECEIPT_PROGRAM_INVALID")

    if not transcript:
        return v2._unused_probe(case, transcript)

    observations = v1._public_transfer_observations(case, transcript)
    mappings = v1._candidate_mappings(program, observations)
    supports = {v1._support_signature(m) for m in mappings}

    query = case.get("domain_b", {}).get("query_inputs")
    if not isinstance(query, Mapping):
        raise CandidateError("DOMAIN_B_QUERY_INVALID")
    consequences = {
        round(x[0], 12) for x in v1._query_predictions(program, mappings, query)
    }

    if len(supports) == 1 and len(consequences) == 1:
        mapping = _role_signature_resolve(case, receipt, program, mappings)
        if mapping is None:
            mapping = sorted(
                mappings, key=lambda m: tuple(sorted(m.items()))
            )[0]
        return v2._conclude(case, transcript, receipt, program, mapping)

    if len(transcript) < 2:
        return v2._unused_probe(case, transcript)

    mapping = _role_signature_resolve(case, receipt, program, mappings)
    if mapping is None:
        mapping = v2._scale_resolve(case, transcript, receipt, program, mappings)
    return v2._conclude(case, transcript, receipt, program, mapping)


def step(case_visible: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]):
    leaf = str(case_visible.get("leaf_id") or "")
    if leaf == TRANSFER:
        return _transfer(case_visible, transcript)
    if leaf == ABSTAIN:
        return v1._abstention_step(case_visible)
    raise CandidateError("LEAF_ID_UNKNOWN")
