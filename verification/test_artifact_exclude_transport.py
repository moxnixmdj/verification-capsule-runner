import subprocess
import unittest

from session_bridge import controller


class ArtifactContractUnitTests(unittest.TestCase):
    def test_structured_excludes_are_accepted(self):
        normalized, unsupported = controller.normalize_artifact_contract([{
            "source": "/workspace/generated_app",
            "destination": "/workspace/generated_app",
            "exclude": ["node_modules", ".venv", "__pycache__", "*.pyc"],
        }])
        self.assertEqual(unsupported, [])
        self.assertEqual(normalized[0]["exclude"], ["node_modules", ".venv", "__pycache__", "*.pyc"])

    def test_absolute_exclude_fails_closed(self):
        normalized, unsupported = controller.normalize_artifact_contract([{
            "source": "/workspace/generated_app",
            "exclude": ["/etc"],
        }])
        self.assertEqual(normalized, [])
        self.assertEqual(unsupported[0]["reason"], "ARTIFACT_EXCLUDE_PATTERN_MUST_BE_RELATIVE")

    def test_parent_traversal_exclude_fails_closed(self):
        normalized, unsupported = controller.normalize_artifact_contract([{
            "source": "/workspace/generated_app",
            "exclude": ["../secret"],
        }])
        self.assertEqual(normalized, [])
        self.assertEqual(unsupported[0]["reason"], "ARTIFACT_EXCLUDE_PATTERN_MUST_BE_RELATIVE")

    def test_service_artifact_remains_fail_closed(self):
        normalized, unsupported = controller.normalize_artifact_contract([{
            "source": "/workspace/generated_app",
            "service": "frontend",
        }])
        self.assertEqual(normalized, [])
        self.assertEqual(unsupported[0]["reason"], "PER_SERVICE_ARTIFACT_REQUIRES_MULTI_SERVICE_COLLECTOR")


class ArtifactTransportDockerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["docker","rm","-f","brain-bridge-task","brain-artifact-target"],check=False,capture_output=True)
        subprocess.run([
            "docker","run","-d","--name","brain-bridge-task","python:3.12-slim",
            "sh","-lc","trap : TERM INT; while :; do sleep 3600; done"
        ],check=True,capture_output=True,text=True)
        subprocess.run([
            "docker","run","-d","--name","brain-artifact-target","python:3.12-slim",
            "sh","-lc","trap : TERM INT; while :; do sleep 3600; done"
        ],check=True,capture_output=True,text=True)
        setup = r"""
mkdir -p /workspace/generated_app/src/__pycache__          /workspace/generated_app/node_modules/pkg          /workspace/generated_app/.venv/bin          /workspace/generated_app/nested/cache
printf keep >/workspace/generated_app/src/main.py
printf pyc >/workspace/generated_app/src/__pycache__/main.pyc
printf dep >/workspace/generated_app/node_modules/pkg/index.js
printf venv >/workspace/generated_app/.venv/bin/python
printf data >/workspace/generated_app/nested/cache/data.txt
"""
        subprocess.run(["docker","exec","brain-bridge-task","sh","-lc",setup],check=True)

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["docker","rm","-f","brain-bridge-task","brain-artifact-target"],check=False,capture_output=True)

    def test_directory_transfer_honors_excludes(self):
        entry = {
            "source": "/workspace/generated_app",
            "destination": "/workspace/generated_app",
            "exclude": ["node_modules", ".venv", "__pycache__", "*.pyc"],
        }
        self.assertTrue(controller.stream_artifact(entry, "brain-artifact-target"))
        def exists(path):
            cp=subprocess.run(["docker","exec","brain-artifact-target","test","-e",path])
            return cp.returncode==0
        self.assertTrue(exists("/workspace/generated_app/src/main.py"))
        self.assertTrue(exists("/workspace/generated_app/nested/cache/data.txt"))
        self.assertFalse(exists("/workspace/generated_app/node_modules"))
        self.assertFalse(exists("/workspace/generated_app/.venv"))
        self.assertFalse(exists("/workspace/generated_app/src/__pycache__"))
        self.assertFalse(exists("/workspace/generated_app/src/__pycache__/main.pyc"))

    def test_destination_remap_preserves_tree(self):
        entry = {
            "source": "/workspace/generated_app",
            "destination": "/opt/copied_app",
            "exclude": ["node_modules", ".venv", "__pycache__", "*.pyc"],
        }
        self.assertTrue(controller.stream_artifact(entry, "brain-artifact-target"))
        cp=subprocess.run(["docker","exec","brain-artifact-target","cat","/opt/copied_app/src/main.py"],capture_output=True,text=True)
        self.assertEqual(cp.returncode,0)
        self.assertEqual(cp.stdout,"keep")


if __name__ == "__main__":
    unittest.main()
