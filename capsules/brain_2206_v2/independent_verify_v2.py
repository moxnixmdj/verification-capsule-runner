from __future__ import annotations
import hashlib, itertools, json
from pathlib import Path
from canonical.runtime.opus55_typed_coverage_dominance_bridge_v1 import compile_typed_sandwich
ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/governance/OPUS55_TYPED_COVERAGE_DOMINANCE_BRIDGE_20261005_V1.json":"b9d61b37b98f91dabbf35d5e58b78c17e844d571",
 "canonical/runtime/opus55_typed_coverage_dominance_bridge_v1.py":"7e62031f4b5d81237c3f09a0142d5f0ce8d3b735",
 "canonical/tests/test_opus55_typed_coverage_dominance_bridge_v1.py":"c997d9a10a0d244c00947018acb01c14707cc967",
}
def blob(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def req(x,msg):
    if not x: raise AssertionError(msg)
def powerset(items):
    items=list(items)
    for m in range(1<<len(items)): yield {items[i] for i in range(len(items)) if m&(1<<i)}
def ud(atoms): return hashlib.sha256(json.dumps(atoms,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
def base():
    atoms={"A":"1"*40,"B":"2"*40,"C":"3"*40}; h=ud(atoms)
    return {"universe_id":"OMEGA-VERIFY","universe_sha256":h,"universe_atoms":atoms,
      "partition_certificate":{"source_sha":"d"*40,"independent_or_objective":True,"pairwise_disjoint_proved":True,"atoms_define_declared_omega_proved":True},
      "coverage_certificates":[{"id":"C1","universe_id":"OMEGA-VERIFY","universe_sha256":h,"source_sha":"a"*40,"cells":["A","B","C"],"independent_or_objective":True,"exact_atom_union_embedding_proved":True,"u_subset_domain_proved":True}],
      "dominance_certificates":[{"id":"B1","universe_id":"OMEGA-VERIFY","universe_sha256":h,"source_sha":"b"*40,"cells":["A","B"],"independent_or_objective":True,"exact_atom_union_embedding_proved":True,"scope_complete":True,"b_subset_q_proved":True}]}
def main():
    for rel,want in EXPECTED.items(): req(blob((ROOT/rel).read_bytes())==want,"BLOB_MISMATCH:"+rel)
    g=json.loads((ROOT/"canonical/governance/OPUS55_TYPED_COVERAGE_DOMINANCE_BRIDGE_20261005_V1.json").read_text())
    req(g["current_truth_repair"]["no_current_verified_omega_partition"] is True,"omega overclaim")
    req("PAIRWISE_DISJOINT" in g["theorem"]["premises"][2],"partition premise missing")
    req("DO_NOT_USE_AS_THE_DOMINANCE_ORDER" in g["current_truth_repair"]["protocol_schema_role"],"carrier promoted")
    req(g["independent_verification_required"] is True,"independent gate weakened")
    for k in ("scheduling_authority","execution_authority","promotion_authority","fresh_reality_authority"): req(g[k] is False,k)
    for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"): req(g["accounting"][k]==0,k)
    atoms=("A","B","C"); S=list(powerset(atoms)); total=prem=0
    for U,C1,C2,B1,B2,Q in itertools.product(S,repeat=6):
        total+=1
        ok=U<=C1 and U<=C2 and B1<=Q and B2<=Q and (C1&C2)<=(B1|B2)
        if ok:
            prem+=1; req(U<=Q,f"THEOREM_COUNTEREXAMPLE:{U,C1,C2,B1,B2,Q}")
    compiler=0
    for C in S:
        for B in S:
            m=base(); m["coverage_certificates"][0]["cells"]=sorted(C); m["dominance_certificates"][0]["cells"]=sorted(B)
            v=compile_typed_sandwich(m); req(v["status"]==("CLOSED" if not(C-B) else "OPEN"),"status"); req(set(v["residual"])==C-B,"residual"); compiler+=1
    attacks=[]
    cases=[
      ("missing_partition",lambda m:m.pop("partition_certificate"),"PARTITION_CERTIFICATE_MISSING"),
      ("unproved_disjointness",lambda m:m["partition_certificate"].__setitem__("pairwise_disjoint_proved",False),"pairwise_disjoint_proved_REQUIRED_TRUE"),
      ("unproved_coverage_embedding",lambda m:m["coverage_certificates"][0].__setitem__("exact_atom_union_embedding_proved",False),"exact_atom_union_embedding_proved_REQUIRED_TRUE"),
      ("unproved_dominance_embedding",lambda m:m["dominance_certificates"][0].__setitem__("exact_atom_union_embedding_proved",False),"exact_atom_union_embedding_proved_REQUIRED_TRUE"),
      ("semantic_atom_drift",lambda m:m["universe_atoms"].__setitem__("A","9"*40),"UNIVERSE_SHA256_CONTENT_MISMATCH"),
      ("digest_mismatch",lambda m:m["dominance_certificates"][0].__setitem__("universe_sha256","f"*64),"UNIVERSE_SHA256_MISMATCH"),
      ("unknown_region",lambda m:m["coverage_certificates"][0]["cells"].append("Z"),"UNKNOWN_REGION"),
      ("scope_incomplete",lambda m:m["dominance_certificates"][0].__setitem__("scope_complete",False),"scope_complete_REQUIRED_TRUE"),
    ]
    for name,mut,needle in cases:
        m=base(); mut(m); v=compile_typed_sandwich(m); req(v["status"]=="FAIL_CLOSED" and needle in v["reason"],name); attacks.append(name)
    print(json.dumps({"status":"PASS","brain_pr":2206,"brain_head":"8f277e454470a21f3ebdd9f091f58ba32aaa164f","exact_blobs":EXPECTED,"exhaustive_assignments":total,"premise_satisfying_assignments":prem,"compiler_subset_pairs":compiler,"adversarial_dimensions":attacks,"semantic_target_coverage_proved":False,"omega_partition_proved_for_real_target":False,"terminal_completion":False,"acceptance_credit_delta":0},indent=2))
if __name__=="__main__": main()
