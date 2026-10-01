from types import SimpleNamespace

import session_bridge.controller as c


def _cp(returncode=0, stderr=""):
    return SimpleNamespace(returncode=returncode, stdout="", stderr=stderr)


def test_stage_unique_same_basename(monkeypatch):
    c.CONFIG = {"artifact_fallback_roots": ["/app", "/workspace"]}
    calls = []
    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[:5] == ["docker", "exec", "brain-bridge-task", "test", "-e"]:
            return _cp(1)
        if cmd[:5] == ["docker", "exec", "brain-bridge-task", "test", "-f"]:
            return _cp(0 if cmd[-1] == "/app/output.json" else 1)
        if cmd[:4] == ["docker", "exec", "brain-bridge-task", "/bin/sh"]:
            return _cp(0)
        raise AssertionError(cmd)
    monkeypatch.setattr(c, "run", fake_run)
    out = c.stage_missing_artifacts(["/results/output.json"])
    assert out == {"staged": [{"source": "/app/output.json", "required": "/results/output.json"}], "unresolved": []}


def test_stage_refuses_ambiguous_candidates(monkeypatch):
    c.CONFIG = {"artifact_fallback_roots": ["/app", "/workspace"]}
    def fake_run(cmd, **kwargs):
        if cmd[:5] == ["docker", "exec", "brain-bridge-task", "test", "-e"]:
            return _cp(1)
        if cmd[:5] == ["docker", "exec", "brain-bridge-task", "test", "-f"]:
            return _cp(0)
        if cmd[:4] == ["docker", "exec", "brain-bridge-task", "/bin/sh"]:
            raise AssertionError("ambiguous artifacts must not be copied")
        raise AssertionError(cmd)
    monkeypatch.setattr(c, "run", fake_run)
    out = c.stage_missing_artifacts(["/results/output.json"])
    assert out["staged"] == []
    assert out["unresolved"] == [{"required": "/results/output.json", "candidates": ["/app/output.json", "/workspace/output.json"]}]
