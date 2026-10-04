from __future__ import annotations
import hashlib, json
from pathlib import Path
from canonical.runtime.unknown_domain_direct_production_preflight_v1 import preflight

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_PRODUCTION_PREFLIGHT_INPUT_V1.json":"deb2e2ce7d639b5650fa2e76d44425ee547157ef",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_PREDICATE_LOCAL_ACTIVATION_V1.json":"337bb7ee777e8b0f7f6340f395ca6c50e466594c",
 "canonical/verification/UNKNOWN_DOMAIN_V2_FINAL_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"93353244a5a0a6a7ef2e1e0a3a1bbedb63cef3ec",
 "canonical/runtime/unknown_domain_direct_production_preflight_v1.py":"e1365ccdba308c529f182797cf68075b2f1dc07c",
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd"
}
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for p,e in EXPECTED.items():
 g=blob((ROOT/p).read_bytes()); assert g==e,(p,g,e)
doc=json.loads((ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_PRODUCTION_PREFLIGHT_INPUT_V1.json").read_text())
out=preflight(doc)
assert out["ready"] is True,out
assert out["status"]=="READY_FOR_ATOMIC_ONE_USE_CLAIM_ONLY",out
assert out["execution_authority"] is False
assert out["fresh_reality_authority"] is False
assert out["promotion_authority"] is False
print(json.dumps(out,sort_keys=True))
