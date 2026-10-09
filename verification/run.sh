#!/usr/bin/env bash
set -euo pipefail

python3 -m unittest -v canonical.tests.test_sec_companyconcept_source_native_v1

python3 - <<'PY'
import hashlib
import json
import pathlib
from canonical.runtime.bound_capabilities import sec_companyconcept_source_native as producer
from canonical.runtime import sec_companyconcept_source_native_verify_v1 as verifier
from canonical.runtime.source_traceable_semantic_ir import compile_semantic_ir

root = pathlib.Path(".").resolve()
tmp = root / "canonical" / "tmp" / "sec_live_verify"
tmp.mkdir(parents=True, exist_ok=True)
(tmp / "config.json").write_text(json.dumps({
    "cik": 320193,
    "taxonomy": "us-gaap",
    "tag": "GrossProfit",
    "sec_user_agent": "ProjectBrain verification@example.com",
}), encoding="utf-8")
args = {
    "config_path": "canonical/tmp/sec_live_verify/config.json",
    "raw_output_path": "canonical/tmp/sec_live_verify/raw.json",
    "semantic_output_path": "canonical/tmp/sec_live_verify/semantic.json",
    "timeout_s": 30,
    "max_bytes": 4000000,
    "max_rows": 2000,
}
out = producer.run(args, root)
check = verifier.verify(
    root=root,
    raw_path=args["raw_output_path"],
    semantic_path=args["semantic_output_path"],
)
semantic = json.loads((root / args["semantic_output_path"]).read_text(encoding="utf-8"))
ir = compile_semantic_ir(semantic["semantic_contract"])
raw = (root / args["raw_output_path"]).read_bytes()
payload = json.loads(raw.decode("utf-8"))

assert payload["cik"] == 320193
assert payload["taxonomy"] == "us-gaap"
assert payload["tag"] == "GrossProfit"
assert payload["entityName"] == "Apple Inc."
assert out["source_native_identity_extracted"] is True
assert out["concept_qname"] == "us-gaap:GrossProfit"
assert out["fact_row_count"] > 0
assert check["verified"] is True, check
assert check["producer_independent"] is True, check
assert ir["status"] == "COMPILED", ir

missing = 0
rows = 0
for values in payload["units"].values():
    assert isinstance(values, list)
    for row in values:
        rows += 1
        for key in ("end", "filed", "accn", "form"):
            if row.get(key) is None:
                missing += 1
assert rows == out["fact_row_count"]
assert missing == 0

receipt = {
    "schema": "PROJECT_BRAIN_SEC_COMPANYCONCEPT_PUBLIC_INDEPENDENT_REPLAY_V1",
    "status": "PASS__EXACT_CODE__ADVERSARIAL_SUITE__LIVE_SEC_SOURCE__INDEPENDENT_BYTE_TO_SEMANTIC_VERIFY",
    "producer_blob": "679ab4ccf981445f7149082d91df7343be5eef57",
    "verifier_blob": "4281bf1212b518e08e5224625693d389810691bd",
    "test_blob": "37a01aa9a1ab46eb07045399d8167ac04a5c6e04",
    "semantic_ir_blob": "cf40b0b4d8f71f15f0140f009b602ff913db6750",
    "source_sha256": hashlib.sha256(raw).hexdigest(),
    "source_bytes": len(raw),
    "concept_qname": out["concept_qname"],
    "fact_row_count": out["fact_row_count"],
    "rows_missing_required_metadata": missing,
    "independent_verifier_status": check["status"],
    "semantic_ir_status": ir["status"],
    "semantic_authority_claimed": False,
    "terminal_credit": False,
}
pathlib.Path("sec-companyconcept-live-receipt.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(receipt, sort_keys=True))
PY
