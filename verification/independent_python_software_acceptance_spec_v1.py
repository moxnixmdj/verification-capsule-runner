from __future__ import annotations

import pathlib
import tempfile
import unittest

from canonical.runtime.bound_capabilities.python_software_acceptance_spec_v1 import (
    compile_request,
    verify_acceptance,
)


class IndependentSoftwareAcceptanceSpecV1(unittest.TestCase):
    def make_repo(self):
        td=tempfile.TemporaryDirectory()
        root=pathlib.Path(td.name)
        (root/"pkg").mkdir()
        (root/"tests").mkdir()
        (root/"pkg/core.py").write_text("def value():\n    return 7\n",encoding="utf-8")
        (root/"README.md").write_text("alpha\n",encoding="utf-8")
        (root/"tests/test_core.py").write_text(
            "import unittest\n"
            "from pkg.core import value\n"
            "class T(unittest.TestCase):\n"
            "    def test_value(self): self.assertEqual(value(),7)\n"
            "if __name__=='__main__': unittest.main()\n",
            encoding="utf-8",
        )
        return td,root

    def test_explicit_compile_test_and_text_contract(self):
        td,root=self.make_repo(); self.addCleanup(td.cleanup)
        plan=compile_request(
            'pkg/core.py must compile; tests/test_core.py tests must pass; README.md must contain "alpha"',
            root,
        )
        out=verify_acceptance(plan,root)
        self.assertTrue(plan["all_critical_bound"])
        self.assertTrue(out["pass"])

    def test_unbound_semantic_clause_blocks_even_with_passing_test(self):
        td,root=self.make_repo(); self.addCleanup(td.cleanup)
        plan=compile_request(
            "tests/test_core.py tests must pass; the module should satisfy the unstated product preference",
            root,
        )
        out=verify_acceptance(plan,root)
        self.assertEqual(plan["unbound_predicate_count"],1)
        self.assertFalse(out["pass"])

    def test_path_traversal_reference_is_unbound(self):
        td,root=self.make_repo(); self.addCleanup(td.cleanup)
        plan=compile_request("create file ../outside.py",root)
        self.assertFalse(plan["all_critical_bound"])
        self.assertEqual(plan["predicates"][0]["kind"],"UNSAFE_PATH_REFERENCE")
        self.assertFalse(verify_acceptance(plan,root)["pass"])

    def test_protected_root_file_change_is_detected(self):
        td,root=self.make_repo(); self.addCleanup(td.cleanup)
        plan=compile_request("do not modify README.md",root)
        self.assertTrue(verify_acceptance(plan,root)["pass"])
        (root/"README.md").write_text("beta\n",encoding="utf-8")
        self.assertFalse(verify_acceptance(plan,root)["pass"])

    def test_allowed_scope_change_passes_but_new_outside_file_fails(self):
        td,root=self.make_repo(); self.addCleanup(td.cleanup)
        plan=compile_request("only modify pkg/core.py",root)
        (root/"pkg/core.py").write_text("def value():\n    return 8\n",encoding="utf-8")
        self.assertTrue(verify_acceptance(plan,root)["pass"])
        (root/"notes.txt").write_text("new\n",encoding="utf-8")
        self.assertFalse(verify_acceptance(plan,root)["pass"])

    def test_test_verifier_does_not_leave_python_bytecode(self):
        td,root=self.make_repo(); self.addCleanup(td.cleanup)
        plan=compile_request("tests/test_core.py tests must pass",root)
        self.assertTrue(verify_acceptance(plan,root)["pass"])
        caches=list(root.rglob("__pycache__"))
        self.assertEqual(caches,[])

    def test_two_test_paths_in_one_clause_fail_closed_as_ambiguous(self):
        td,root=self.make_repo(); self.addCleanup(td.cleanup)
        (root/"tests/test_other.py").write_text(
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_ok(self): self.assertTrue(True)\n"
            "if __name__=='__main__': unittest.main()\n",
            encoding="utf-8",
        )
        plan=compile_request(
            "tests/test_core.py and tests/test_other.py tests must pass",
            root,
        )
        self.assertFalse(plan["all_critical_bound"])
        self.assertFalse(verify_acceptance(plan,root)["pass"])

    def test_negative_text_requirement_is_independently_checked(self):
        td,root=self.make_repo(); self.addCleanup(td.cleanup)
        plan=compile_request('README.md must not contain "omega"',root)
        self.assertTrue(verify_acceptance(plan,root)["pass"])
        (root/"README.md").write_text("omega\n",encoding="utf-8")
        self.assertFalse(verify_acceptance(plan,root)["pass"])


if __name__=="__main__":
    unittest.main(verbosity=2)
