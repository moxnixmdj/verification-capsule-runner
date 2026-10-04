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
        with self.assertRaisesRegex(prod.ProductionLaunchError,"ATOMIC_CLAIM_RESPONSE_SHA_MISMATCH"):
            prod.claim_then_execute(
                repo="x/y",token="t",launch_sha="a"*40,digest="b"*64,
                execute_fn=fake_execute,create_ref_fn=fake_create,
            )
        self.assertFalse(called["execute"])

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

    def test_result_persistence_ambiguous_write_accepts_only_exact_byte_and_git_blob_readback(self):
        content={"schema":"X","status":"PRODUCTION_PASS","case_results":[{"case_id":"c1","pass":True}]}
        raw=prod._result_bytes(content)
        def fake_put(repo,token,branch,path,doc):
            return 0,{"message":"TimeoutError"}
        def fake_get(repo,token,branch,path):
            return 200,raw,prod._git_blob(raw)
        receipt=prod.persist_result_durable(
            repo="x/y",token="t",branch="claim",path="result.json",content=content,
            attempts=1,put_fn=fake_put,get_fn=fake_get,sleep_fn=lambda _:None,emit_recovery=False,
        )
        self.assertEqual(receipt["status"],"DURABLE_EXISTING_AND_READBACK_VERIFIED")
        self.assertEqual(receipt["write_status"],0)
        self.assertEqual(receipt["content_sha"],prod._git_blob(raw))

    def test_result_persistence_201_still_requires_exact_readback(self):
        content={"schema":"X","status":"PRODUCTION_PASS"}
        raw=prod._result_bytes(content)
        def fake_put(repo,token,branch,path,doc):
            return 201,{"commit":{"sha":"c"*40}}
        def fake_get(repo,token,branch,path):
            return 200,raw,prod._git_blob(raw)
        receipt=prod.persist_result_durable(
            repo="x/y",token="t",branch="claim",path="result.json",content=content,
            attempts=1,put_fn=fake_put,get_fn=fake_get,sleep_fn=lambda _:None,emit_recovery=False,
        )
        self.assertEqual(receipt["status"],"DURABLE_CREATED_AND_READBACK_VERIFIED")
        self.assertEqual(receipt["commit_sha"],"c"*40)

    def test_result_persistence_retries_and_fails_closed_on_wrong_remote_bytes(self):
        content={"schema":"X","status":"PRODUCTION_PASS"}
        puts={"n":0}
        def fake_put(repo,token,branch,path,doc):
            puts["n"]+=1
            return 503,{"message":"temporary"}
        def fake_get(repo,token,branch,path):
            return 200,b"wrong-bytes",prod._git_blob(b"wrong-bytes")
        with self.assertRaisesRegex(prod.ProductionLaunchError,"RESULT_DURABILITY_NOT_ESTABLISHED:503"):
            prod.persist_result_durable(
                repo="x/y",token="t",branch="claim",path="result.json",content=content,
                attempts=3,put_fn=fake_put,get_fn=fake_get,sleep_fn=lambda _:None,emit_recovery=False,
            )
        self.assertEqual(puts["n"],3)

    def test_result_persistence_rejects_correct_bytes_with_wrong_git_blob_sha(self):
        content={"schema":"X","status":"PRODUCTION_PASS"}
        raw=prod._result_bytes(content)
        def fake_put(repo,token,branch,path,doc):
            return 201,{"commit":{"sha":"c"*40}}
        def fake_get(repo,token,branch,path):
            return 200,raw,"0"*40
        with self.assertRaisesRegex(prod.ProductionLaunchError,"RESULT_DURABILITY_NOT_ESTABLISHED:201"):
            prod.persist_result_durable(
                repo="x/y",token="t",branch="claim",path="result.json",content=content,
                attempts=1,put_fn=fake_put,get_fn=fake_get,sleep_fn=lambda _:None,emit_recovery=False,
            )


if __name__=="__main__":
    unittest.main(verbosity=2)
