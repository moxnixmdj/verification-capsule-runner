#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = "execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V2.json"
EFFECTIVE = "execution_guard/TB_SCIENCE_RANK20_EXECUTION_BEHAVIOR_V4.json"
CLAIM = "capsules/tb_science_rank20_20261010_v1/RANK20_LOGICAL_ATTEMPT_CLAIM_BINDING_V5.json"
WORKFLOW = ".github/workflows/execute-tb-science-rank20-20261010-v1.yml"
SEED_SHA = "dc20b4ef740eaeb6741c834d9c74634653c69193"
EFFECTIVE_SHA = "d7776d18a2f75b5b974299e2985eee0f4ec0878d"
CLAIM_SHA = "7d94ac0b86053a31fd711dcb0652370041671e44"
WORKFLOW_SHA = "e4cb372e501790fd9ed5aa72193d18109a599102"
ZERO_SHA = "ba2d467c54a9f9720bc1b647befe655b80555fab"
PREFLIGHT_SHA = "74d55719d01f3f434b0b75001548f56a4ed83ff6"
START_CAS_SHA = "35cd4c7a31d5ffbafa755dcdf888c2dee1beeb1b"
EXPECTED_CHANGED_BINDINGS = {
    "zero_exposure_tests",
    "preflight",
    "start_cas",
    "logical_attempt_claim_binding",
}

def blob(rel: str) -> str:
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def main() -> int:
    assert blob(SEED) == SEED_SHA
    assert blob(EFFECTIVE) == EFFECTIVE_SHA
    assert blob(CLAIM) == CLAIM_SHA
    assert blob(WORKFLOW) == WORKFLOW_SHA

    seed = load(SEED)
    effective = load(EFFECTIVE)
    claim = load(CLAIM)

    for key in ("date", "scope", "slot_id", "task_digest", "workflow_path", "behavior"):
        assert effective[key] == seed[key], key
    assert effective["behavior"] == seed["behavior"]
    assert effective["execution_authority"] == seed["execution_authority"]
    assert effective["promotion_authority"] == seed["promotion_authority"]
    assert effective["acceptance_credit_delta"] == seed["acceptance_credit_delta"]
    assert effective["terminal_credit_delta"] == seed["terminal_credit_delta"]

    old = seed["runtime_bindings"]
    new = effective["runtime_bindings"]
    assert set(old) == set(new)
    changed = {key for key in old if old[key] != new[key]}
    assert changed == EXPECTED_CHANGED_BINDINGS, changed

    assert new["zero_exposure_tests"]["git_blob_sha"] == ZERO_SHA
    assert blob(new["zero_exposure_tests"]["path"]) == ZERO_SHA
    assert new["preflight"]["git_blob_sha"] == PREFLIGHT_SHA
    assert blob(new["preflight"]["path"]) == PREFLIGHT_SHA
    assert new["start_cas"]["git_blob_sha"] == START_CAS_SHA
    assert blob(new["start_cas"]["path"]) == START_CAS_SHA
    assert new["logical_attempt_claim_binding"] == {
        "path": CLAIM,
        "git_blob_sha": CLAIM_SHA,
    }

    assert claim["workflow_blob"] == WORKFLOW_SHA
    assert claim["behavior_blob"] == SEED_SHA
    assert claim["zero_exposure_test_blob"] == ZERO_SHA
    assert claim["execution_branch"] == "execute/tb-science-rank20-20261010-v2"
    assert claim["activation_filename"] == "ACTIVATE_RANK20_V2_PR.json"

    workflow = (ROOT / WORKFLOW).read_text(encoding="utf-8")
    assert "GITHUB_WORKSPACE" in workflow and "PYTHONPATH" in workflow
    assert "execute/tb-science-rank20-20261010-v2" in workflow
    assert "ACTIVATE_RANK20_V2_PR.json" in workflow

    print("PASS__RANK20_V5_EFFECTIVE_BEHAVIOR_STRICT_REFINEMENT__ZERO_EXPOSURE")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
