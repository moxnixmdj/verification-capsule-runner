from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

from canonical.runtime import r2_finance_task_role_raw_fact_unless_direct_adequacy_v1 as direct
from canonical.runtime import finance_task_role_raw_fact_unless_branch_v1 as producer
from canonical.runtime import finance_task_role_raw_fact_unless_verify_v1 as verifier

POLICY = (
    "Total exposure means exposure_amount. "
    "Apply Rule A unless Total exposure is at least 125.50."
)
BOOL_POLICY = (
    "Exception status means breach. "
    "Apply Rule A unless Exception status is true."
)


def goal():
    return (
        "Using the task-role cross-document finance UNLESS case at "
        "canonical/tmp/case.json, select and independently verify the applicable "
        "branch and save it to canonical/tmp/result.json."
    )


def write_bundle(root: Path, value="130.00", policy=POLICY, bool_mode=False, raw_fact=None):
    policy_rel = "canonical/tmp/policy.txt"
    fact_rel = "canonical/tmp/facts.json"
    case_rel = "canonical/tmp/case.json"
    pp, fp, cp = root / policy_rel, root / fact_rel, root / case_rel
    pp.parent.mkdir(parents=True, exist_ok=True)
    pp.write_text(policy, encoding="utf-8")
    if raw_fact is None:
        if bool_mode:
            facts = {
                "schema_id": "FINANCE_TYPED_CONTEXT_V1",
                "fields": {"breach": {"type": "BOOL", "value": value is True}},
            }
        else:
            facts = {
                "schema_id": "FINANCE_TYPED_CONTEXT_V1",
                "fields": {
                    "exposure_amount": {
                        "type": "DECIMAL_STRING",
                        "value": str(value),
                    }
                },
            }
        raw_fact = json.dumps(facts, separators=(",", ":"))
    fp.write_text(raw_fact, encoding="utf-8")
    case = {
        "schema": producer.INPUT_SCHEMA,
        "task_record": {
            "task_id": "finance-crossdoc-task",
            "shared_files": [policy_rel, fact_rel],
            "week_files": [],
            "source_roles": {
                "policy_source_path": policy_rel,
                "fact_source_path": fact_rel,
            },
        },
    }
    cp.write_text(json.dumps(case), encoding="utf-8")
    return case, cp, pp, fp


