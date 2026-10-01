import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "session_bridge"))
import controller_fast as c


def test_plain_string_artifact_supported():
    normalized, unsupported = c.normalize_artifact_contract(["/app/output.json"])
    assert normalized == [{"source":"/app/output.json","destination":"/app/output.json","service":None,"exclude":[]}]
    assert unsupported == []


def test_structured_local_artifact_supported():
    normalized, unsupported = c.normalize_artifact_contract([
        {"source":"/app/out.json","destination":"/results/out.json"}
    ])
    assert normalized == [{"source":"/app/out.json","destination":"/results/out.json","service":None,"exclude":[]}]
    assert unsupported == []


def test_per_service_artifact_fails_closed():
    normalized, unsupported = c.normalize_artifact_contract([
        {"source":"/var/lib/state.json","service":"api"}
    ])
    assert normalized == []
    assert unsupported[0]["reason"] == "PER_SERVICE_ARTIFACT_REQUIRES_MULTI_SERVICE_COLLECTOR"
    assert unsupported[0]["service"] == "api"


def test_exclude_filter_is_supported_when_safe_and_relative():
    normalized, unsupported = c.normalize_artifact_contract([
        {"source":"/app/out","exclude":["*.tmp","node_modules"]}
    ])
    assert unsupported == []
    assert normalized == [{
        "source":"/app/out","destination":"/app/out","service":None,
        "exclude":["*.tmp","node_modules"]
    }]


def test_unsafe_exclude_filter_fails_closed():
    normalized, unsupported = c.normalize_artifact_contract([
        {"source":"/app/out","exclude":["../secret"]}
    ])
    assert normalized == []
    assert unsupported[0]["reason"] == "ARTIFACT_EXCLUDE_PATTERN_MUST_BE_RELATIVE"


def test_builder_artifact_postcondition_regression_is_enforced_in_controller_source():
    source = (Path(__file__).resolve().parent / "session_bridge" / "controller_fast.py").read_text()
    assert "REQUIRED_ARTIFACTS_MISSING_AFTER_BUILDER:" in source
    assert '"artifact_poststate": artifact_poststate' in source
    assert '"missing_artifacts": missing_artifacts' in source
    assert '"id": "artifact_contract_postcondition"' in source


def test_rank22_false_success_class_cannot_be_process_exit_only():
    source = (Path(__file__).resolve().parent / "session_bridge" / "controller_fast.py").read_text()
    burst_write = source.index('legacy.write_json(EVIDENCE / f"burst_{next_burst:03d}.json"')
    postcondition = source.index('REQUIRED_ARTIFACTS_MISSING_AFTER_BUILDER:')
    assert postcondition < burst_write
