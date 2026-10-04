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
            return 201,{"ref":ref,"object":{"sha":sha}}
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

    def test_claim_201_wrong_object_sha_seals_without_execution(self):
        called={"execute":False}
        def fake_create(repo,token,ref,sha):
            return 201,{"ref":ref,"object":{"sha":"d"*40}}
        def fake_execute(**kwargs):
            called["execute"]=True
            return {}
        branch,out=prod.claim_then_execute(
            repo="x/y",token="t",launch_sha="c"*40,digest="e"*64,
            execute_fn=fake_execute,create_ref_fn=fake_create,
        )
        self.assertFalse(called["execute"])
        self.assertEqual(branch,"unknown-domain-direct-claims/"+"e"*64)
        self.assertEqual(out["status"],"ATOMIC_CLAIM_RESPONSE_INVALID__ONE_USE_CLAIM_CONSUMED__NO_EXECUTION__FAIL_CLOSED")
        self.assertEqual(out["production_cases_generated"],0)
        self.assertFalse(out["replay_allowed"])

    def test_post_claim_exception_is_hashed_not_persisted(self):
        secret_text="synthetic-hidden-secret"
        def fake_create(repo,token,ref,sha):
            return 201,{"ref":ref,"object":{"sha":sha}}
        def fake_execute(**kwargs):
            raise RuntimeError(secret_text)
        branch,out=prod.claim_then_execute(
            repo="x/y",token="t",launch_sha="c"*40,digest="d"*64,
            execute_fn=fake_execute,create_ref_fn=fake_create,
        )
        self.assertEqual(branch,"unknown-domain-direct-claims/"+"d"*64)
        self.assertEqual(out["status"],"PRODUCTION_EXECUTION_EXCEPTION__ONE_USE_CLAIM_CONSUMED__FAIL_CLOSED")
        self.assertEqual(out["exception_type"],"RuntimeError")
        self.assertFalse(out["exception_message_persisted"])
        self.assertNotIn(secret_text,json.dumps(out))
        self.assertEqual(len(out["exception_message_sha256"]),64)
        self.assertFalse(out["replay_allowed"])

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


    def test_result_persistence_ambiguous_write_accepts_exact_readback_only(self):
        content={"schema":"X","status":"PRODUCTION_PASS","case_results":[{"case_id":"c1","pass":True}]}
        raw=prod._result_bytes(content)
        def fake_put(repo,token,branch,path,doc):
            return 0,{"message":"TimeoutError"}
        def fake_get(repo,token,branch,path):
            return 200,raw,prod._git_blob(raw)
        receipt=prod.persist_result_durable(
            repo="x/y",token="t",branch="claim",path="result.json",content=content,
            attempts=1,put_fn=fake_put,get_fn=fake_get,sleep_fn=lambda _:None,
        )
        self.assertEqual(receipt["status"],"DURABLE_EXISTING_AND_READBACK_VERIFIED")
        self.assertEqual(receipt["write_status"],0)
        self.assertEqual(receipt["content_sha"],prod._git_blob(raw))

    def test_result_persistence_201_requires_exact_readback(self):
        content={"schema":"X","status":"PRODUCTION_PASS"}
        raw=prod._result_bytes(content)
        def fake_put(repo,token,branch,path,doc):
            return 201,{"commit":{"sha":"c"*40}}
        def fake_get(repo,token,branch,path):
            return 200,raw,prod._git_blob(raw)
        receipt=prod.persist_result_durable(
            repo="x/y",token="t",branch="claim",path="result.json",content=content,
            attempts=1,put_fn=fake_put,get_fn=fake_get,sleep_fn=lambda _:None,
        )
        self.assertEqual(receipt["status"],"DURABLE_CREATED_AND_READBACK_VERIFIED")
        self.assertEqual(receipt["commit_sha"],"c"*40)

    def test_result_persistence_wrong_remote_bytes_fail_closed(self):
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
                attempts=3,put_fn=fake_put,get_fn=fake_get,sleep_fn=lambda _:None,
            )
        self.assertEqual(puts["n"],3)

    def test_result_persistence_correct_bytes_wrong_git_blob_sha_fail_closed(self):
        content={"schema":"X","status":"PRODUCTION_PASS"}
        raw=prod._result_bytes(content)
        def fake_put(repo,token,branch,path,doc):
            return 201,{"commit":{"sha":"c"*40}}
        def fake_get(repo,token,branch,path):
            return 200,raw,"0"*40
        with self.assertRaisesRegex(prod.ProductionLaunchError,"RESULT_DURABILITY_NOT_ESTABLISHED:201"):
            prod.persist_result_durable(
                repo="x/y",token="t",branch="claim",path="result.json",content=content,
                attempts=1,put_fn=fake_put,get_fn=fake_get,sleep_fn=lambda _:None,
            )


if __name__=="__main__":
    unittest.main(verbosity=2)
