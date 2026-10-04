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
import time
import urllib.error
import urllib.parse
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


class ProductionLaunchError(RuntimeError):
    pass


def _git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def _json_request(method:str,url:str,token:str,payload:Mapping[str,Any]|None=None):
    raw=None if payload is None else json.dumps(payload,separators=(",",":")).encode()
    headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
    }
    if raw is not None:
        headers["Content-Type"]="application/json"
    req=urllib.request.Request(url,data=raw,method=method,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=30) as resp:
            body=resp.read()
            return int(resp.status), json.loads(body or b"{}")
    except urllib.error.HTTPError as exc:
        body=exc.read()
        try: parsed=json.loads(body or b"{}")
        except Exception: parsed={"message":"non-json error"}
        return int(exc.code), parsed
    except (urllib.error.URLError,TimeoutError,OSError) as exc:
        return 0,{"message":type(exc).__name__}


def create_ref(repo:str,token:str,ref:str,sha:str):
    return _json_request("POST",f"https://api.github.com/repos/{repo}/git/refs",token,{"ref":ref,"sha":sha})


def _result_bytes(content:Mapping[str,Any])->bytes:
    return (json.dumps(content,indent=2,sort_keys=True)+"\n").encode()


def put_result(repo:str,token:str,branch:str,path:str,content:Mapping[str,Any]):
    raw=_result_bytes(content)
    payload={
        "message":"Record immutable Unknown-Domain one-use production result",
        "content":base64.b64encode(raw).decode(),
        "branch":branch,
    }
    return _json_request("PUT",f"https://api.github.com/repos/{repo}/contents/{path}",token,payload)


def get_result_bytes(repo:str,token:str,branch:str,path:str):
    qbranch=urllib.parse.quote(branch,safe="")
    qpath=urllib.parse.quote(path,safe="/")
    status,response=_json_request(
        "GET",
        f"https://api.github.com/repos/{repo}/contents/{qpath}?ref={qbranch}",
        token,
        None,
    )
    if status!=200 or not isinstance(response,Mapping):
        return status,None,None
    encoded=str(response.get("content") or "").replace("\n","")
    try:
        raw=base64.b64decode(encoded,validate=True)
    except Exception:
        return status,None,None
    return status,raw,str(response.get("sha") or "")


def persist_result_durable(
    *,
    repo:str,
    token:str,
    branch:str,
    path:str,
    content:Mapping[str,Any],
    attempts:int=5,
    put_fn:Callable[...,tuple[int,Mapping[str,Any]]]=put_result,
    get_fn:Callable[...,tuple[int,bytes|None,str|None]]=get_result_bytes,
    sleep_fn:Callable[[float],Any]=time.sleep,
    emit_recovery:bool=True,
):
    if attempts<1:
        raise ProductionLaunchError("RESULT_PERSISTENCE_ATTEMPTS_INVALID")
    raw=_result_bytes(content)
    if emit_recovery:
        print("UNKNOWN_DOMAIN_RESULT_RECOVERY_B64_V1="+base64.b64encode(raw).decode(),flush=True)
    last_status=None
    for attempt in range(attempts):
        status,response=put_fn(repo,token,branch,path,content)
        last_status=status
        if status==201 and isinstance(response,Mapping):
            commit=response.get("commit")
            commit_sha=str(commit.get("sha") or "") if isinstance(commit,Mapping) else ""
            if len(commit_sha)==40:
                return {
                    "status":"DURABLE_CREATED",
                    "attempts":attempt+1,
                    "commit_sha":commit_sha,
                    "content_sha":"",
                }
        check_status,existing,content_sha=get_fn(repo,token,branch,path)
        if check_status==200 and existing==raw:
            return {
                "status":"DURABLE_VERIFIED_EXISTING",
                "attempts":attempt+1,
                "commit_sha":"",
                "content_sha":str(content_sha or ""),
            }
        if attempt+1<attempts:
            sleep_fn(float(min(2**attempt,8)))
    raise ProductionLaunchError("RESULT_DURABILITY_NOT_ESTABLISHED:"+str(last_status))


def lease_bytes_and_digest(path:Path=LEASE_PATH):
    raw=path.read_bytes()
    return raw,hashlib.sha256(raw).hexdigest()


def validate_lease(lease:Mapping[str,Any],digest:str)->None:
    if lease.get("schema")!="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_V1":
        raise ProductionLaunchError("LEASE_SCHEMA_INVALID")
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
    if response_ref!=claim_ref or len(obj_sha)!=40:
        raise ProductionLaunchError("ATOMIC_CLAIM_RESPONSE_INVALID")
    result=dict(execute_fn(claim_id=claim_ref))
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
    result["execution_lease_sha256"]=digest
    result["execution_lease_git_blob_sha"]=_git_blob(raw)
    result["launch_ref"]="refs/heads/"+ref_name
    result_path=RESULT_PREFIX+digest.upper()+"_V1.json"
    persistence=persist_result_durable(
        repo=repo,token=token,branch=claim_branch,path=result_path,content=result
    )
    commit_sha=str(persistence.get("commit_sha") or "")
    print(json.dumps({
        "status":result["status"],
        "claim_ref":"refs/heads/"+claim_branch,
        "claim_create_http_status":201,
        "production_cases_generated":27,
        "all_27_cases_pass":result["aggregate"].get("all_27_cases_pass"),
        "result_path":result_path,
        "result_commit_sha":commit_sha,
        "result_persistence_status":persistence.get("status"),
        "result_persistence_attempts":persistence.get("attempts"),
        "result_content_sha":persistence.get("content_sha"),
    },sort_keys=True))


if __name__=="__main__":
    main()
