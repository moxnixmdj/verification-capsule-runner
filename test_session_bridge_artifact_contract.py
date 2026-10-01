import session_bridge.controller_fast as c


def test_plain_string_artifact_supported():
    normalized, unsupported = c.normalize_artifact_contract(["/app/output.json"])
    assert normalized == [{"source":"/app/output.json","destination":"/app/output.json","service":None}]
    assert unsupported == []


def test_structured_local_artifact_supported():
    normalized, unsupported = c.normalize_artifact_contract([
        {"source":"/app/out.json","destination":"/results/out.json"}
    ])
    assert normalized == [{"source":"/app/out.json","destination":"/results/out.json","service":None}]
    assert unsupported == []


def test_per_service_artifact_fails_closed():
    normalized, unsupported = c.normalize_artifact_contract([
        {"source":"/var/lib/state.json","service":"api"}
    ])
    assert normalized == []
    assert unsupported[0]["reason"] == "PER_SERVICE_ARTIFACT_REQUIRES_MULTI_SERVICE_COLLECTOR"
    assert unsupported[0]["service"] == "api"


def test_exclude_filter_fails_closed():
    normalized, unsupported = c.normalize_artifact_contract([
        {"source":"/app/out","exclude":["*.tmp"]}
    ])
    assert normalized == []
    assert unsupported[0]["reason"] == "ARTIFACT_EXCLUDE_FILTER_UNSUPPORTED"
