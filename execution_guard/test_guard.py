import dataclasses, inspect, json, pathlib, tempfile, unittest
import guard
from guard import Denied, Frozen, MemStore, reserve_live, seed_history
from audit import audit

S=Frozen("gate","1"*64,"2"*64,"3"*64,"4"*40,"5"*64)

class GuardTests(unittest.TestCase):
    def test_duplicate_and_alias_problem_denied(self):
        st=MemStore(); reserve_live(st,S,"a","test://1")
        with self.assertRaises(Denied): reserve_live(st,S,"b","test://2")
        with self.assertRaises(Denied): reserve_live(st,dataclasses.replace(S,gate_id="alias"),"b","test://2")

    def test_historical_seed_denies_replay_and_is_idempotent(self):
        st=MemStore()
        item={"attempt_id":"6"*32,"owner_id":"hist","source_ref":"test://old","source_evidence_sha256":"7"*64,"observed_at":"2026-09-30T04:00:00Z"}
        seed_history(st,S,item); seed_history(st,S,item)
        with self.assertRaises(Denied): reserve_live(st,dataclasses.replace(S,gate_id="alias"),"new","test://new")

    def test_audit_rejects_unguarded(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); (root/".github/workflows").mkdir(parents=True)
            (root/".github/workflows/x.yml").write_text("permissions:\n  contents: read\nsteps:\n  - run: python run_parent_once.py\n")
            inv=root/"inv.json"
            inv.write_text(json.dumps({"schema":"BRAIN_EXECUTION_LAUNCHER_INVENTORY_V1","launchers":[{"workflow":".github/workflows/x.yml","science_command":"python run_parent_once.py","binding":"b.json"}]}))
            self.assertTrue(audit(root,inv))

    def test_guard_source_scrubs_child_credentials(self):
        src=inspect.getsource(guard.cmd_run)
        self.assertIn("env.pop(secret_name,None)",src)
        for name in ("GITHUB_TOKEN","GH_TOKEN","GITHUB_PAT","GITHUB_APP_TOKEN","BRAIN_EXECUTION_GUARD_TOKEN"):
            self.assertIn(name,src)

if __name__=="__main__":
    unittest.main()
