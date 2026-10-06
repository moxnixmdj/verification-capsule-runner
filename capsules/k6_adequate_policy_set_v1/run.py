import importlib.util, pathlib, traceback, json, hashlib

root=pathlib.Path(__file__).resolve().parent
test_path=root/"canonical/tests/test_k6_adequate_policy_set_compiler_v1.py"
spec=importlib.util.spec_from_file_location("tests",test_path)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
tests=[(n,getattr(mod,n)) for n in dir(mod) if n.startswith("test_") and callable(getattr(mod,n))]
failed=[]
for n,f in tests:
    try:
        f(); print("PASS",n)
    except Exception as e:
        failed.append(n); print("FAIL",n,repr(e)); traceback.print_exc()
files=[
 "canonical/runtime/terminal_distribution_outcome_order_v1.py",
 "canonical/runtime/k6_adequate_policy_set_compiler_v1.py",
 "canonical/tests/test_k6_adequate_policy_set_compiler_v1.py",
]
digests={}
for rel in files:
    digests[rel]=hashlib.sha1((root/rel).read_bytes()).hexdigest()
print(json.dumps({"passed":len(tests)-len(failed),"total":len(tests),"failed":failed,"git_blob_sha1":digests},sort_keys=True))
raise SystemExit(1 if failed else 0)
