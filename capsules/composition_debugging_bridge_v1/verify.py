from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
OLD=ROOT/"composition_recovery_bridge_v1"

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def blob(p):
    b=Path(p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def req(cond,code,errors):
    if not cond: errors.append(code)

def main():
    e=[]
    bridge=load(HERE/"bridge.json")
    req(blob(HERE/"bridge.json")=="c6ec2a46bf8e271bafc6d4fd18a138cf67b657aa","BRIDGE_BLOB",e)
    req(bridge.get("component_id")=="debugging","COMPONENT",e)
    req(bridge.get("interface_id")=="coding+debugging+tool discovery","INTERFACE",e)
    req(bridge.get("proved_properties")==["SCOPED_ACCEPTANCE_PROOF"],"PROPERTY",e)
    req(bridge.get("verified") is False and bridge.get("independent") is False,"SELF_CREDIT",e)

    env=load(OLD/"envelope.json")
    prot=load(OLD/"protocols.json")
    mani=load(OLD/"manifest.json")
    scope=load(OLD/"recovery_scope.json")
    acc=load(OLD/"recovery_acceptance.json")

    rows=[x for x in mani["interfaces"] if x.get("component_id")=="debugging"]
    req(len(rows)==1,"DEBUGGING_NOT_UNIQUE",e)
    if rows:
        req(rows[0].get("interface_id")=="coding+debugging+tool discovery","TARGET_INTERFACE_DRIFT",e)
        req(rows[0].get("required_properties")==["SCOPED_ACCEPTANCE_PROOF"],"TARGET_PROPERTY_DRIFT",e)

    fam=next((x for x in env["families"] if x.get("id")=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"),None)
    req(isinstance(fam,dict),"SOURCE_FAMILY_MISSING",e)
    if fam:
        text=fam.get("useful_behavior","").lower()
        req(all(s in text for s in ["falsify conclusions","diagnose failures"]),"SOURCE_BEHAVIOR_TOO_NARROW",e)

    src=next((x for x in prot["protocols"] if x.get("family")=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"),None)
    req(isinstance(src,dict),"SOURCE_PROTOCOL_MISSING",e)
    if src:
        dims=set(src.get("task_dimensions",[]))
        req({"semantic self-check","counterexample discovery","earliest causal failure localization","repair selection"}.issubset(dims),"DEBUGGING_DIMENSIONS_MISSING",e)
        metrics=set(src.get("primary_metrics",[]))
        req({"failure_detection_rate","true_root_cause_topk","repair_rescue_rate"}.issubset(metrics),"DEBUGGING_METRICS_MISSING",e)

    req(str(scope.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"SCOPE_NOT_INDEPENDENT",e)
    sv=scope.get("verified",{})
    req(sv.get("scope_complete") is True,"SCOPE_NOT_COMPLETE",e)
    req(sv.get("objective_ceiling_or_floor") is True,"NO_OBJECTIVE_BOUND",e)
    req(str(acc.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),"ACCEPTANCE_NOT_INDEPENDENT",e)
    req((acc.get("verified_result",{}).get("newly_closed_families"))==["SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"],"SOURCE_FAMILY_NOT_CLOSED",e)

    out={"schema":"PROJECT_BRAIN_COMPOSITION_DEBUGGING_BRIDGE_INDEPENDENT_VERIFICATION_V1","pass":not e,"errors":sorted(e),"verified_component":"debugging" if not e else None,"verified_interface":"coding+debugging+tool discovery" if not e else None,"proved_properties":["SCOPED_ACCEPTANCE_PROOF"] if not e else [],"adjacent_component_credit":False,"parent_composition_credit":False,"incremental_spend_usd":0}
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if not e else 1
if __name__=="__main__": raise SystemExit(main())
