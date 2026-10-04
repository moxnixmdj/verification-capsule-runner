"""Total-string hidden generator V4 for the Unknown-Domain direct evaluator.

V3 structurally totalized identifiers, but its accepted beacon gate admitted
arbitrary Python strings while downstream V2/V3 HMAC helpers used strict UTF-8
encoding.  A string containing an unpaired surrogate therefore passed the gate
and then raised UnicodeEncodeError, falsifying the claimed all-accepted-input
totality theorem.

V4 preserves V3 evaluator semantics while canonicalizing every accepted Python
string beacon and evaluator-secret string into a deterministic ASCII/bytes
representation before any legacy HMAC path.  Historical V1-V3 bytes remain
untouched.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as v3

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V4"
BEACON_CANONICALIZATION = "UTF8_SURROGATEPASS_BYTES_TO_LOWER_HEX_WITH_V4_PREFIX"
SECRET_CANONICALIZATION = "UTF8_SURROGATEPASS_FOR_STR__BYTES_IDENTITY"
STRING_DOMAIN_TOTALITY = "TOTAL_FOR_EVERY_FINITE_PYTHON_STR_ACCEPTED_BY_LENGTH_GATE"


def _beacon_gate(beacon: Any) -> str:
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("POST_FREEZE_BEACON_INVALID")
    return beacon


def _canonical_beacon(beacon: Any) -> str:
    text = _beacon_gate(beacon)
    raw = text.encode("utf-8", "surrogatepass")
    # Hex is ASCII and injective over bytes, so all legacy strict-UTF8 helpers
    # receive an encodable string without collapsing distinct Python strings.
    return "UDIRV4-BEACON-HEX|" + raw.hex()


def _secret_bytes_total(secret: Any) -> bytes:
    if isinstance(secret, bytes):
        out = secret
    elif isinstance(secret, str):
        out = secret.encode("utf-8", "surrogatepass")
    else:
        raise v1.UnknownDomainGeneratorError("EVALUATOR_SECRET_INVALID")
    if len(out) < 32:
        raise v1.UnknownDomainGeneratorError("EVALUATOR_SECRET_TOO_SHORT")
    return out


def _generate(*, beacon: str, evaluator_secret: Any, namespace: str):
    canonical_beacon = _canonical_beacon(beacon)
    secret = _secret_bytes_total(evaluator_secret)
    out = v3._generate(
        beacon=canonical_beacon,
        evaluator_secret=secret,
        namespace=namespace,
    )
    out["schema"] = SCHEMA
    out["beacon_canonicalization"] = BEACON_CANONICALIZATION
    out["secret_canonicalization"] = SECRET_CANONICALIZATION
    out["string_domain_totality"] = STRING_DOMAIN_TOTALITY
    return out


def generate_production_population(*, beacon: str, evaluator_secret: Any, authority: Mapping[str, Any]):
    v1._production_authorized(authority)
    out = _generate(
        beacon=beacon,
        evaluator_secret=evaluator_secret,
        namespace="UDIRV4",
    )
    out["authority_claim_id"] = str(authority["one_use_claim_id"])
    out["production"] = True
    return out


def generate_qualification_fixture_population(*, beacon: str):
    out = _generate(
        beacon=beacon,
        evaluator_secret=b"QUALIFICATION-ONLY-V4-SECRET-0123456789-ABCDEFG",
        namespace="QUALV4",
    )
    out["production"] = False
    out["hard_nonclaim"] = "QUALIFICATION_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    return out
