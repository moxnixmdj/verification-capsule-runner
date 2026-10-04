import json, pathlib, subprocess

BASE="subject/root2_v8_activation_20261004_sol"
FILES={
  "prior":f"{BASE}/PRIOR_ROOT.json",
  "projected":f"{BASE}/PROJECTED_ROOT.json",
  "activation":f"{BASE}/ACTIVATION.json",
  "v8":f"{BASE}/V8.json",
  "verification":f"{BASE}/V8_VERIFICATION.json",
}
EXPECTED={
  "prior":"c5139a9a80aea6ee89779ca5324dc31daf8f2719",
  "projected":"0e11e2f04daae66defe038c78fdad44af2535423",
  "activation":"e0c0b2a25e764c875e4af4cffb3a61f05a7a58bc",
  "v8":"2eaeb74fe306ee2507145e26eb731f69f46e6153",
  "verification":"7e2d71144853c41fadab55f4074d484edf46e651",
}
def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k], (k,got,EXPECTED[k])

prior=json.loads(pathlib.Path(FILES["prior"]).read_text())
proj=json.loads(pathlib.Path(FILES["projected"]).read_text())
act=json.loads(pathlib.Path(FILES["activation"]).read_text())
v8=json.loads(pathlib.Path(FILES["v8"]).read_text())
ver=json.loads(pathlib.Path(FILES["verification"]).read_text())

# Frozen terminal truth.
expected_acceptance={
 "accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,
 "total_families":19,"total_atomic":38,"terminal":False,
}
assert prior["current_acceptance"]==proj["current_acceptance"]==expected_acceptance
assert prior["accounting"]==proj["accounting"]

# Exact V8 and verifier bindings.
assert act["frontier"]["git_blob_sha"]==EXPECTED["v8"]
assert act["verification"]["git_blob_sha"]==EXPECTED["verification"]
assert act["verification"]["conclusion"]=="success"
assert act["parent"]["git_blob_sha"]=="35e8b578aca1290bcf469d6350ae085ba8a86c64"
assert act["parent"]["verification_git_blob_sha"]=="c2b96c9d48b7ef6508ea77dc6983da12eaf099c3"
assert act["parent"]["activation_git_blob_sha"]=="ccfc97ca8f5586d583990f0e37277b88c12227e9"
assert act["authority"]=={
 "scheduling":True,"effective_scheduling":True,"execution":False,
 "promotion":False,"fresh_reality":False,
}
assert ver["subject"]["git_blob_sha"]==EXPECTED["v8"]
assert ver["independent_runner"]["conclusion"]=="success"
assert ver["verified"]["accepted_families"]==5
assert ver["verified"]["proved_atomic"]==12
assert ver["verified"]["unresolved_atomic"]==26
assert ver["verified"]["exactly_one_new_v8_delta"] is True
assert ver["verified"]["custom_route_comparability_open"] is True
assert ver["verified"]["vals_platform_and_jury_zero_spend_open"] is True
assert ver["execution_authority"] is False
assert ver["promotion_authority"] is False
assert ver["fresh_reality_authority"] is False
assert v8["execution_authority"] is False
assert v8["promotion_authority"] is False
assert v8["fresh_reality_authority"] is False

# Projected live chain.
r2=proj["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert r2["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V8.json"
assert r2["current_frontier_git_blob_sha"]==EXPECTED["v8"]
assert r2["status"]=="ACTIVE__ROOT2_FRONTIER_V8_INDEPENDENT_PASS__CURRENT_AUTHORITY_BOUND__ZERO_CREDIT"
assert r2["current_frontier_verification_path"]=="canonical/verification/ROOT2_V8_FINANCE_DUAL_ROUTE_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
assert r2["current_frontier_verification_git_blob_sha"]==EXPECTED["verification"]
assert r2["current_frontier_activation_path"]=="canonical/governance/ROOT2_FRONTIER_V8_ACTIVATION_V1.json"
assert r2["current_frontier_activation_git_blob_sha"]==EXPECTED["activation"]
assert r2["effective_scheduling_authority"] is True
assert r2["fresh_reality_authority"] is False
assert proj["scheduler_policy"]["root2_current_frontier"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V8.json"
assert proj["scheduler_policy"]["root2_effective_scheduling_authority"] is True
assert proj["scheduler_policy"]["fresh_reality_before_zero_reality_fixed_point"] is False

# Exact whole-document drift audit.
def diff(a,b,path=()):
    out=[]
    if type(a) is not type(b):
        return [path]
    if isinstance(a,dict):
        keys=set(a)|set(b)
        for k in sorted(keys):
            if k not in a or k not in b:
                out.append(path+(k,))
            else:
                out.extend(diff(a[k],b[k],path+(k,)))
        return out
    if isinstance(a,list):
        if len(a)!=len(b):
            return [path]
        for i,(x,y) in enumerate(zip(a,b)):
            out.extend(diff(x,y,path+(str(i),)))
        return out
    return [] if a==b else [path]

changed={".".join(p) for p in diff(prior,proj)}
allowed={
 "roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_path",
 "roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_git_blob_sha",
 "roots.root_2_measurement_or_comparator.active_closure_controller.status",
 "roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_verification_path",
 "roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_verification_git_blob_sha",
 "roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_activation_path",
 "roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_activation_git_blob_sha",
 "scheduler_policy.root2_current_frontier",
}
assert changed==allowed, ("unexpected projection drift", sorted(changed-allowed), "missing expected", sorted(allowed-changed))

# Explicitly verify unrelated roots are byte-semantically identical.
assert prior["roots"]["root_1_capability_missing"]==proj["roots"]["root_1_capability_missing"]
assert prior["roots"]["root_3_scope_completeness"]==proj["roots"]["root_3_scope_completeness"]
assert prior.get("root3_current_execution_state")==proj.get("root3_current_execution_state")

print("PASS: Root2 V8 activation projection changes exactly 8 authorized pointer/status fields")
print("PASS: Root1, Root3, acceptance accounting, and fresh-reality block are unchanged")
print("PASS: V8 -> verification -> activation content-addressed chain is exact")
print("PASS: 5/19 families, 12/38 predicates, 26 unresolved; zero credit; scheduling only")
