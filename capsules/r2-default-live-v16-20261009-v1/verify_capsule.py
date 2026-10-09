#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, py_compile, re, sys, types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / "CAPSULE_MANIFEST.json").read_text(encoding="utf-8"))

def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest()

for rel, expected in MANIFEST["exact_files"].items():
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit("MISSING_EXACT_FILE:" + rel)
    observed = blob_sha(path)
    if observed != expected:
        raise SystemExit("BLOB_MISMATCH:" + rel + ":" + observed + "!=" + expected)

sys.path.insert(0, str(ROOT))
import canonical.runtime as runtime_pkg

def install_stub(short: str, attrs: dict):
    full = "canonical.runtime." + short
    module = types.ModuleType(full)
    for k, v in attrs.items():
        setattr(module, k, v)
    sys.modules[full] = module
    setattr(runtime_pkg, short, module)

install_stub("raw_goal_archive_acceptance_v1", {"GRAMMAR": re.compile(r"(?!)")})
install_stub("raw_goal_exact_literal_acceptance_v1", {"preflight": lambda goal: {"matched": False}})
install_stub("raw_goal_literal_json_acceptance_v1", {"preflight": lambda goal: {"matched": False}})
install_stub("r2_direct_end_to_end_adequacy_v1", {"run": lambda request: {"pass": False, "status": "STUB_NOT_EXECUTED"}})

from canonical.runtime import r2_direct_route_registry_v1 as router
from canonical.runtime import r2_direct_route_live_integration_closure_v3 as closure

registry = router.load_registry(repo_root=ROOT)
if registry["route_count"] != 36 or len(registry["routes"]) != 36:
    raise SystemExit("REGISTRY_COUNT_NOT_36")
ordered = sorted(registry["routes"], key=lambda row: row["priority"])
expected_top = [
    "DIRECT_ADEQUACY::CROSS_DOCUMENT_NATURAL_EFFECT_LATTICE_V3",
    "DIRECT_ADEQUACY::FINANCE_BOUNDED_COREFERENCE_AMBIGUITY_CONTROL_V1",
    "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_FIELD_LATTICE_V2",
    "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V1",
    "DIRECT_ADEQUACY::CROSS_DOCUMENT_SOURCE_RESIDUAL_FRONTIER_V1",
    "DIRECT_ADEQUACY::CROSS_DOCUMENT_RESIDUAL_EFFECT_FRONTIER_V1",
    "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_WORLDSET_V1",
    "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_COMPOSITION_V1",
]
if [row["route_id"] for row in ordered[:8]] != expected_top:
    raise SystemExit("V16_PRECEDENCE_MISMATCH")
barriers = {row["route_id"]: row.get("semantic_open_stops_fallback") for row in ordered[:8]}
for rid in [expected_top[0], expected_top[2], expected_top[3], expected_top[4], expected_top[5], expected_top[6]]:
    if barriers.get(rid) is not True:
        raise SystemExit("SEMANTIC_OPEN_BARRIER_MISSING:" + rid)
if barriers.get(expected_top[1]) is not False or barriers.get(expected_top[7]) is not False:
    raise SystemExit("UNEXPECTED_SEMANTIC_OPEN_BARRIER")

state = router.effective_state(repo_root=ROOT)
if state["baseline_activation_route_count"] != 36:
    raise SystemExit("BASELINE_COUNT_NOT_36")
if state["deployable_route_count"] != 36:
    raise SystemExit("DEPLOYABLE_COUNT_NOT_36")
if state["legacy_selection_metadata_count"] != 36:
    raise SystemExit("METADATA_COUNT_NOT_36")
if state["dynamic_admission_route_count"] != 0:
    raise SystemExit("DYNAMIC_ADMISSION_NOT_EMPTY")
if state["stale_selection_metadata_route_ids"]:
    raise SystemExit("STALE_SELECTION_METADATA")

gate = closure.evaluate(repo_root=ROOT)
if gate.get("pass") is not True:
    raise SystemExit("CLOSURE_GATE_FAILED:" + json.dumps(gate, sort_keys=True))

natural = {
    "route_id": expected_top[0],
    "selection_class": router.LEGACY_SELECTION_CLASS,
    "priority": 0,
    "semantic_open_stops_fallback": True,
}
coref = {
    "route_id": expected_top[1],
    "selection_class": router.LEGACY_SELECTION_CLASS,
    "priority": 1,
    "semantic_open_stops_fallback": False,
}
fake_state = dict(state)
fake_state["rows"] = [natural, coref]
calls = []
old_effective, old_pf = router.effective_state, router._preflight_row
try:
    router.effective_state = lambda **kwargs: fake_state
    def fake_pf(row, request, repo_root):
        calls.append(row["route_id"])
        if row["route_id"] == expected_top[0]:
            return {
                "matched": False,
                "direct_route_semantic_open": True,
                "status": "OPEN__NATURAL_EFFECT_LATTICE_TOP",
                "route_id": expected_top[0],
            }
        return {"matched": True, "route_id": expected_top[1]}
    router._preflight_row = fake_pf
    out = router.preflight({"task_id": "capsule", "goal": "bounded natural effect test"}, repo_root=ROOT)
finally:
    router.effective_state, router._preflight_row = old_effective, old_pf
if out.get("direct_route_semantic_open") is not True or out.get("route_id") != expected_top[0]:
    raise SystemExit("SEMANTIC_OPEN_DID_NOT_STOP_FALLBACK")
if calls != [expected_top[0]]:
    raise SystemExit("SEMANTIC_OPEN_EVALUATED_LATER_ROUTE")

for rel in [
    "canonical/runtime/r2_direct_route_registry_v1.py",
    "canonical/runtime/r2_direct_route_dynamic_admission_v1.py",
    "canonical/runtime/promote_r2_direct_route_v1.py",
    "canonical/runtime/r2_direct_route_live_integration_closure_v3.py",
    "canonical/runtime/general_adequate_decision_fixed_point_v2.py",
]:
    py_compile.compile(str(ROOT / rel), doraise=True)

print(json.dumps({
    "status": "PASS__R2_DEFAULT_LIVE_V16_PUBLIC_CAPSULE",
    "source_head_sha": MANIFEST["source_head_sha"],
    "exact_file_count": MANIFEST["exact_file_count"],
    "route_count": state["deployable_route_count"],
    "verified_deployable_equals_default_executable": gate["verified_deployable_equals_default_executable"],
    "semantic_open_barrier_replay": True,
    "version_chain_import_live": gate["version_chain_import_live"],
    "terminal_authority": False,
}, sort_keys=True))
