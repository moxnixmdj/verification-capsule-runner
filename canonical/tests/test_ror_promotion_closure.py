#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, subprocess, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
MODULE=ROOT/"canonical/runtime/bound_capabilities/source_authority_binding_ror.py"
REGISTRY=ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
RECEIPT=ROOT/"canonical/capabilities/obsolescence/MODEL_INDEPENDENT_ROR_SOURCE_AUTHORITY_IDENTITY_PROMOTION_20260930_V1.json"
EXPECTED_MODULE_BLOB="9396ff7169b274af9bbfbe736e004587631e3b05"

class PromotionClosure(unittest.TestCase):
    def test_exact_qualified_module_blob(self):
        got=subprocess.check_output(["git","hash-object",str(MODULE)],text=True).strip()
        self.assertEqual(got,EXPECTED_MODULE_BLOB)

    def test_registry_is_narrow_verified_binding(self):
        reg=json.loads(REGISTRY.read_text())
        e=reg["capabilities"]["source.authority.identity.ror"]
        self.assertEqual(e["status"],"VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(e["adapter_module"],"source_authority_binding_ror")
        self.assertEqual(e["provides"],["source.authority.host_organization_identity"])
        self.assertEqual(e["verification"]["producer_git_blob"],EXPECTED_MODULE_BLOB)
        self.assertEqual(e["verification"]["public_run_id"],36676947006)
        limits=" ".join(e.get("limitations") or []).lower()
        for word in ("primary-source","relevance","factual","evidence sufficiency"):
            self.assertIn(word,limits)
        self.assertEqual(e["incremental_spend_usd"],0)

    def test_receipt_matches_public_qualification(self):
        r=json.loads(RECEIPT.read_text())
        self.assertEqual(r["exact_producer_git_blob"],EXPECTED_MODULE_BLOB)
        self.assertEqual(r["public_qualification"]["workflow_run_id"],36676947006)
        self.assertEqual(r["public_qualification"]["conclusion"],"success")
        self.assertEqual(r["model_dependency_count"],0)
        self.assertEqual(r["incremental_spend_usd"],0)

if __name__=="__main__": unittest.main(verbosity=2)
