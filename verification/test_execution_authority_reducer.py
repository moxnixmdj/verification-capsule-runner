import copy

from execution_authority_reducer import canonical_event_hash, derive_authority


BASE = [
    ("STAGE_A_PASS", "stage-a"),
    ("STAGE_B_PASS", "stage-b"),
    ("SOURCE_BOUNDARY_PASS", "source"),
    ("EXECUTION_SURFACE_PASS", "surface"),
    ("ACCEPTANCE_FROZEN", "acceptance"),
    ("MINIMUM_REALITY_CUT_PASS", "minimum-cut"),
    ("RUNTIME_API_PREFLIGHT_PASS", "runtime-api"),
    ("LEASE_ISSUED", "lease"),
]


def make(raw):
    out=[]
    prev=None
    for seq,(typ,evidence) in enumerate(raw):
        e={
            "schema":"BRAIN_AUTHORITY_EVENT_V1",
            "task":"t",
            "seq":seq,
            "event_id":f"E{seq}",
            "type":typ,
            "evidence":evidence,
            "prev_event_sha256":prev,
        }
        e["event_sha256"]=canonical_event_hash(e)
        prev=e["event_sha256"]
        out.append(e)
    return out


def chain(carrier):
    return make(BASE + [("CARRIER_OPEN", carrier)])


def append(events, typ, evidence):
    out=copy.deepcopy(events)
    e={
        "schema":"BRAIN_AUTHORITY_EVENT_V1",
        "task":"t",
        "seq":len(out),
        "event_id":f"E{len(out)}",
        "type":typ,
        "evidence":evidence,
        "prev_event_sha256":out[-1]["event_sha256"] if out else None,
    }
    e["event_sha256"]=canonical_event_hash(e)
    out.append(e)
    return out


def derive(events):
    return derive_authority(events,task="t",execution_budget=1,verifier_budget=1)


def test_full_prerequisite_chain_can_execute():
    out=derive(chain({"pr":425,"head":"aaa"}))
    assert out["valid"] is True
    assert out["can_execute"] is True
    assert out["can_verify"] is False


def test_exact_carrier_identity_changes_authority_hash():
    a=derive(chain({"pr":425,"head":"aaa"}))
    b=derive(chain({"pr":427,"head":"bbb"}))
    assert a["valid"] and b["valid"]
    assert a["active_carrier_binding_sha256"] != b["active_carrier_binding_sha256"]
    assert a["state_sha256"] != b["state_sha256"]


def test_second_open_carrier_without_close_fails_closed():
    out=derive(append(chain({"pr":425}),"CARRIER_OPEN",{"pr":427}))
    assert out["valid"] is False
    assert any(x.startswith("SECOND_CARRIER_OPEN_WITHOUT_CLOSE") for x in out["errors"])


def test_missing_acceptance_freeze_blocks_lease_and_execution():
    raw=[x for x in BASE if x[0]!="ACCEPTANCE_FROZEN"]+[("CARRIER_OPEN",{"pr":1})]
    out=derive(make(raw))
    assert out["valid"] is False
    assert any(x.startswith("LEASE_ISSUED_BEFORE_ALL_PREREQS") for x in out["errors"])
    assert out["can_execute"] is False


def test_missing_minimum_reality_cut_blocks_execution():
    raw=[x for x in BASE if x[0]!="MINIMUM_REALITY_CUT_PASS"]+[("CARRIER_OPEN",{"pr":1})]
    out=derive(make(raw))
    assert out["valid"] is False
    assert out["can_execute"] is False


def test_missing_runtime_api_preflight_blocks_execution():
    raw=[x for x in BASE if x[0]!="RUNTIME_API_PREFLIGHT_PASS"]+[("CARRIER_OPEN",{"pr":1})]
    out=derive(make(raw))
    assert out["valid"] is False
    assert out["can_execute"] is False


