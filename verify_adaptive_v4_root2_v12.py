#!/usr/bin/env python3
import json
from pathlib import Path

B=Path("subject/adaptive_v4_root2_v12_20261004_sol")
v3=json.loads((B/"V3.json").read_text())
v4=json.loads((B/"V4.json").read_text())
act=json.loads((B/"V4_ACTIVATION.json").read_text())

assert v4["exact_live_state"]==v3["exact_live_state"]
assert v4["verified_runtime"]==v3["verified_runtime"]
assert v4["optimization"]==v3["optimization"]
assert v4["preserved_search_deletions"]==v3["preserved_search_deletions"]
assert v4["authority_bindings"]["root3"]==v3["authority_bindings"]["root3"]
assert v4["authority_bindings"]["retrieval"]==v3["authority_bindings"]["retrieval"]

r=v4["authority_bindings"]["root2"]
assert r["frontier_git_blob_sha"]=="75ca9127a73ca2dd52a49f2f09e2e0ccc384129a"
assert r["final_activation_git_blob_sha"]=="fdc58167f39de2b27de544c8f957a1e9af4e5c52"

assert v4["execution_authority"] is False
assert v4["promotion_authority"] is False
assert v4["fresh_reality_authority"] is False
assert act["subject"]["policy_git_blob_sha"]=="10aa59870c12b330ca72a2b3e6eac3c41386b2af"
assert act["subject"]["root2_activation_git_blob_sha"]=="fdc58167f39de2b27de544c8f957a1e9af4e5c52"
assert act["authority"]["execution"] is False
assert act["authority"]["promotion"] is False
assert act["authority"]["fresh_reality"] is False

print("PASS adaptive V4 is a Root2 V12 rebind with V3 runtime semantics preserved")
