"""One-use production launcher for the frozen Unknown-Domain direct V2 evaluator.

The launcher is inert until a GitHub branch-create event names the exact SHA-256
of a frozen execution lease. It then rechecks the lease and point-of-use
preflight, atomically creates the one-use claim ref through GitHub's REST API,
and proceeds only when that create returns HTTP 201. Beacon and evaluator secret
are generated only after that linearization event.

The immutable result intentionally excludes hidden evaluator records and the raw
secret/beacon. It contains only content digests, case-level frozen-scorer
verdicts, probe counts, and the aggregate reduction input.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as generator
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime.unknown_domain_direct_production_preflight_v1 import preflight

ROOT=Path(__file__).resolve().parents[2]
LEASE_PATH=ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_V1.json"
PREFLIGHT_INPUT_PATH=ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_PRODUCTION_PREFLIGHT_INPUT_V1.json"
TARGET="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
LEAVES={
 "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE",
 "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS",
}
LAUNCH_PREFIX="unknown-domain-direct-launch/"
CLAIM_PREFIX="unknown-domain-direct-claims/"
RESULT_PREFIX="canonical/verification/UNKNOWN_DOMAIN_DIRECT_PRODUCTION_RESULT_"
RESULT_ARTIFACT_PATH=ROOT/"unknown_domain_direct_production_result.json"


class ProductionLaunchError(RuntimeError):
    pass


def _git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def _json_request(method:str,url:str,token:str,payload:Mapping[str,Any]):
    raw=json.dumps(payload,separators=(",",":")).encode()
    req=urllib.request.Request(
        url,data=raw,method=method,
        headers={
            "Authorization":"Bearer "+token,
            "Accept":"application/vnd.github+json",
            "X-GitHub-Api-Version":"2022-11-28",
            "Content-Type":"application/json",
        },
    )
    try:
        with urllib.request.urlopen(req,timeout=30) as resp:
            body=resp.read()
            return int(resp.status), json.loads(body or b"{}")
    except urllib.error.HTTPError as exc:
        body=exc.read()
        try: parsed=json.loads(body or b"{}")
        except Exception: parsed={"message":"non-json error"}
        return int(exc.code), parsed


def create_ref(repo:str,token:str,ref:str,sha:str):
    return _json_request("POST",f"https://api.github.com/repos/{repo}/git/refs",token,{"ref":ref,"sha":sha})


def put_result(repo:str,token:str,branch:str,path:str,content:Mapping[str,Any]):
    raw=(json.dumps(content,indent=2,sort_keys=True)+"\n").encode()
    payload={
        "message":"Record immutable Unknown-Domain one-use production result",
        "content":base64.b64encode(raw).decode(),
        "branch":branch,
    }
    return _json_request("PUT",f"https://api.github.com/repos/{repo}/contents/{path}",token,payload)


def canonical_identity_from_lease(lease:Mapping[str,Any])->dict[str,Any]:
    components=lease.get("exact_components")
    source=lease.get("source_brain")
    claim=lease.get("atomic_claim")
    limits=lease.get("limits")
    resources=lease.get("resources")
    authority=lease.get("authority")
    if not isinstance(components,Mapping) or not all(isinstance(x,Mapping) for x in (source,claim,limits,resources,authority)):
        raise ProductionLaunchError("LEASE_IDENTITY_INPUT_INVALID")
    return {
        "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_IDENTITY_V2",
        "target_predicate":str(lease.get("target_predicate") or ""),
        "authorized_leaves":sorted(map(str,lease.get("authorized_leaves",[]))),
        "activation_git_blob_sha":source.get("final_activation_blob"),
        "qualification_receipt_git_blob_sha":source.get("qualification_receipt_blob"),
        "production_precommit_git_blob_sha":source.get("production_precommit_blob"),
        "exact_execution_subject":{
            "candidate_v1":components.get("canonical/runtime/unknown_domain_direct_candidate_v1.py"),
            "candidate_v2":components.get("canonical/runtime/unknown_domain_direct_candidate_v2.py"),
            "generator_v1":components.get("canonical/runtime/unknown_domain_direct_hidden_generator_v1.py"),
            "generator_v2":components.get("canonical/runtime/unknown_domain_direct_hidden_generator_v2.py"),
            "hidden_scorer":components.get("canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py"),
            "execution_harness":components.get("canonical/runtime/unknown_domain_direct_execution_harness_v1.py"),
        },
        "claim_repository":claim.get("repository"),
        "claim_namespace":claim.get("claim_ref_prefix"),
        "production_budget":{
            "production_populations_allowed":limits.get("production_populations"),
            "production_cases_allowed":limits.get("production_cases"),
            "max_transfer_probes_per_case":limits.get("max_transfer_probes_per_case"),
            "replay_allowed":limits.get("replay_allowed"),
            "replacement_allowed":limits.get("replacement_allowed"),
            "post_result_tuning_allowed":limits.get("post_result_tuning_allowed"),
        },
        "resource_boundary":dict(resources),
        "global_fresh_reality":authority.get("global_fresh_reality"),
    }


def lease_bytes_and_digest(path:Path=LEASE_PATH):
    raw=path.read_bytes()
    lease=json.loads(raw)
    identity=canonical_identity_from_lease(lease)
    canonical=json.dumps(identity,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return raw,hashlib.sha256(canonical).hexdigest()


def validate_lease(lease:Mapping[str,Any],digest:str)->None:
    if lease.get("schema")!="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_V1":
        raise ProductionLaunchError("LEASE_SCHEMA_INVALID")
    derived_identity=canonical_identity_from_lease(lease)
    if lease.get("lease_identity")!=derived_identity:
        raise ProductionLaunchError("LEASE_IDENTITY_NOT_CANONICAL")
    canonical=json.dumps(derived_identity,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    if hashlib.sha256(canonical).hexdigest()!=digest:
        raise ProductionLaunchError("LEASE_IDENTITY_DIGEST_MISMATCH")
    if lease.get("atomic_claim",{}).get("claim_key_rule")!="SHA256_OF_CANONICAL_QUALIFIED_EXECUTION_TUPLE_V2":
        raise ProductionLaunchError("LEASE_CLAIM_KEY_RULE_INVALID")
    if lease.get("target_predicate")!=TARGET:
        raise ProductionLaunchError("LEASE_TARGET_MISMATCH")
    if set(map(str,lease.get("authorized_leaves",[])))!=LEAVES:
        raise ProductionLaunchError("LEASE_LEAF_SET_MISMATCH")
    limits=lease.get("limits",{})
    if limits.get("production_populations")!=1 or limits.get("production_cases")!=27:
        raise ProductionLaunchError("LEASE_PRODUCTION_LIMIT_INVALID")
    if limits.get("replay_allowed") is not False or limits.get("replacement_allowed") is not False:
        raise ProductionLaunchError("LEASE_REPLAY_OR_REPLACEMENT_ALLOWED")
    resources=lease.get("resources",{})
    expected={"persistent_learned_bytes":0,"external_frontier_model_calls":0,"external_learned_capability_calls":0,"incremental_spend_usd":0}
    if resources!=expected:
        raise ProductionLaunchError("LEASE_RESOURCE_BOUNDARY_INVALID")
    components=lease.get("exact_components")
    if not isinstance(components,dict) or not components:
        raise ProductionLaunchError("LEASE_COMPONENTS_INVALID")
    for rel,expected_sha in components.items():
        p=ROOT/str(rel)
        if not p.is_file():
            raise ProductionLaunchError("LEASE_COMPONENT_MISSING:"+str(rel))
        got=_git_blob(p.read_bytes())
        if got!=expected_sha:
            raise ProductionLaunchError("LEASE_COMPONENT_BLOB_MISMATCH:"+str(rel))



def validate_event_sha_binding(launch_sha:str,runtime_head:str)->None:
    if runtime_head!=launch_sha:
        raise ProductionLaunchError("RUNTIME_HEAD_EVENT_SHA_MISMATCH")


def current_git_head()->str:
    try:
        return subprocess.check_output(
            ["git","rev-parse","HEAD"],cwd=ROOT,text=True,stderr=subprocess.DEVNULL
        ).strip()
    except Exception as exc:
        raise ProductionLaunchError("RUNTIME_HEAD_UNAVAILABLE") from exc

def validate_point_of_use()->Mapping[str,Any]:
    doc=json.loads(PREFLIGHT_INPUT_PATH.read_text())
    out=preflight(doc)
    if out.get("ready") is not True or out.get("status")!="READY_FOR_ATOMIC_ONE_USE_CLAIM_ONLY":
        raise ProductionLaunchError("POINT_OF_USE_PREFLIGHT_NOT_READY:"+json.dumps(out,sort_keys=True))
    return out


def evaluate_packet(packet:Mapping[str,Any])->dict[str,Any]:
    visible=packet.get("visible_cases")
    hidden=packet.get("hidden_records")
    if not isinstance(visible,list) or not isinstance(hidden,list) or len(visible)!=27 or len(hidden)!=27:
        raise ProductionLaunchError("PRODUCTION_PACKET_COUNT_INVALID")
    rows=[]
    scorer_rows=[]
    for case_visible,hidden_record in zip(visible,hidden):
        out=harness.execute_case(candidate_step=candidate.step,case_visible=case_visible,hidden_record=hidden_record)
        sr=dict(out["scorer_result"])
        scorer_rows.append(sr)
        rows.append({
            "case_id":out["case_id"],
            "leaf_id":out["leaf_id"],
            "probe_count":out["probe_count"],
            "scorer_result":sr,
        })
    agg=scorer.aggregate(scorer_rows)
    return {"case_results":rows,"aggregate":agg}


def execute_after_claim(*,claim_id:str)->dict[str,Any]:
    # These values do not exist before the atomic claim succeeds.
    beacon="UDIR-PROD-"+secrets.token_hex(24)
    evaluator_secret=secrets.token_bytes(32)
    authority={
        "active":True,
        "target_predicate":TARGET,
        "authorized_leaves":sorted(LEAVES),
        "predicate_local_fresh_reality":True,
        "global_fresh_reality":False,
        "one_use_claim_created":True,
        "one_use_claim_id":claim_id,
        "incremental_spend_usd":0,
    }
    packet=generator.generate_production_population(
        beacon=beacon,evaluator_secret=evaluator_secret,authority=authority
    )
    if packet.get("production") is not True or packet.get("case_count")!=27:
        raise ProductionLaunchError("PRODUCTION_PACKET_INVALID")
    if packet.get("authority_claim_id")!=claim_id:
        raise ProductionLaunchError("PRODUCTION_CLAIM_BINDING_MISMATCH")
    evaluated=evaluate_packet(packet)
    return {
        "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_PRODUCTION_RESULT_V1",
        "status":"PRODUCTION_PASS" if evaluated["aggregate"].get("all_27_cases_pass") is True else "PRODUCTION_FAIL",
        "target_predicate":TARGET,
        "authority_claim_id":claim_id,
        "visible_packet_digest":packet["visible_packet_digest"],
        "hidden_packet_digest":packet["hidden_packet_digest"],
        "beacon_sha256":hashlib.sha256(beacon.encode()).hexdigest(),
        "evaluator_secret_sha256":hashlib.sha256(evaluator_secret).hexdigest(),
        "production_cases_generated":27,
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "incremental_spend_usd":0,
        "case_results":evaluated["case_results"],
        "aggregate":evaluated["aggregate"],
        "raw_hidden_records_persisted":False,
        "raw_evaluator_secret_persisted":False,
        "raw_beacon_persisted":False,
        "replay_allowed":False,
        "replacement_allowed":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "promotion_authority":False,
        "separate_independent_reduction_required":True,
    }


def claim_then_execute(
    *,
    repo:str,
    token:str,
    launch_sha:str,
    digest:str,
    execute_fn:Callable[...,Mapping[str,Any]]=execute_after_claim,
    create_ref_fn:Callable[...,tuple[int,Mapping[str,Any]]]=create_ref,
):
    claim_branch=CLAIM_PREFIX+digest
    claim_ref="refs/heads/"+claim_branch
    status,response=create_ref_fn(repo,token,claim_ref,launch_sha)
    if status!=201:
        raise ProductionLaunchError("ATOMIC_CLAIM_CREATE_NOT_201:"+str(status))
    response_ref=str(response.get("ref") or "")
    obj=response.get("object") if isinstance(response,Mapping) else None
    obj_sha=str(obj.get("sha") or "") if isinstance(obj,Mapping) else ""
    if response_ref!=claim_ref or obj_sha!=launch_sha:
        result={
            "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_PRODUCTION_RESULT_V1",
            "status":"ATOMIC_CLAIM_RESPONSE_INVALID__ONE_USE_CLAIM_CONSUMED__NO_EXECUTION__FAIL_CLOSED",
            "target_predicate":TARGET,
            "authority_claim_id":claim_ref,
            "claim_response_ref":response_ref,
            "claim_response_object_sha":obj_sha,
            "production_cases_generated":0,
            "persistent_learned_bytes":0,
            "external_frontier_model_calls":0,
            "external_learned_capability_calls":0,
            "incremental_spend_usd":0,
            "raw_hidden_records_persisted":False,
            "raw_evaluator_secret_persisted":False,
            "raw_beacon_persisted":False,
            "replay_allowed":False,
            "replacement_allowed":False,
            "acceptance_credit_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
            "promotion_authority":False,
            "separate_independent_reduction_required":True,
        }
    else:
        try:
            result=dict(execute_fn(claim_id=claim_ref))
        except Exception as exc:
            result={
                "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_PRODUCTION_RESULT_V1",
                "status":"PRODUCTION_EXECUTION_EXCEPTION__ONE_USE_CLAIM_CONSUMED__FAIL_CLOSED",
                "target_predicate":TARGET,
                "authority_claim_id":claim_ref,
                "exception_type":type(exc).__name__,
                "exception_message_sha256":hashlib.sha256(str(exc).encode()).hexdigest(),
                "exception_message_persisted":False,
                "production_cases_generated":"UNKNOWN_AFTER_CLAIM_EXCEPTION",
                "persistent_learned_bytes":0,
                "external_frontier_model_calls":0,
                "external_learned_capability_calls":0,
                "incremental_spend_usd":0,
                "raw_hidden_records_persisted":False,
                "raw_evaluator_secret_persisted":False,
                "raw_beacon_persisted":False,
                "replay_allowed":False,
                "replacement_allowed":False,
                "acceptance_credit_delta":0,
                "family_credit_delta":0,
                "capability_credit_delta":0,
                "ownership_credit_delta":0,
                "promotion_authority":False,
                "separate_independent_reduction_required":True,
            }
    result["claim_create_http_status"]=201
    result["claim_response_ref"]=response_ref
    result["claim_response_object_sha"]=obj_sha
    result["claim_uniqueness_source"]="ATOMIC_CREATE_RESPONSE"
    return claim_branch,result


def main()->None:
    repo=os.environ.get("GITHUB_REPOSITORY","")
    token=os.environ.get("GITHUB_TOKEN","")
    ref_name=os.environ.get("GITHUB_REF_NAME","")
    launch_sha=os.environ.get("GITHUB_SHA","")
    if not repo or not token or len(launch_sha)!=40:
        raise ProductionLaunchError("GITHUB_CONTEXT_INVALID")
    runtime_head=current_git_head()
    validate_event_sha_binding(launch_sha,runtime_head)
    if not ref_name.startswith(LAUNCH_PREFIX):
        raise ProductionLaunchError("LAUNCH_REF_PREFIX_INVALID")
    suffix=ref_name[len(LAUNCH_PREFIX):]
    raw,digest=lease_bytes_and_digest()
    if suffix!=digest:
        raise ProductionLaunchError("LAUNCH_REF_LEASE_DIGEST_MISMATCH")
    lease=json.loads(raw)
    validate_lease(lease,digest)
    validate_point_of_use()

    claim_branch,result=claim_then_execute(
        repo=repo,token=token,launch_sha=launch_sha,digest=digest
    )
    result["execution_identity_sha256"]=digest
    result["execution_lease_sha256"]=digest
    result["execution_lease_git_blob_sha"]=_git_blob(raw)
    result["launch_ref"]="refs/heads/"+ref_name
    result["runtime_git_head"]=runtime_head
    result_path=RESULT_PREFIX+digest.upper()+"_V1.json"
    result["result_path"]=result_path
    sealed_json=json.dumps(result,sort_keys=True,separators=(",",":"))
    RESULT_ARTIFACT_PATH.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("SEALED_PRODUCTION_RESULT_SHA256="+hashlib.sha256(sealed_json.encode()).hexdigest())
    print("SEALED_PRODUCTION_RESULT_JSON="+sealed_json)
    status,response=put_result(repo,token,claim_branch,result_path,result)
    if status!=201:
        raise ProductionLaunchError("RESULT_COMMIT_NOT_201:"+str(status))
    commit=response.get("commit") if isinstance(response,Mapping) else None
    commit_sha=str(commit.get("sha") or "") if isinstance(commit,Mapping) else ""
    print(json.dumps({
        "status":result["status"],
        "claim_ref":"refs/heads/"+claim_branch,
        "claim_create_http_status":201,
        "production_cases_generated":result.get("production_cases_generated"),
        "all_27_cases_pass":(result.get("aggregate") or {}).get("all_27_cases_pass"),
        "result_path":result_path,
        "result_commit_sha":commit_sha,
    },sort_keys=True))


if __name__=="__main__":
    main()
