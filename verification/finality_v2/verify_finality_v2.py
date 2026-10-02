from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "terminal_closure_reducer.py":"55440e4519b3aaf8245b39ef60507410a4228b69",
 "ownership_matrix_v2.json":"1936fec15a983f7027e3696905aed99756727cfc",
 "final_proof_bundle_v2.json":"f1eddea39603b5fd5088a5bc397a0ac0fa569d78",
 "terminal_closure_manifest_v1.json":"6bd74a11a076819663643452d1f00111f2c4638c",
 "global_ownership_receipt.json":"e0dbd996c18bdb818693ab0d217d751594a03d0f",
 "donor_cleanroom_receipt.json":"d3144bf0aa618b15ef594d24de54d55cbdb329fd",
 "postwave_reduction.json":"51e3e7578e9adbeee2168d2223b84481fea16a09",
}
def git_blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()
for name,expected in EXPECTED.items():
    got=git_blob(ROOT/name)
    assert got==expected,(name,expected,got)

bundle=json.loads((ROOT/"final_proof_bundle_v2.json").read_text())
matrix=json.loads((ROOT/"ownership_matrix_v2.json").read_text())
closure=json.loads((ROOT/"terminal_closure_manifest_v1.json").read_text())
global_receipt=json.loads((ROOT/"global_ownership_receipt.json").read_text())
donor=json.loads((ROOT/"donor_cleanroom_receipt.json").read_text())
reduction=json.loads((ROOT/"postwave_reduction.json").read_text())

rows=matrix["rows"]
assert len(rows)==19
assert len({r["family"] for r in rows})==19
assert all(r["status"]=="VERIFIED_OWNED_EQUAL_OR_BETTER" for r in rows)
assert matrix["summary"]["verified_owned_count"]==19
assert matrix["summary"]["ownership_pending_count"]==0
assert matrix["summary"]["full_opus_5_5_envelope_obsoleted"] is True

assert reduction["contract_verdict"]["valid"] is True
assert reduction["contract_verdict"]["contract_pass_count"]==12
assert reduction["family_verdict"]["valid"] is True
assert reduction["family_verdict"]["family_pass_count"]==19
assert reduction["family_verdict"]["failed_families"]==[]

assert "INDEPENDENT_PUBLIC_RUNNER_PASS" in global_receipt["status"]
assert global_receipt["result"]["counters"]=={
 "donor_dependent_required_behaviors":0,
 "unresolved_verifier_mutations":0,
 "unresolved_composition_failures":0,
}
assert global_receipt["result"]["terminal_predicates"]["final_donor_deletion_cleanroom_pass"] is True

assert "INDEPENDENT_PUBLIC_RUNNER_PASS__DONOR_DENIED_IDENTICAL_FROZEN_QUALIFICATION__BEHAVIOR_PRESERVED" in donor["status"]
assert donor["behavior_preserved"] is True
assert donor["byte_identical_terminal_result"] is True
assert donor["undeclared_dependency_count"]==0

entries=sorted((x["path"],x["git_blob_sha"]) for x in bundle["ordered_evidence"])
leaves=[hashlib.sha256(("leaf\0"+p+"\0"+s).encode()).digest() for p,s in entries]
while len(leaves)>1:
    if len(leaves)%2: leaves.append(leaves[-1])
    leaves=[hashlib.sha256(b"node\0"+leaves[i]+leaves[i+1]).digest() for i in range(0,len(leaves),2)]
root=leaves[0].hex()
assert root==bundle["merkle_root_sha256"]=="11eef43b66bb3cb697c7cb49f374df6cb45c6b6200610cc276998aa37d7f9a66"
evidence=dict(entries)
assert evidence["canonical/runtime/terminal_closure_reducer.py"]=="55440e4519b3aaf8245b39ef60507410a4228b69"
assert evidence["canonical/runtime/test_terminal_closure_reducer.py"]=="d5bb1c65fff1767f1b911c24bc826f0a2c3d59bf"
assert evidence["canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V2.json"]=="1936fec15a983f7027e3696905aed99756727cfc"

spec=importlib.util.spec_from_file_location("terminal_closure_reducer",ROOT/"terminal_closure_reducer.py")
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
verdict=mod.evaluate_manifest(closure)
assert verdict["achieved"] is True,verdict
assert verdict["failed_predicates"]==[],verdict
assert verdict["closed_family_count"]==19
print(json.dumps({
 "status":"INDEPENDENT_FINALITY_V2_PASS",
 "closed_family_count":19,
 "ownership_matrix_verified_count":19,
 "proof_bundle_root":root,
 "closure_failed_predicates":[],
},sort_keys=True))
