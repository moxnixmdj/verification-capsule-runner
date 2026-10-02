from __future__ import annotations
import hashlib,json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REG=ROOT/"BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
TRANS=ROOT/"OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json"
MAN=ROOT/"FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"
BRIDGE=ROOT/"COMPOSITION_BEHAVIORAL_BRIDGE_V1.json"

def sha(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def norm(x):
    s=str(x or "").lower().replace("_"," ").replace("/"," ")
    return re.sub(r"\s+"," ",s).strip()

reg=json.loads(REG.read_text()); trans=json.loads(TRANS.read_text()); man=json.loads(MAN.read_text()); bridge=json.loads(BRIDGE.read_text())
expected_auth={
 "behavioral_contract_registry":("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json",sha(REG)),
 "acceptance_transmutation":("canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json",sha(TRANS)),
 "component_manifest":("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json",sha(MAN)),
}
for k,(p,s) in expected_auth.items():
    row=bridge["authority"][k]
    assert row["path"]==p and row["git_blob_sha"]==s,(k,row,p,s)

residuals=reg["active_contracted_residuals"]; fammap=reg["family_to_residual_contracts"]; interfaces=man["interfaces"]; evidence=trans["evidence"]
by_id={x["behavior_id"]:x for x in residuals}
composition=set(fammap["MULTI_CAPABILITY_COMPOSITION"])
closures=[x for x in evidence if x.get("verified") is True and x.get("independent") is True and x.get("contamination_clean") is True and x.get("binds_frozen_protocol") is True and x.get("scope_relation")=="PROVEN_STRONGER" and x.get("closes_entire_protocol") is True]
derived=[]
for iface in interfaces:
    component=iface["component_id"]; iid=iface["interface_id"]
    for e in closures:
        family=e["family"]; contracts=fammap.get(family)
        if not isinstance(contracts,list) or len(contracts)!=1: continue
        behavior=contracts[0]
        if behavior not in composition: continue
        row=by_id[behavior]
        text=norm(" ".join(str(row.get(k) or "") for k in ("source","scope","terminal_consequence")))
        if norm(component) not in text: continue
        derived.append({
          "component_id":component,"interface_id":iid,"behavior_id":behavior,"source_family":family,
          "closure_evidence_id":e.get("id"),"source_witness_path":e.get("source_witness_path"),
          "independent_verification":e.get("independent_verification"),"proved_properties":["SCOPED_ACCEPTANCE_PROOF"]
        })
derived=sorted(derived,key=lambda x:(x["component_id"],x["interface_id"],x["behavior_id"]))
actual=sorted(bridge["bindings"],key=lambda x:(x["component_id"],x["interface_id"],x["behavior_id"]))
assert derived==actual,(derived,actual)
assert len(derived)==2
assert {x["component_id"] for x in derived}=={"delegation","tool discovery"}
assert bridge["verification_state"]["independent_verification"] is False
assert bridge["verification_state"]["slicer_receipt_authorized"] is False
print(json.dumps({"status":"PASS","derived_binding_count":2,"components":sorted(x["component_id"] for x in derived),"brain_blob_shas":{p:src for p,src in [(expected_auth[k][0],expected_auth[k][1]) for k in expected_auth]}},sort_keys=True))
