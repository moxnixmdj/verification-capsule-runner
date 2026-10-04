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


    def test_lease_does_not_require_impossible_self_digest(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            payload=b"component-bytes"
            (root/"component.bin").write_bytes(payload)
            lease={
                "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_V1",
                "target_predicate":prod.TARGET,
                "authorized_leaves":sorted(prod.LEAVES),
                "limits":{"production_populations":1,"production_cases":27,"replay_allowed":False,"replacement_allowed":False},
                "resources":{"persistent_learned_bytes":0,"external_frontier_model_calls":0,"external_learned_capability_calls":0,"incremental_spend_usd":0},
                "exact_components":{"component.bin":prod._git_blob(payload)},
            }
            old=prod.ROOT
            try:
                prod.ROOT=root
                prod.validate_lease(lease,"f"*64)
            finally:
                prod.ROOT=old

    def test_lease_digest_is_raw_file_sha256(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"lease.json"; p.write_bytes(b'{"x":1}\n')
            raw,digest=prod.lease_bytes_and_digest(p)
            import hashlib
            self.assertEqual(digest,hashlib.sha256(raw).hexdigest())

if __name__=="__main__":
    unittest.main(verbosity=2)
