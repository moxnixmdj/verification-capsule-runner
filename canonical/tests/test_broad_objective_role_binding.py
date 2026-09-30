#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
DECOMP=ROOT/"canonical/runtime/bound_capabilities/broad_objective_decompose.py"
INTEGRATION=ROOT/"canonical/tests/test_broad_objective_source_provenance_runtime.py"

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class BroadRoleShapeQualification(unittest.TestCase):
    def test_generic_broad_objective_emits_source_discovery_first_without_recipe(self):
        m=load(DECOMP,"broad_objective_decompose_qualification")
        objective="Assess whether an unfamiliar engineering claim remains valid under a changed operating condition"
        result=m.decompose(objective)
        self.assertEqual(result["status"],"DECOMPOSED",result)
        self.assertEqual(result["objective"],objective)
        self.assertEqual(result["roles"][0]["role"],"SOURCE_DISCOVERY")
        self.assertEqual(result["roles"][0]["status"],"REQUIRES_GROUNDING")
        self.assertEqual(result["invented_source_urls"],[])
        self.assertEqual(result["task_specific_literals_added"],[])
        self.assertEqual(result["model_dependency_count"],0)

if __name__=="__main__":
    integration=load(INTEGRATION,"broad_source_provenance_integration_tests")
    suite=unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(BroadRoleShapeQualification))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(integration))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
