#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject/root2_v18_decision_root_projection"
OLD=SUB/"OLD_TERMINAL_ROOT_CAUSE_STATE_V1.json"
NEW=SUB/"NEW_TERMINAL_ROOT_CAUSE_STATE_V1.json"
V18=SUB/"ROOT2_FRONTIER_V18_FINAL_ACTIVATION_V1.json"
DEC=SUB/"ROOT2_DECISION_ONLY_EVALUATION_FINAL_ACTIVATION_V1.json"

def git_blob_sha(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert git_blob_sha(OLD)=="54021118b1b1f299cf0191d1e413a3009d95d76c"
assert git_blob_sha(NEW)=="3b3bc8ba4f923b7f3a0fcd45b29a11aef7e56ebf"
assert git_blob_sha(V18)=="a7a9b3414a2ecc8eb54b65e55030646e781671b9"
assert git_blob_sha(DEC)=="2f8690507a16840f085bcf34da90df1593dd0226"
old=json.loads(OLD.read_text())
new=json.loads(NEW.read_text())
v18=json.loads(V18.read_text())
dec=json.loads(DEC.read_text())

def diff(a,b,path=""):
    out=[]
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)):
            p=(path+"."+k) if path else k
            if k not in a or k not in b:
                out.append(p); continue
            out.extend(diff(a[k],b[k],p))
        return out
    if isinstance(a,list) and isinstance(b,list):
        if a!=b: out.append(path)
        return out
    if a!=b: out.append(path)
    return out

allowed={
 "roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_path",
 "roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_git_blob_sha",
 "roots.root_2_measurement_or_comparator.active_closure_controller.status",
 "roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_verification_path",
 "roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_verification_git_blob_sha",
 "roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_activation_path",
 "roots.root_2_measurement_or_comparator.active_closure_controller.current_frontier_activation_git_blob_sha",
 "scheduler_policy.root2_current_frontier",
 "scheduler_policy.root2_current_frontier_git_blob_sha",
 "scheduler_policy.root2_current_frontier_activation",
 "scheduler_policy.root2_decision_only_evaluation",
}
observed=set(diff(old,new))
assert observed==allowed, {"unexpected":sorted(observed-allowed),"missing":sorted(allowed-observed)}

assert v18["status"].startswith("ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS")
assert v18["frontier"]["git_blob_sha"]=="57d5ee650d4ee250db455d5818899f32aa304918"
assert v18["verification"]["workflow_run_id"]==37190949097
assert v18["verification"]["conclusion"]=="success"
assert v18["authority"]=={
 "scheduling":True,"execution":False,"fresh_reality":False,"promotion":False,"acceptance_reduction":False
}
assert dec["status"].startswith("ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS")
assert dec["effective_authority"]["scheduling"] is True
assert dec["effective_authority"]["decision_certificate_compilation"] is True
for k in ("benchmark_execution","fresh_reality","acceptance_reduction","promotion"):
    assert dec["effective_authority"][k] is False

assert new["current_acceptance"]==old["current_acceptance"]
assert new["current_acceptance"]["accepted_families"]==5
assert new["current_acceptance"]["proved_atomic"]==12
assert new["current_acceptance"]["unresolved_atomic"]==26
assert new["current_acceptance"]["terminal"] is False
ac=new["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert ac["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V18.json"
assert ac["current_frontier_git_blob_sha"]=="57d5ee650d4ee250db455d5818899f32aa304918"
assert ac["current_frontier_activation_git_blob_sha"]=="a7a9b3414a2ecc8eb54b65e55030646e781671b9"
assert ac["fresh_reality_authority"] is False
sp=new["scheduler_policy"]
assert sp["root2_current_frontier_git_blob_sha"]=="57d5ee650d4ee250db455d5818899f32aa304918"
assert sp["root2_decision_only_evaluation"]["final_activation_git_blob_sha"]=="2f8690507a16840f085bcf34da90df1593dd0226"
assert sp["root2_decision_only_evaluation"]["execution_authority"] is False
assert sp["root2_decision_only_evaluation"]["fresh_reality_authority"] is False
print(json.dumps({"status":"PASS","old_root":git_blob_sha(OLD),"new_root":git_blob_sha(NEW),"allowed_delta_count":len(observed),"accepted_families":5,"proved_atomic":12,"unresolved_atomic":26,"fresh_reality_authority":False,"acceptance_credit_delta":0},sort_keys=True))
