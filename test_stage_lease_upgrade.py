import unittest

from session_bridge.acceptance_contract import validate_lease_upgrade
from session_bridge import execution_authority_reducer as authority_reducer


def obs(commit, mode="EXACT_FETCH_ONLY"):
    return {
        "schema":"PROJECT_BRAIN_CONTINUOUS_OBS_CONTEXT_V1",
        "status":"CURRENT",
        "canonical_brain_commit":commit,
        "dependency_inventory_complete":True,
        "material_world_state_dependencies_complete":True,
      "information_boundary_complete":True,
      "information_policy":{"mode":mode,"allowed_exact_sources":[],"allowed_external_tool_kinds":[]},
        "unknown_material_dependencies":[],
        "stale_authority_absent":True,
        "valid_proof_action_priority":True,
        "obs_layers_current":{k:True for k in ("goal","capability","blocker","solution","verification","inherited_system","obs_process")},
        "canonical_state_dependencies":[
            {"path":"canonical/CANONICAL_POINTER.json","sha256":"d"*64},
            {"path":"canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json","sha256":"e"*64},
            {"path":"canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json","sha256":"f"*64},
        ],
        "dependencies":[{
            "dependency_id":"runner","class":"EXECUTION_SURFACE","material":True,
            "volatility":"STATIC","scope":"GLOBAL","status":"READY",
            "evidence":["runner receipt"]
        }],
    }


def authority_preflight(task):
    raw = [
        ("STAGE_A_PASS", "stage-a"),
        ("STAGE_B_PASS", "stage-b"),
        ("SOURCE_BOUNDARY_PASS", "source-boundary"),
        ("EXECUTION_SURFACE_PASS", "execution-surface"),
        ("ACCEPTANCE_FROZEN", "acceptance"),
        ("MINIMUM_REALITY_CUT_PASS", "minimum-reality-cut"),
        ("RUNTIME_API_PREFLIGHT_PASS", "runtime-api"),
        ("LEASE_ISSUED", "lease"),
        ("CARRIER_OPEN", {"pr": 999, "head": "fixture"}),
    ]
    events=[]
    prev=None
    for seq,(typ,evidence) in enumerate(raw):
        e={
            "schema":authority_reducer.SCHEMA,
            "event_id":f"auth-{seq}",
            "task":task,
            "seq":seq,
            "prev_event_sha256":prev,
            "type":typ,
            "evidence":evidence,
        }
        e["event_sha256"]=authority_reducer.canonical_event_hash(e)
        prev=e["event_sha256"]
        events.append(e)
    derived=authority_reducer.derive_authority(
        events,task=task,execution_budget=1,verifier_budget=1
    )
    assert derived["valid"] is True
    assert derived["can_execute"] is True
    return {
        "schema":"BRAIN_DERIVED_AUTHORITY_PREFLIGHT_V1",
        "reducer_git_blob_sha":"d49deb24be6a0ac268c700f788777c39fe33086d",
        "events":events,
        "state_sha256":derived["state_sha256"],
    }

def lease(scope, *, rank=17, task="data-anonymization", session="data-anonymization-20261001-v1", execute=False):
    return {
        "schema": "BRAIN_FAST_BURST_LEASE_AUTHORIZATION_V1",
        "session_id": session,
        "task": task,
        "authorization": True,
        "lease_merged_to_main": True,
        "canonical_brain_commit": "a" * 40,
        "canonical_lease_path": "canonical/governance/LEASE_TEST.json",
        "sample_rank": rank,
        "scope": scope,
        "task_execution_authorized": execute,
        "replay_for_credit": False,
        "continuous_obs": obs("a" * 40),
        "execution_count_allowed": 1 if execute else 0,
        "derived_authority_preflight": (authority_preflight(task) if execute else None),
        "terminal_verifier_count_allowed": 1 if execute else 0,
        "source_boundary_preflight": ({
            "schema": "BRAIN_SOURCE_BOUNDARY_PREFLIGHT_V1",
            "status": "PASS",
            "task_specific_external_search": False,
            "task_specific_hints_read": False,
            "solution_read": False,
            "tests_read": False,
            "hidden_verifier_read": False,
            "task_command_executed": False,
            "contamination_ledger_sha256": "c" * 64,
            "evidence": ["canonical contamination ledger independently checked"],
        } if execute else None),
        "runtime_api_preflight": ({
            "schema": "BRAIN_RUNTIME_API_CONTRACT_PREFLIGHT_V1",
            "status": "PASS",
            "exact_execution_surface": True,
            "planned_api_surface_complete": True,
            "unverified_api_symbols": [],
            "contracts": [{
                "id": "python-runtime",
                "symbol": "python.version_info",
                "expected_behavior": "runtime API is present with verified behavior",
                "status": "PASS",
                "evidence": ["exact-surface synthetic smoke"],
            }],
        } if execute else None),
        "execution_surface_preflight": ({
            "schema": "BRAIN_EXECUTION_SURFACE_PREFLIGHT_V1",
            "status": "PASS",
            "exact_or_materially_equivalent": True,
            "package_management_policy_verified": True,
            "required_install_steps_verified": True,
            "required_runtime_imports_verified": True,
            "environment_sha256": "b" * 64,
            "evidence": ["exact task-image smoke passed"],
        } if execute else None),
    }


class LeaseUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.stage_b = lease("STAGE_B_INSTRUCTION_EXPOSURE_ONLY", execute=False)
        self.stage_c = lease("STAGE_C_ONE_SHOT_EXECUTION", execute=True)

    def check(self, current=None, candidate=None, *, next_burst=0, acceptance_hash=None):
        return validate_lease_upgrade(
            current or self.stage_b,
            candidate or self.stage_c,
            "data-anonymization-20261001-v1",
            "data-anonymization",
            next_burst=next_burst,
            acceptance_hash=acceptance_hash,
        )

    def test_exact_monotonic_upgrade_passes(self):
        self.assertEqual(self.check(acceptance_hash="frozen"), [])

    def test_rank_swap_fails(self):
        x=lease("STAGE_C_ONE_SHOT_EXECUTION", rank=18, execute=True)
        self.assertIn("LEASE_UPGRADE_RANK_MISMATCH", self.check(candidate=x, acceptance_hash="frozen"))

    def test_wrong_target_scope_fails(self):
        x=lease("STAGE_B_INSTRUCTION_EXPOSURE_ONLY", execute=False)
        self.assertIn("LEASE_UPGRADE_TARGET_SCOPE_INVALID", self.check(candidate=x, acceptance_hash="frozen"))

    def test_post_burst_upgrade_fails(self):
        self.assertIn("LEASE_UPGRADE_AFTER_BUILDER_STARTED", self.check(next_burst=1, acceptance_hash="frozen"))

    def test_upgrade_before_acceptance_freeze_fails(self):
        self.assertIn("LEASE_UPGRADE_REQUIRES_ACCEPTANCE_FROZEN", self.check())

    def test_task_swap_fails_authorization(self):
        x=lease("STAGE_C_ONE_SHOT_EXECUTION", task="other-task", execute=True)
        self.assertIn("LEASE_TASK_MISMATCH", self.check(candidate=x, acceptance_hash="frozen"))

    def test_replay_enabled_fails(self):
        x=dict(self.stage_c); x["replay_for_credit"]=True
        self.assertIn("LEASE_UPGRADE_REPLAY_POLICY_INVALID", self.check(candidate=x, acceptance_hash="frozen"))

    def test_missing_execution_surface_preflight_fails(self):
        x=dict(self.stage_c); x.pop("execution_surface_preflight", None)
        self.assertIn("EXECUTION_SURFACE_PREFLIGHT_MISSING", self.check(candidate=x, acceptance_hash="frozen"))

    def test_host_only_approximation_fails(self):
        x=dict(self.stage_c)
        x["execution_surface_preflight"]=dict(x["execution_surface_preflight"])
        x["execution_surface_preflight"]["exact_or_materially_equivalent"]=False
        self.assertIn("EXECUTION_SURFACE_NOT_MATERIALLY_EQUIVALENT", self.check(candidate=x, acceptance_hash="frozen"))

    def test_package_policy_unverified_fails(self):
        x=dict(self.stage_c)
        x["execution_surface_preflight"]=dict(x["execution_surface_preflight"])
        x["execution_surface_preflight"]["package_management_policy_verified"]=False
        self.assertIn("PACKAGE_MANAGEMENT_POLICY_UNVERIFIED", self.check(candidate=x, acceptance_hash="frozen"))

    def test_install_smoke_missing_fails(self):
        x=dict(self.stage_c)
        x["execution_surface_preflight"]=dict(x["execution_surface_preflight"])
        x["execution_surface_preflight"]["required_install_steps_verified"]=False
        self.assertIn("REQUIRED_INSTALL_STEPS_UNVERIFIED", self.check(candidate=x, acceptance_hash="frozen"))


    def test_missing_source_boundary_preflight_fails(self):
        x=dict(self.stage_c); x.pop("source_boundary_preflight", None)
        self.assertIn("SOURCE_BOUNDARY_PREFLIGHT_MISSING", self.check(candidate=x, acceptance_hash="frozen"))

    def test_external_task_search_fails(self):
        x=dict(self.stage_c)
        x["source_boundary_preflight"]=dict(x["source_boundary_preflight"])
        x["source_boundary_preflight"]["task_specific_external_search"]=True
        self.assertIn("TASK_SPECIFIC_EXTERNAL_SEARCH_DETECTED", self.check(candidate=x, acceptance_hash="frozen"))

    def test_hidden_verifier_read_fails(self):
        x=dict(self.stage_c)
        x["source_boundary_preflight"]=dict(x["source_boundary_preflight"])
        x["source_boundary_preflight"]["hidden_verifier_read"]=True
        self.assertIn("HIDDEN_VERIFIER_READ", self.check(candidate=x, acceptance_hash="frozen"))

    def test_solution_read_fails(self):
        x=dict(self.stage_c)
        x["source_boundary_preflight"]=dict(x["source_boundary_preflight"])
        x["source_boundary_preflight"]["solution_read"]=True
        self.assertIn("SOLUTION_READ", self.check(candidate=x, acceptance_hash="frozen"))

    def test_tests_read_fails(self):
        x=dict(self.stage_c)
        x["source_boundary_preflight"]=dict(x["source_boundary_preflight"])
        x["source_boundary_preflight"]["tests_read"]=True
        self.assertIn("TESTS_READ", self.check(candidate=x, acceptance_hash="frozen"))

    def test_missing_ledger_digest_fails(self):
        x=dict(self.stage_c)
        x["source_boundary_preflight"]=dict(x["source_boundary_preflight"])
        x["source_boundary_preflight"]["contamination_ledger_sha256"]="bad"
        self.assertIn("CONTAMINATION_LEDGER_DIGEST_INVALID", self.check(candidate=x, acceptance_hash="frozen"))


    def test_missing_derived_authority_fails(self):
        x=dict(self.stage_c); x.pop("derived_authority_preflight", None)
        self.assertIn("DERIVED_AUTHORITY_PREFLIGHT_MISSING", self.check(candidate=x, acceptance_hash="frozen"))

    def test_broken_authority_hash_chain_fails(self):
        x=dict(self.stage_c)
        p=dict(x["derived_authority_preflight"])
        p["events"]=[dict(e) for e in p["events"]]
        p["events"][3]["prev_event_sha256"]="0"*64
        x["derived_authority_preflight"]=p
        errors=self.check(candidate=x, acceptance_hash="frozen")
        self.assertTrue(any(e.startswith("DERIVED_AUTHORITY_EVENT_CHAIN_INVALID:") for e in errors))

    def test_later_revocation_beats_stale_authorized_true(self):
        x=dict(self.stage_c)
        p=dict(x["derived_authority_preflight"])
        events=[dict(e) for e in p["events"]]
        prev=events[-1]["event_sha256"]
        e={
            "schema":authority_reducer.SCHEMA,
            "event_id":"auth-revoke",
            "task":"data-anonymization",
            "seq":len(events),
            "prev_event_sha256":prev,
            "type":"LEASE_REVOKED",
        }
        e["event_sha256"]=authority_reducer.canonical_event_hash(e)
        events.append(e)
        p["events"]=events
        derived=authority_reducer.derive_authority(events,task="data-anonymization",execution_budget=1,verifier_budget=1)
        p["state_sha256"]=derived["state_sha256"]
        x["derived_authority_preflight"]=p
        self.assertIn("DERIVED_AUTHORITY_CAN_EXECUTE_FALSE", self.check(candidate=x, acceptance_hash="frozen"))

    def test_wrong_derived_state_digest_fails(self):
        x=dict(self.stage_c)
        p=dict(x["derived_authority_preflight"])
        p["state_sha256"]="0"*64
        x["derived_authority_preflight"]=p
        self.assertIn("DERIVED_AUTHORITY_STATE_DIGEST_MISMATCH", self.check(candidate=x, acceptance_hash="frozen"))


    def test_missing_runtime_api_preflight_fails(self):
        x=dict(self.stage_c); x.pop("runtime_api_preflight", None)
        self.assertIn("RUNTIME_API_PREFLIGHT_MISSING", self.check(candidate=x, acceptance_hash="frozen"))

    def test_unverified_runtime_api_symbol_fails(self):
        x=dict(self.stage_c)
        x["runtime_api_preflight"]=dict(x["runtime_api_preflight"])
        x["runtime_api_preflight"]["unverified_api_symbols"]=["FreeCAD.Base.Vector.X"]
        self.assertIn("UNVERIFIED_RUNTIME_API_SYMBOLS_REMAIN", self.check(candidate=x, acceptance_hash="frozen"))

    def test_nonexact_runtime_api_surface_fails(self):
        x=dict(self.stage_c)
        x["runtime_api_preflight"]=dict(x["runtime_api_preflight"])
        x["runtime_api_preflight"]["exact_execution_surface"]=False
        self.assertIn("RUNTIME_API_PREFLIGHT_NOT_EXACT_SURFACE", self.check(candidate=x, acceptance_hash="frozen"))


if __name__ == "__main__":
    unittest.main()
