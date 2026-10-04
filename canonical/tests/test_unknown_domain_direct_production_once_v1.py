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

    def test_claim_response_sha_mismatch_aborts_before_execution(self):
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
        self.assertEqual(out["status"],"ATOMIC_CLAIM_RESPONSE_INVALID__ONE_USE_CLAIM_CONSUMED__NO_EXECUTION__FAIL_CLOSED")
        self.assertEqual(out["production_cases_generated"],0)
        self.assertFalse(out["replay_allowed"])

    def test_claim_transport_exception_is_zero_execution_and_sanitized(self):
        called={"execute":False}
        def fake_create(repo,token,ref,sha):
            raise TimeoutError("secret-looking-transport-detail")
        def fake_execute(**kwargs):
            called["execute"]=True
            return {}
        branch,out=prod.claim_then_execute(
            repo="x/y",token="t",launch_sha="a"*40,digest="f"*64,
            execute_fn=fake_execute,create_ref_fn=fake_create,
        )
        self.assertFalse(called["execute"])
        self.assertEqual(branch,"unknown-domain-direct-claims/"+"f"*64)
        self.assertEqual(out["status"],"ATOMIC_CLAIM_TRANSPORT_EXCEPTION__OUTCOME_AMBIGUOUS__NO_EXECUTION__FAIL_CLOSED")
        self.assertIsNone(out["claim_create_http_status"])
        self.assertTrue(out["posthoc_claim_ref_reconciliation_required"])
        self.assertEqual(out["production_cases_generated"],0)
        self.assertIn("claim_transport_exception_message_sha256",out)
        self.assertNotIn("claim_transport_exception_message",out)
        self.assertNotIn("secret-looking-transport-detail",json.dumps(out))
        self.assertFalse(out["replay_allowed"])

    def test_malformed_201_response_is_consumed_claim_zero_execution(self):
        called={"execute":False}
        def fake_create(repo,token,ref,sha):
            return 201,{"_malformed_json_response":True}
        def fake_execute(**kwargs):
            called["execute"]=True
            return {}
        _,out=prod.claim_then_execute(
            repo="x/y",token="t",launch_sha="a"*40,digest="e"*64,
            execute_fn=fake_execute,create_ref_fn=fake_create,
        )
        self.assertFalse(called["execute"])
        self.assertEqual(out["status"],"ATOMIC_CLAIM_RESPONSE_INVALID__ONE_USE_CLAIM_CONSUMED__NO_EXECUTION__FAIL_CLOSED")
        self.assertEqual(out["production_cases_generated"],0)
        self.assertFalse(out["replay_allowed"])

    def test_post_claim_execution_exception_is_sealed_and_sanitized(self):
        def fake_create(repo,token,ref,sha):
            return 201,{"ref":ref,"object":{"sha":"a"*40}}
        def fake_execute(**kwargs):
            raise RuntimeError("secret-looking-execution-detail")
        _,out=prod.claim_then_execute(
            repo="x/y",token="t",launch_sha="a"*40,digest="d"*64,
            execute_fn=fake_execute,create_ref_fn=fake_create,
        )
        self.assertEqual(out["status"],"PRODUCTION_EXECUTION_EXCEPTION__ONE_USE_CLAIM_CONSUMED__FAIL_CLOSED")
        self.assertEqual(out["exception_type"],"RuntimeError")
        self.assertIn("exception_message_sha256",out)
        self.assertNotIn("exception_message",out)
        self.assertNotIn("secret-looking-execution-detail",json.dumps(out))
        self.assertFalse(out["replay_allowed"])
        self.assertFalse(out["replacement_allowed"])

    def test_runtime_environment_is_exactly_pinned(self):
        prod.validate_runtime_environment(version_info=(3,12,15),machine="x86_64")
        with self.assertRaisesRegex(prod.ProductionLaunchError,"PYTHON_RUNTIME_VERSION_MISMATCH"):
            prod.validate_runtime_environment(version_info=(3,12,14),machine="x86_64")
        with self.assertRaisesRegex(prod.ProductionLaunchError,"PYTHON_RUNTIME_ARCH_MISMATCH"):
            prod.validate_runtime_environment(version_info=(3,12,15),machine="arm64")

    def test_production_workflow_runtime_is_commit_and_patch_pinned(self):
        p=prod.ROOT/".github/workflows/unknown-domain-direct-one-use-production.yml"
        text=p.read_text()
        self.assertIn("actions/checkout@11d5960a326750d5838078e36cf38b85af677262",text)
        self.assertIn("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",text)
        self.assertIn("python-version: '3.12.15'",text)
        self.assertIn("architecture: 'x64'",text)
        self.assertIn("ref: ${{ github.sha }}",text)

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
