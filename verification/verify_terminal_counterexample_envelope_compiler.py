import hashlib
import importlib.util
import json
from pathlib import Path

EXPECTED_BRAIN_BLOB = "86344162be260f294e5af87c56141e7e41fd0f5a"
path = Path("verification/terminal_counterexample_envelope_compiler.py")
source = path.read_bytes()

spec = importlib.util.spec_from_file_location("terminal_envelope", path)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

mod.self_test()

# Independent checks beyond the embedded self-test.
out = mod.evaluate({
    "contract_id": "CHAIN",
    "required_dimensions": ["A", "B", "C", "D"],
    "verified_envelopes": [{
        "id": "A_PASS",
        "covers": ["A"],
        "receipt": "receipt://a",
        "proof_kind": "FORMAL_PROOF",
        "authority_verified": True,
    }],
    "verified_failures": [],
    "verified_implications": [
        {"if_proved": ["A"], "then_proved": ["B"], "receipt": "r://ab", "authority_verified": True},
        {"if_proved": ["B"], "then_proved": ["C"], "receipt": "r://bc", "authority_verified": True},
    ],
})
errors=[]
if out.get("proved_dimensions_after_implication_closure") != ["A","B","C"]: errors.append("TRANSITIVE_CLOSURE")
if out.get("minimum_residual_proof_basis") != ["D"]: errors.append("RESIDUAL_BASIS")
if out.get("terminal_credit_delta") != 0: errors.append("CREDIT")
if out.get("fresh_terminal_evidence_consumed") != 0: errors.append("FRESH_EVIDENCE")
if "SIMULATION" not in out.get("authority_rule",""): errors.append("AUTHORITY_RULE")

bad = mod.evaluate({
    "contract_id":"BAD",
    "required_dimensions":["A"],
    "verified_envelopes":[{"id":"SIM","covers":["A"],"receipt":"r","proof_kind":"SIMULATION_PREDICTION","authority_verified":True}],
    "verified_failures":[],
    "verified_implications":[],
})
if bad.get("status") != "FAIL_CLOSED": errors.append("SIMULATION_FAIL_CLOSED")

print(json.dumps({
    "pass": not errors,
    "errors": errors,
    "brain_blob_sha": EXPECTED_BRAIN_BLOB,
    "mirrored_source_sha256": hashlib.sha256(source).hexdigest(),
}, sort_keys=True))
raise SystemExit(1 if errors else 0)
