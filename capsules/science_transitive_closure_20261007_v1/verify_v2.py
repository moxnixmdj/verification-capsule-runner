from __future__ import annotations
import hashlib, importlib, importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED_TOP={
 "canonical/runtime/python_transitive_runtime_closure_v1.py":"43d502c621c219632fa0f9a19632dfc0228e4847",
 "canonical/tests/test_python_transitive_runtime_closure_v1.py":"7f71c5ac0d0dfd64a9ca64861422546d9fec9bb7",
 "canonical/governance/TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261007_V1.json":"4b2a4fb3bd85b066e642a0253d4c325dbb431237",
 "canonical/governance/TB_SCIENCE_TRANSITIVE_CARRIER_CLOSURE_REPAIR_20261007_V1.json":"a2162c41f7b40bd41d4c53ca608557e9ebe2e8f2",
}
def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
for rel,want in EXPECTED_TOP.items():
    got=blob(ROOT/rel)
    assert got==want,(rel,got,want)

manifest=json.loads((ROOT/"canonical/governance/TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261007_V1.json").read_text())
assert manifest["rank8_counterexample"]["copied_root_file_count"]==4
assert manifest["rank8_counterexample"]["required_closure_file_count"]==14
assert manifest["rank8_counterexample"]["omitted_transitive_file_count"]==10
assert manifest["rank8_counterexample"]["observed_crash_module"]=="canonical.runtime.explicit_requirement_index_v2"
assert manifest["rank8_counterexample"]["task_capability_negative_evidence"] is False
assert manifest["accounting"]["terminal_credit_delta"]==0
rows=manifest["closure"]
assert len(rows)==14
for row in rows:
    p=ROOT/row["path"]
    assert p.is_file(),row["path"]
    got=blob(p)
    assert got==row["git_blob_sha"],(row["path"],got,row["git_blob_sha"])

sys.path.insert(0,str(ROOT))
compiler=importlib.import_module("canonical.runtime.python_transitive_runtime_closure_v1")
roots=[x["path"] for x in manifest["roots"]]
closure=compiler.compute_closure(ROOT,roots)
assert closure["pass"] is True,closure
assert closure["closure_file_count"]==14
assert {x["path"] for x in closure["files"]}=={x["path"] for x in rows}

agent=importlib.import_module("canonical.runtime.harbor_science_agent_v1")
planner=importlib.import_module("canonical.runtime.harbor_science_planner_v1")
assert hasattr(agent,"HarborScienceAgent")
assert hasattr(planner,"TOOL")

test_path=ROOT/"canonical/tests/test_python_transitive_runtime_closure_v1.py"
spec=importlib.util.spec_from_file_location("science_closure_tests",test_path)
tests=importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(tests)
test_names=sorted(name for name in dir(tests) if name.startswith("test_") and callable(getattr(tests,name)))
assert len(test_names)==6,test_names
for name in test_names:
    getattr(tests,name)()

print(json.dumps({
 "status":"PASS",
 "exact_top_blobs":EXPECTED_TOP,
 "closure_file_count":14,
 "rank8_omitted_transitive_count":10,
 "agent_import_pass":True,
 "planner_import_pass":True,
 "direct_test_function_count":6,
 "benchmark_task_exposure":0,
 "acceptance_credit_delta":0,
 "terminal_credit_delta":0
},sort_keys=True))
