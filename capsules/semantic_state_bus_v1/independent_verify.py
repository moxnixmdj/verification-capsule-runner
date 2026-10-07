from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE
sys.path.insert(0, str(ROOT))

EXPECTED = {
    ROOT / "canonical/runtime/semantic_state_bus_v1.py":
        "fc7d07b48c69168909b063452a1947d7dc27ec0c",
    ROOT / "canonical/tests/test_semantic_state_bus_v1.py":
        "b3a82eb563cea5688cc2ee15056075d8d412b137",
    ROOT / "canonical/governance/SEMANTIC_STATE_BUS_V1.json":
        "1e782299494d80b84c997df7fa6658256ff8a4a5",
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


for path, expected in EXPECTED.items():
    actual = git_blob_sha(path)
    assert actual == expected, (path, actual, expected)

bus = importlib.import_module("canonical.runtime.semantic_state_bus_v1")

# Independent finite falsification family. Vary semantic values while keeping
# object shape fixed. Every decoy must perturb the downstream binding and every
# exact rollback must recover the original state and binding.
for i in range(32):
    state0 = bus.empty_state(
        case_id=f"CASE-{i}",
        base_context_sha256=hashlib.sha256(f"base-{i}".encode()).hexdigest(),
    )
    true_value = {
        "record_id": f"R-{i}",
        "status": "approved" if i % 2 == 0 else "pending",
        "count": i,
    }
    state1, _ = bus.write(
        state0,
        key="semantic",
        value=true_value,
        semantic_type="SEMANTIC_RECORD",
        producer_stage="producer",
        provenance_sha256=hashlib.sha256(
            f"provenance-{i}".encode()
        ).hexdigest(),
        expected_state_sha256=state0["state_sha256"],
    )
    cp = bus.checkpoint(state1, label="truth")
    task = {"goal": f"consume-{i}"}
    true_ctx = bus.bind_downstream_context(
        state1,
        keys=["semantic"],
        consumer_stage="consumer",
        public_task=task,
    )

    decoy_value = {
        "record_id": f"Q-{i}",
        "status": "rejected" if i % 2 == 0 else "approved",
        "count": i + 1000,
    }
    state2, intervention = bus.intervene_same_shape(
        state1,
        key="semantic",
        decoy_value=decoy_value,
        intervention_stage="independent_falsifier",
        provenance_sha256=hashlib.sha256(
            f"intervention-{i}".encode()
        ).hexdigest(),
        expected_state_sha256=state1["state_sha256"],
    )
    decoy_ctx = bus.bind_downstream_context(
        state2,
        keys=["semantic"],
        consumer_stage="consumer",
        public_task=task,
    )
    assert intervention["true_value_sha256"] != intervention["decoy_value_sha256"]
    assert true_ctx["binding_sha256"] != decoy_ctx["binding_sha256"]

    restored, rb = bus.rollback(
        state2,
        checkpoint_record=cp,
        expected_current_state_sha256=state2["state_sha256"],
    )
    rescue_ctx = bus.bind_downstream_context(
        restored,
        keys=["semantic"],
        consumer_stage="consumer",
        public_task=task,
    )
    assert rb["exact_state_restoration"] is True
    assert restored == state1
    assert rescue_ctx["binding_sha256"] == true_ctx["binding_sha256"]

# Tamper rejection independent of the Brain test suite.
s = bus.empty_state(case_id="TAMPER", base_context_sha256="a" * 64)
s, _ = bus.write(
    s,
    key="x",
    value={"a": 1},
    semantic_type="X",
    producer_stage="producer",
    provenance_sha256="b" * 64,
    expected_state_sha256=s["state_sha256"],
)
s["entries"]["x"]["value"]["a"] = 2
try:
    bus.read(s, keys=["x"], consumer_stage="consumer")
except bus.StateBusError:
    pass
else:
    raise AssertionError("tampered state accepted")

# Cross-case rollback rejection.
a = bus.empty_state(case_id="A", base_context_sha256="c" * 64)
b = bus.empty_state(case_id="B", base_context_sha256="c" * 64)
cp = bus.checkpoint(a, label="A")
try:
    bus.rollback(
        b,
        checkpoint_record=cp,
        expected_current_state_sha256=b["state_sha256"],
    )
except bus.StateBusError:
    pass
else:
    raise AssertionError("cross-case rollback accepted")

print(json.dumps({
    "status": "PASS",
    "exact_blob_count": len(EXPECTED),
    "finite_intervention_cases": 32,
    "terminal_credit": 0
}, sort_keys=True))