class CrossDocumentRouteTests(unittest.TestCase):
    def test_decimal_true_and_false(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_bundle(root, "130.00")
            out = direct.run({"task_id": "a", "goal": goal()}, repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["selected_branch"], "EXCEPTION_BRANCH")
            self.assertTrue(out["condition_holds"])
            self.assertTrue(out["acceptance_receipt"]["producer_independent"])

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_bundle(root, "100.00")
            out = direct.run({"task_id": "b", "goal": goal()}, repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["selected_branch"], "ORDINARY_BRANCH")
            self.assertFalse(out["condition_holds"])
            result = json.loads((root / "canonical/tmp/result.json").read_text())
            self.assertEqual(result["selected_text"], "Apply Rule A")

    def test_boolean(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_bundle(root, True, policy=BOOL_POLICY, bool_mode=True)
            out = direct.run({"task_id": "c", "goal": goal()}, repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["operator"], "BOOL_EQ")
            self.assertEqual(out["selected_branch"], "EXCEPTION_BRANCH")

    def test_undeclared_fact_role_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            case, cp, _, _ = write_bundle(root)
            case["task_record"]["shared_files"] = ["canonical/tmp/policy.txt"]
            cp.write_text(json.dumps(case), encoding="utf-8")
            out = direct.preflight({"task_id": "d", "goal": goal()}, repo_root=root)
            self.assertEqual(out["status"], "FAIL_CLOSED")
            self.assertIn("FACT_SOURCE_ROLE_NOT_IN_DECLARED_SOURCE_SET", out["reason"])

    def test_duplicate_json_fact_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = (
                '{"schema_id":"FINANCE_TYPED_CONTEXT_V1","fields":{'
                '"exposure_amount":{"type":"DECIMAL_STRING","value":"130.00"},'
                '"exposure_amount":{"type":"DECIMAL_STRING","value":"0.00"}}}'
            )
            write_bundle(root, raw_fact=raw)
            out = direct.preflight({"task_id": "e", "goal": goal()}, repo_root=root)
            self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_verifier_rejects_tampered_branch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            case, _, _, _ = write_bundle(root)
            result = producer.compute(case, repo_root=root)
            result["selected_branch"] = "ORDINARY_BRANCH"
            checked = verifier.verify(case, result, repo_root=root)
            self.assertFalse(checked["verified"])
            self.assertIn("MISMATCH:selected_branch", checked["errors"])

    def test_preflight_side_effect_free(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_bundle(root)
            out = direct.preflight({"task_id": "f", "goal": goal()}, repo_root=root)
            self.assertEqual(out["status"], "DIRECT_ADEQUACY_ROUTE_MATCHED")
            self.assertFalse((root / "canonical/tmp/result.json").exists())

    def test_source_mutation_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_bundle(root)
            fact_path = root / "canonical/tmp/facts.json"
            original = direct.producer.compute
            calls = {"n": 0}
            def mutating(case, *, repo_root):
                calls["n"] += 1
                out = original(case, repo_root=repo_root)
                if calls["n"] == 2:
                    fact_path.write_text(
                        '{"schema_id":"FINANCE_TYPED_CONTEXT_V1","fields":'
                        '{"exposure_amount":{"type":"DECIMAL_STRING","value":"999.00"}}}',
                        encoding="utf-8",
                    )
                return out
            direct.producer.compute = mutating
            try:
                out = direct.run({"task_id": "g", "goal": goal()}, repo_root=root)
            finally:
                direct.producer.compute = original
            self.assertFalse(out["pass"])
            self.assertIn("SOURCE_MUTATED_BY_PRODUCER", out["reason"])

    def test_v4_matched_and_fallback(self):
        fake_v3 = types.ModuleType("canonical.runtime.r2_direct_end_to_end_adequacy_v3")
        fake_v3.ROUTES = {"sentinel": {"capability_id": "old"}}
        fake_v3.preflight = lambda request, repo_root=None: {"matched": False, "sentinel": "preflight"}
        fake_v3.run = lambda request, repo_root=None: {"matched": False, "sentinel": "run"}
        sys.modules["canonical.runtime.r2_direct_end_to_end_adequacy_v3"] = fake_v3
        sys.modules.pop("canonical.runtime.r2_direct_end_to_end_adequacy_v4", None)
        v4 = importlib.import_module("canonical.runtime.r2_direct_end_to_end_adequacy_v4")

        self.assertEqual(
            v4.preflight({"task_id": "z", "goal": "unrelated"}, repo_root="."),
            {"matched": False, "sentinel": "preflight"},
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_bundle(root)
            out = v4.run({"task_id": "h", "goal": goal()}, repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["route_id"], direct.ROUTE_ID)

    def test_fixed_point_step_zero_reaches_v4_route(self):
        # Stub only machinery that is downstream of a successful direct match.
        fake_controller = types.ModuleType("canonical.runtime.general_adequate_decision_controller_v1")
        def forbidden_controller(*args, **kwargs):
            raise AssertionError("controller should not run after direct step-zero closure")
        fake_controller.run = forbidden_controller
        sys.modules["canonical.runtime.general_adequate_decision_controller_v1"] = fake_controller

        for name in (
            "canonical.runtime.r2_existing_policy_adequacy_repair_v1",
            "canonical.runtime.r2_basis_discriminator_repair_v1",
        ):
            mod = types.ModuleType(name)
            mod.repair = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("repair should not run after direct step-zero closure")
            )
            sys.modules[name] = mod

        sys.modules.pop("canonical.runtime.general_adequate_decision_fixed_point_v2", None)
        fixed = importlib.import_module("canonical.runtime.general_adequate_decision_fixed_point_v2")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_bundle(root)
            out = fixed.run({"task_id": "i", "goal": goal()}, repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["route_id"], direct.ROUTE_ID)
            self.assertEqual(out["r2_fixed_point_status"], "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED")
            self.assertEqual(out["r2_fixed_point_steps"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
