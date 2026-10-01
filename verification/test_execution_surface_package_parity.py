import unittest
from execution_surface_package_parity import assess_surface_parity

def base():
    return {
        "os_image": "ubuntu-24.04-task-image",
        "architecture": "x86_64",
        "python_provenance": "debian-managed-python-3.12",
        "environment_management_policy": "externally-managed",
        "package_install_policy": "venv-required",
        "pep668_externally_managed": True,
        "required_native_libraries": ["ffmpeg"],
        "available_native_libraries": ["ffmpeg", "libsndfile"],
    }

class SurfaceParityTests(unittest.TestCase):
    def test_exact_surface_passes(self):
        self.assertTrue(assess_surface_parity(base(),base())["pass"])

    def test_rank19_setup_python_vs_debian_pep668_fails(self):
        pre=base()
        pre["python_provenance"]="actions-setup-python-cpython-3.12"
        pre["environment_management_policy"]="unmanaged"
        pre["package_install_policy"]="system-pip-allowed"
        pre["pep668_externally_managed"]=False
        out=assess_surface_parity(pre,base())
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("python_provenance:") for x in out["mismatches"]))
        self.assertTrue(any(x.startswith("environment_management_policy:") for x in out["mismatches"]))
        self.assertTrue(any(x.startswith("package_install_policy:") for x in out["mismatches"]))
        self.assertTrue(any(x.startswith("pep668_externally_managed:") for x in out["mismatches"]))

    def test_unknown_policy_fails_closed(self):
        pre=base(); pre["package_install_policy"]="unknown"
        out=assess_surface_parity(pre,base())
        self.assertFalse(out["pass"])
        self.assertIn("package_install_policy",out["unknown"])

    def test_missing_native_library_fails(self):
        pre=base(); pre["available_native_libraries"]=[]
        out=assess_surface_parity(pre,base())
        self.assertFalse(out["pass"])
        self.assertIn("missing_native_libraries:ffmpeg",out["mismatches"])

if __name__=="__main__":
    unittest.main(verbosity=2)
