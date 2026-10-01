import unittest
from session_bridge.execution_surface import classify_python_package_policy


class PackagePolicyTests(unittest.TestCase):
    def test_pep668_requires_venv_when_usable(self):
        p={"python":{"present":True,"externally_managed":True,"pip_available":True,"venv_usable":True}}
        self.assertEqual(classify_python_package_policy(p),"VENV_REQUIRED")

    def test_pep668_without_venv_fails_safe(self):
        p={"python":{"present":True,"externally_managed":True,"pip_available":True,"venv_usable":False}}
        self.assertEqual(classify_python_package_policy(p),"NO_SAFE_PYTHON_INSTALL_ROUTE")

    def test_unmanaged_pip(self):
        p={"python":{"present":True,"externally_managed":False,"pip_available":True,"venv_usable":True}}
        self.assertEqual(classify_python_package_policy(p),"SYSTEM_PIP_ALLOWED_OR_UNMANAGED")

    def test_no_python(self):
        p={"python":{"present":False}}
        self.assertEqual(classify_python_package_policy(p),"PYTHON_UNAVAILABLE")

    def test_venv_only(self):
        p={"python":{"present":True,"externally_managed":False,"pip_available":False,"venv_usable":True}}
        self.assertEqual(classify_python_package_policy(p),"VENV_ONLY")


if __name__=="__main__":
    unittest.main()
