from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from canonical.runtime.minimum_terminal_basis_v1 import evaluate

EXPECTED_BRAIN_BLOBS = {
    "canonical/runtime/minimum_terminal_basis_v1.py": "0ec8eb45056cc5835905060b9205408da36247aa",
    "canonical/tests/test_minimum_terminal_basis_v1.py": "99e638cbbd5959797f4bf1d23fe7f9f1351c5534",
    "canonical/governance/MINIMUM_TERMINAL_BASIS_COMPILER_V1.json": "f678350bfeb05b3ece60c767504b599fdee3bc18",
}

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

for rel, expected in EXPECTED_BRAIN_BLOBS.items():
    actual = git_blob_sha(ROOT / rel)
    assert actual == expected, (rel, actual, expected)

gov = json.loads((ROOT / "canonical/governance/MINIMUM_TERMINAL_BASIS_COMPILER_V1.json").read_text())
assert gov["status"] == "IMPLEMENTED_CANDIDATE__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT"
assert gov["capability_credit_delta"] == 0
assert gov["family_credit_delta"] == 0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False

# Stronger single fact must dominate a larger conjunctive basis.
doc = {
    "targets": ["P1", "P2", "P3"],
    "baseline_facts": ["BASE"],
    "candidate_facts": ["STRONG", "A", "B", "C"],
    "implications": [
        {"edge_id":"s","if_all":["STRONG"],"then":["P1","P2","P3"],"verified":True,"independent":True,"receipt":"r://s"},
        {"edge_id":"a","if_all":["A","BASE"],"then":["P1"],"verified":True,"independent":True,"receipt":"r://a"},
        {"edge_id":"b","if_all":["B"],"then":["P2"],"verified":True,"independent":True,"receipt":"r://b"},
        {"edge_id":"c","if_all":["C"],"then":["P3"],"verified":True,"independent":True,"receipt":"r://c"},
    ],
    "terminal_false_worlds": [
        {"world_id":"w1","eliminated_by":["STRONG","A"]},
        {"world_id":"w2","eliminated_by":["STRONG","B"]},
        {"world_id":"w3","eliminated_by":["STRONG","C"]},
    ],
}
out=evaluate(doc)
assert out["status"] == "EXACT_MINIMUM_TERMINAL_BASIS_AND_HITTING_SET_COMPUTED", out
assert out["minimum_generating_bases"] == [["STRONG"]], out
assert out["minimum_false_world_hitting_sets"] == [["STRONG"]], out
assert out["minimum_joint_terminal_cuts"] == [["STRONG"]], out
assert out["capability_credit_delta"] == 0 and out["family_credit_delta"] == 0
assert out["execution_authority"] is False and out["promotion_authority"] is False

# Two incomparable minima must both be returned deterministically.
doc2 = {
    "targets":["T"],
    "baseline_facts":[],
    "candidate_facts":["A","B"],
    "implications":[
        {"edge_id":"ea","if_all":["A"],"then":["T"],"verified":True,"independent":True,"receipt":"r://ea"},
        {"edge_id":"eb","if_all":["B"],"then":["T"],"verified":True,"independent":True,"receipt":"r://eb"},
    ],
    "terminal_false_worlds":[{"world_id":"w","eliminated_by":["A","B"]}],
}
out2=evaluate(doc2)
assert out2["minimum_generating_bases"] == [["A"],["B"]], out2
assert out2["minimum_joint_terminal_cuts"] == [["A"],["B"]], out2

# Fail closed on fake authority.
bad=json.loads(json.dumps(doc))
bad["implications"][0]["independent"]=False
assert evaluate(bad)["status"] == "FAIL_CLOSED"

bad2=json.loads(json.dumps(doc))
bad2["terminal_false_worlds"][0]["eliminated_by"].append("GHOST")
assert evaluate(bad2)["status"] == "FAIL_CLOSED"

# Unreachable targets never become a basis.
unreachable={
    "targets":["NEVER"],
    "baseline_facts":[],
    "candidate_facts":["A"],
    "implications":[],
    "terminal_false_worlds":[],
}
u=evaluate(unreachable)
assert u["status"] == "TERMINAL_BASIS_RESIDUAL_UNSATISFIABLE_WITH_DECLARED_CANDIDATES"
assert u["all_targets_derivable"] is False
assert u["minimum_generating_bases"] == []

print("independent minimum terminal basis verification: PASS")
