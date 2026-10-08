from __future__ import annotations

import hashlib
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def verify_exact_blobs() -> None:
    expected = json.loads((ROOT / "EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))
    failures = []
    for rel, want in sorted(expected["files"].items()):
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"MISSING:{rel}")
            continue
        got = git_blob_sha(path.read_bytes())
        if got != want:
            failures.append(f"DRIFT:{rel}:{got}:{want}")
    if failures:
        raise SystemExit("EXACT_BLOB_BINDING_FAILED\n" + "\n".join(failures))
    print(f"EXACT_BLOB_BINDING_PASS={len(expected['files'])}")


def module(name: str, **attrs):
    m = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(m, key, value)
    sys.modules[name] = m
    return m


def install_non_load_bearing_import_stubs() -> None:
    # These modules are imported by the copied Brain files but their behavior is
    # outside this capsule's proof. The tested path never invokes them. Exact
    # load-bearing source files remain copied and hash-bound above.
    module(
        "canonical.runtime.capability_first_scheduler_v1",
        update_pareto_frontier=lambda *args, **kwargs: {
            "active_capability_ids": [],
            "pareto_frontier": [],
        },
    )

    class ExecutableSkillProgramError(ValueError):
        pass

    def program_digest(*, steps, preconditions, postconditions, invalidators):
        payload = {
            "steps": steps,
            "preconditions": preconditions,
            "postconditions": postconditions,
            "invalidators": invalidators,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    module(
        "canonical.runtime.executable_skill_program_v7",
        ExecutableSkillProgramError=ExecutableSkillProgramError,
        induce_candidate=lambda *args, **kwargs: None,
        program_digest=program_digest,
    )
    module(
        "canonical.runtime.executable_skill_verification_authenticator_v1",
        authenticate_and_verify=lambda *args, **kwargs: None,
        reauthenticate_record=lambda *args, **kwargs: {"pass": False},
    )
    module(
        "canonical.runtime.universal_solver_episode_verification_authenticator_v1",
        authenticate=lambda *args, **kwargs: None,
        reauthenticate_record=lambda *args, **kwargs: {"pass": False},
    )
    module(
        "canonical.runtime.universal_verified_adaptive_solver_v12",
        run=lambda *args, **kwargs: {"pass": False, "status": "STUB_NOT_LOAD_BEARING"},
    )
    module(
        "canonical.runtime.raw_goal_archive_acceptance_v1",
        CAPABILITY="raw.goal.archive.acceptance.stub",
    )
    module(
        "canonical.runtime.r3_independent_learning_verifier_v1",
        verify_episode_request=lambda *args, **kwargs: None,
        verify_skill_request=lambda *args, **kwargs: None,
    )


def run() -> int:
    verify_exact_blobs()
    sys.path.insert(0, str(ROOT))
    install_non_load_bearing_import_stubs()

    from canonical.tests import test_r3_root1_adapter_gap_witness_v1 as witness_tests
    from canonical.tests import test_r3_root1_adapter_gap_driver_v1 as driver_tests

    suite = unittest.TestSuite()
    loader = unittest.defaultTestLoader
    suite.addTests(loader.loadTestsFromModule(witness_tests))
    suite.addTests(loader.loadTestsFromModule(driver_tests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"FOCUSED_TESTS_RUN={result.testsRun}")
    print(f"FOCUSED_FAILURES={len(result.failures)}")
    print(f"FOCUSED_ERRORS={len(result.errors)}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(run())