def test_execution_consumed_requires_authority_at_transition():
    raw=[
        ("STAGE_A_PASS","a"),
        ("STAGE_B_PASS","b"),
        ("CARRIER_OPEN",{"pr":1}),
        ("EXECUTION_CONSUMED",{"run":1}),
        ("SOURCE_BOUNDARY_PASS","source"),
        ("EXECUTION_SURFACE_PASS","surface"),
        ("ACCEPTANCE_FROZEN","acceptance"),
        ("MINIMUM_REALITY_CUT_PASS","cut"),
        ("RUNTIME_API_PREFLIGHT_PASS","api"),
        ("LEASE_ISSUED","lease"),
    ]
    out=derive(make(raw))
    assert out["valid"] is False
    assert any(x.startswith("CARRIER_OPEN_WITHOUT_LIVE_LEASE") for x in out["errors"]) or any(
        x.startswith("EXECUTION_CONSUMED_WITHOUT_DERIVED_AUTHORITY") for x in out["errors"]
    )


def test_execution_then_semantic_success_and_output_freeze_enables_verifier():
    events=append(chain({"pr":425}),"EXECUTION_CONSUMED",{"run":1})
    mid=derive(events)
    assert mid["valid"] is True
    assert mid["can_execute"] is False
    assert mid["can_verify"] is False
    events=append(events,"BUILDER_SEMANTIC_SUCCESS",{"sentinel":"PASS"})
    assert derive(events)["can_verify"] is False
    events=append(events,"OUTPUT_FROZEN",{"sha256":"d"*64})
    out=derive(events)
    assert out["valid"] is True
    assert out["can_verify"] is True


def test_exit_zero_without_semantic_success_cannot_verify():
    events=append(chain({"pr":425}),"EXECUTION_CONSUMED",{"exit_code":0})
    events=append(events,"OUTPUT_FROZEN",{"sha256":"d"*64})
    out=derive(events)
    assert out["valid"] is False
    assert out["can_verify"] is False
    assert any(x.startswith("OUTPUT_FROZEN_BEFORE_SEMANTIC_SUCCESS") for x in out["errors"])


def test_verifier_consumed_before_output_freeze_is_invalid():
    events=append(chain({"pr":425}),"EXECUTION_CONSUMED",{"run":1})
    events=append(events,"BUILDER_SEMANTIC_SUCCESS",{"sentinel":"PASS"})
    events=append(events,"VERIFIER_CONSUMED",{"run":2})
    out=derive(events)
    assert out["valid"] is False
    assert any(x.startswith("VERIFIER_CONSUMED_WITHOUT_DERIVED_AUTHORITY") for x in out["errors"])


def test_task_taint_is_irreversible_for_authority():
    events=append(chain({"pr":425}),"TASK_TAINTED",{"reason":"external-search"})
    events=append(events,"SOURCE_BOUNDARY_PASS",{"new":"claim"})
    events=append(events,"LEASE_ISSUED",{"new":"lease"})
    out=derive(events)
    assert out["valid"] is False or out["can_execute"] is False
    if out["valid"]:
        assert out["state"]["tainted"] is True
        assert out["can_execute"] is False


def test_budget_consumption_is_transition_checked():
    events=append(chain({"pr":425}),"EXECUTION_CONSUMED",{"run":1})
    events=append(events,"EXECUTION_CONSUMED",{"run":2})
    out=derive(events)
    assert out["valid"] is False
    assert any(x.startswith("EXECUTION_CONSUMED_WITHOUT_DERIVED_AUTHORITY") for x in out["errors"])


def test_revocation_and_close_remove_all_authority():
    events=append(chain({"pr":425}),"EXECUTION_CONSUMED",{"run":1})
    events=append(events,"BUILDER_SEMANTIC_SUCCESS",{"sentinel":"PASS"})
    events=append(events,"OUTPUT_FROZEN",{"sha256":"d"*64})
    events=append(events,"LEASE_REVOKED","failure")
    events=append(events,"CARRIER_CLOSED",{"pr":425})
    out=derive(events)
    assert out["valid"] is True
    assert out["can_execute"] is False
    assert out["can_verify"] is False
    assert out["state"]["execution_used"] == 1
    assert out["state"]["active_carrier_binding_sha256"] is None
