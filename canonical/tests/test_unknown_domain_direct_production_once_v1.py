from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as generator
from canonical.runtime import unknown_domain_direct_production_once_v1 as prod

class ProductionLauncherTests(unittest.TestCase):
    def test_claim_failure_prevents_execution(self):
        called={"execute":False}
        def fake_create(repo,token,ref,sha):
            return 422,{"message":"Reference already exists"}
        def fake_execute(**kwargs):
            called["execute"]=True
            return {}
        with self.assertRaisesRegex(prod.ProductionLaunchError,"ATOMIC_CLAIM_CREATE_NOT_201:422"):
            prod.claim_then_execute(
                repo="x/y",token="t",launch_sha="a"*40,digest="b"*64,
                execute_fn=fake_execute,create_ref_fn=fake_create,
            )
        self.assertFalse(called["execute"])

    def test_claim_success_executes_once_and_binds_receipt(self):
        calls={"n":0}
        def fake_create(repo,token,ref,sha):
            return 201,{"ref":ref,"object":{"sha":"c"*40}}
        def fake_execute(**kwargs):
            calls["n"]+=1
            return {"status":"X","authority_claim_id":kwargs["claim_id"]}
        branch,out=prod.claim_then_execute(
            repo="x/y",token="t",launch_sha="a"*40,digest="b"*64,
            execute_fn=fake_execute,create_ref_fn=fake_create,
        )
        self.assertEqual(calls["n"],1)
        self.assertEqual(branch,"unknown-domain-direct-claims/"+"b"*64)
        self.assertEqual(out["claim_create_http_status"],201)
        self.assertEqual(out["claim_uniqueness_source"],"ATOMIC_CREATE_RESPONSE")

    def test_qualification_packet_evaluation_is_sanitized(self):
        packet=generator.generate_qualification_fixture_population(beacon="LAUNCHER-VERIFY-0123456789")
        out=prod.evaluate_packet(packet)
        self.assertEqual(len(out["case_results"]),27)
        self.assertTrue(out["aggregate"]["all_27_cases_pass"],out["aggregate"])
        raw=json.dumps(out)
        self.assertNotIn("hidden_records",raw)
        self.assertNotIn("evaluator_secret",raw)


    def test_actual_lease_validates_with_closed_transitive_components(self):
        lease=json.loads(prod.LEASE_PATH.read_text())
        raw,digest=prod.lease_bytes_and_digest()
        self.assertIn("canonical/runtime/unknown_domain_direct_hidden_generator_v1.py",lease["exact_components"])
        prod.validate_lease(lease,digest)
        self.assertEqual(prod.canonical_identity_from_lease(lease),lease["lease_identity"])

    def test_claim_identity_ignores_incidental_metadata(self):
        lease=json.loads(prod.LEASE_PATH.read_text())
        with tempfile.TemporaryDirectory() as d:
            p1=Path(d)/"a.json"
            p2=Path(d)/"b.json"
            a=json.loads(json.dumps(lease))
            b=json.loads(json.dumps(lease))
            b["date"]="2099-12-31"
            b["status"]="INCIDENTAL_METADATA_CHANGED"
            p1.write_text(json.dumps(a,sort_keys=True))
            p2.write_text(json.dumps(b,sort_keys=True))
            _,d1=prod.lease_bytes_and_digest(p1)
            _,d2=prod.lease_bytes_and_digest(p2)
            self.assertEqual(d1,d2)

    def test_claim_identity_changes_on_load_bearing_subject_mutation(self):
        lease=json.loads(prod.LEASE_PATH.read_text())
        original=prod.canonical_identity_from_lease(lease)
        altered=json.loads(json.dumps(lease))
        altered["exact_components"]["canonical/runtime/unknown_domain_direct_hidden_generator_v1.py"]="0"*40
        changed=prod.canonical_identity_from_lease(altered)
        self.assertNotEqual(original,changed)


if __name__=="__main__":
    unittest.main(verbosity=2)
