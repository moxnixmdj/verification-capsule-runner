from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as generator
from canonical.runtime import unknown_domain_direct_production_once_v1 as prod

class ProductionLauncherTests(unittest.TestCase):
    def test_runtime_head_must_equal_create_event_sha(self):
        prod.validate_event_sha_binding("a"*40,"a"*40)
        with self.assertRaisesRegex(prod.ProductionLaunchError,"RUNTIME_HEAD_EVENT_SHA_MISMATCH"):
            prod.validate_event_sha_binding("a"*40,"b"*40)

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
            return 201,{"ref":ref,"object":{"sha":"a"*40}}
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
        self.assertEqual(out["claim_response_object_sha"],"a"*40)
        self.assertEqual(out["launch_event_sha"],"a"*40)

    def test_claim_response_sha_mismatch_seals_without_execution(self):
        called={"execute":False}
        def fake_create(repo,token,ref,sha):
            return 201,{"ref":ref,"object":{"sha":"c"*40}}
        def fake_execute(**kwargs):
            called["execute"]=True
            return {}
        branch,out=prod.claim_then_execute(
            repo="x/y",token="t",launch_sha="a"*40,digest="b"*64,
            execute_fn=fake_execute,create_ref_fn=fake_create,
        )
        self.assertFalse(called["execute"])
        self.assertEqual(branch,"unknown-domain-direct-claims/"+"b"*64)
        self.assertEqual(out["claim_create_http_status"],201)
        self.assertEqual(out["status"],"ATOMIC_CLAIM_RESPONSE_SHA_MISMATCH__ONE_USE_CLAIM_CONSUMED__NO_EXECUTION__FAIL_CLOSED")
        self.assertEqual(out["production_cases_generated"],0)
        self.assertFalse(out["replay_allowed"])

    def test_nonmapping_201_response_seals_without_execution(self):
        called={"execute":False}
        def fake_create(repo,token,ref,sha):
            return 201,"invalid-response"
        def fake_execute(**kwargs):
            called["execute"]=True
            return {}
        _,out=prod.claim_then_execute(
            repo="x/y",token="t",launch_sha="a"*40,digest="c"*64,
            execute_fn=fake_execute,create_ref_fn=fake_create,
        )
        self.assertFalse(called["execute"])
        self.assertEqual(out["status"],"ATOMIC_CLAIM_RESPONSE_SHA_MISMATCH__ONE_USE_CLAIM_CONSUMED__NO_EXECUTION__FAIL_CLOSED")
        self.assertEqual(out["production_cases_generated"],0)

    def test_post_claim_execution_exception_is_sealed_fail_closed(self):
        def fake_create(repo,token,ref,sha):
            return 201,{"ref":ref,"object":{"sha":"a"*40}}
        def fake_execute(**kwargs):
            raise RuntimeError("synthetic-post-claim-failure")
        branch,out=prod.claim_then_execute(
            repo="x/y",token="t",launch_sha="a"*40,digest="d"*64,
            execute_fn=fake_execute,create_ref_fn=fake_create,
        )
        self.assertEqual(branch,"unknown-domain-direct-claims/"+"d"*64)
        self.assertEqual(out["claim_create_http_status"],201)
        self.assertEqual(out["status"],"PRODUCTION_EXECUTION_EXCEPTION__ONE_USE_CLAIM_CONSUMED__FAIL_CLOSED")
        self.assertEqual(out["exception_type"],"RuntimeError")
        self.assertFalse(out["replay_allowed"])
        self.assertFalse(out["replacement_allowed"])

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
        _,digest=prod.lease_bytes_and_digest()
        self.assertIn("canonical/runtime/unknown_domain_direct_hidden_generator_v1.py",lease["exact_components"])
        prod.validate_lease(lease,digest)
        self.assertEqual(prod.canonical_identity_from_lease(lease),lease["lease_identity"])

    def test_claim_identity_ignores_incidental_and_control_plane_metadata(self):
        lease=json.loads(prod.LEASE_PATH.read_text())
        original=prod.canonical_identity_from_lease(lease)
        altered=json.loads(json.dumps(lease))
        altered["date"]="2099-12-31"
        altered["status"]="INCIDENTAL_METADATA_CHANGED"
        altered["exact_components"]["canonical/runtime/unknown_domain_direct_production_once_v1.py"]="0"*40
        altered["exact_components"][".github/workflows/unknown-domain-direct-one-use-production.yml"]="1"*40
        self.assertEqual(original,prod.canonical_identity_from_lease(altered))

    def test_claim_identity_changes_on_load_bearing_execution_subject_mutation(self):
        lease=json.loads(prod.LEASE_PATH.read_text())
        original=prod.canonical_identity_from_lease(lease)
        altered=json.loads(json.dumps(lease))
        altered["exact_components"]["canonical/runtime/unknown_domain_direct_hidden_generator_v1.py"]="0"*40
        self.assertNotEqual(original,prod.canonical_identity_from_lease(altered))

if __name__=="__main__":
    unittest.main(verbosity=2)
