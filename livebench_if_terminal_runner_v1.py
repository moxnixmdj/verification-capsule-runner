#!/usr/bin/env python3
from __future__ import annotations
import collections, gzip, hashlib, importlib, json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
BENCHMARK_ID="LIVEBENCH_IF_2026_06_25"
THRESHOLD=65.7
DATA_REV="0868379c4b5cf62aeacaf8be4f08fced815c81bb"
DATA_SHA256="a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
DATA_BYTES=537024
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
TASKS=("paraphrase","simplify","story_generation","summarize")
CANDIDATE_COMMIT="d5de4f5808dced840da34d051e3f9a5ff06e2e54"

EXPECTED={
 "astra":("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/astra_runtime.py","7f5d16b1db69cb620954bc778e0ba6e15e687b75"),
 "adapter":("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py","7e3885fa7a6e56df656c066e0a8f17cfa21424e7"),
 "entrypoint":("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_external_task_entrypoint_v1.py","603beefe0db24102b86b7c965e5433bd880392af"),
 "goal_compiler":("canonical/runtime/goal_compiler.py","4b61fe911471854ec15c7900816f61e9e55f602e"),
 "bound_registry":("canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json","7badee4878700f2cd4176beb8319d2a6a0bdf782"),
 "capability_planner":("canonical/runtime/capability_planner.py","64ff65cb184f50d3336326f33cccfcc0a53301a8"),
 "proposal_generators":("canonical/runtime/capability_proposal_generators.py","71f2bbfda66a65d8d75e035b9ae073671ebd56e2"),
 "response_adapter":("subject/livebench_zero_case_resource_fit_20261004/livebench_if_response_adapter.py","eb497ae5585f4f22b06b8088609b6d17714ebc53"),
}
SCORER_BLOBS={
 "livebench/if_runner/ifbench/evaluation_lib.py":"2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
 "livebench/if_runner/ifbench/instructions.py":"02b2dfeb50f036b89bec3df34522c73f756d8f44",
 "livebench/if_runner/ifbench/instructions_registry.py":"adfed4832877566e62970257b50c6fa32c302fb2",
 "livebench/if_runner/ifbench/instructions_util.py":"21b13c7fcfc2c2de01e80c9e7dd222b9bca81342",
 "livebench/process_results/instruction_following/utils.py":"8ce01747887ec0792c8f024e1972e34ece781676",
}
RELEASES={"2024-07-26","2024-06-24","2024-08-31","2024-11-25","2025-04-02","2025-04-25","2025-05-30","2025-11-25","2025-12-23","2026-01-08","2026-06-25"}

def git_blob(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def sha256(path:pathlib.Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def copy_runtime(dst:pathlib.Path)->None:
    mapping={
      EXPECTED["astra"][0]:"canonical/runtime/astra_runtime.py",
      EXPECTED["adapter"][0]:"canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py",
      EXPECTED["entrypoint"][0]:"canonical/runtime/root2_external_task_entrypoint_v1.py",
      EXPECTED["goal_compiler"][0]:"canonical/runtime/goal_compiler.py",
      EXPECTED["bound_registry"][0]:"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
      EXPECTED["capability_planner"][0]:"canonical/runtime/capability_planner.py",
      EXPECTED["proposal_generators"][0]:"canonical/runtime/capability_proposal_generators.py",
      EXPECTED["response_adapter"][0]:"canonical/runtime/livebench_if_response_adapter.py",
    }
    for src_rel,out_rel in mapping.items():
        out=dst/out_rel
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/src_rel,out)
    (dst/"canonical/__init__.py").write_text("",encoding="utf-8")
    (dst/"canonical/runtime/__init__.py").write_text("",encoding="utf-8")
    (dst/"canonical/astra_runtime/state").mkdir(parents=True,exist_ok=True)
    (dst/"canonical/astra_runtime/evidence").mkdir(parents=True,exist_ok=True)

def run_one(runtime_template:pathlib.Path,q:dict)->dict:
    with tempfile.TemporaryDirectory(prefix="livebench-case-") as td:
        wd=pathlib.Path(td)
        shutil.copytree(runtime_template/"canonical",wd/"canonical")
        payload={"benchmark_id":BENCHMARK_ID,"task_id":str(q["question_id"]),"task_payload":{"instruction":q["turns"][0]},"allowed_tools":[]}
        driver=wd/"run_case.py"
        driver.write_text(
            "import json,sys\n"
            "from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as a\n"
            "req=json.load(sys.stdin)\n"
            "try:\n"
            " out=a.infer(req); print(json.dumps({'ok':True,'out':out},ensure_ascii=False))\n"
            "except BaseException as e:\n"
            " print(json.dumps({'ok':False,'error':type(e).__name__+':'+str(e)},ensure_ascii=False))\n",
            encoding="utf-8",
        )
        p=subprocess.run([sys.executable,str(driver)],input=json.dumps(payload,ensure_ascii=False),text=True,capture_output=True,cwd=wd,timeout=120)
        lines=[x for x in p.stdout.splitlines() if x.strip()]
        if not lines:
            return {"ok":False,"error":"NO_JSON_OUTPUT","stderr":p.stderr[-4000:]}
        try:
            obj=json.loads(lines[-1])
        except Exception:
            return {"ok":False,"error":"INVALID_JSON_OUTPUT","stdout":p.stdout[-4000:],"stderr":p.stderr[-4000:]}
        if p.returncode!=0:
            obj={"ok":False,"error":"SUBPROCESS_NONZERO:"+str(p.returncode)+":"+str(obj.get("error") or ""), "stderr":p.stderr[-4000:]}
        return obj

def norm_date(x):
    if x is None:return ""
    if hasattr(x,"strftime"):return x.strftime("%Y-%m-%d")
    return str(x)[:10]

def main()->int:
    errors=[]
    if os.environ.get("GITHUB_ACTIONS")!="true": errors.append("NOT_GITHUB_ACTIONS")
    if str(os.environ.get("REPOSITORY_PRIVATE","")).lower()!="false": errors.append("REPOSITORY_NOT_PUBLIC")
    if sys.version_info[:2]!=(3,12): errors.append("PYTHON_VERSION_NOT_3_12")

    activation=json.loads((ROOT/"subject/livebench_direct_authority_activation_v1/activation.json").read_text(encoding="utf-8"))
    if activation.get("active") is not True: errors.append("AUTHORITY_NOT_ACTIVE")
    if activation.get("target_predicate")!="LIVEBENCH_IF_GE_65_7": errors.append("AUTHORITY_TARGET_MISMATCH")
    auth=activation.get("authority") or {}
    if auth.get("execution") is not True or auth.get("predicate_local_fresh_reality") is not True:
        errors.append("PREDICATE_LOCAL_EXECUTION_AUTHORITY_FALSE")
    eb=activation.get("exact_execution_binding") or {}
    for k,v in {"candidate_commit":CANDIDATE_COMMIT,"benchmark_id":BENCHMARK_ID,"population_count":200,"threshold_percent":THRESHOLD}.items():
        if eb.get(k)!=v: errors.append("ACTIVATION_BINDING_MISMATCH:"+k)

    observed={}
    for key,(rel,want) in EXPECTED.items():
        p=ROOT/rel
        if not p.is_file():
            errors.append("MISSING_RUNTIME:"+key); continue
        got=git_blob(p); observed[key]=got
        if got!=want: errors.append("RUNTIME_BLOB_MISMATCH:"+key+":"+got+":"+want)

    with tempfile.TemporaryDirectory(prefix="livebench-preflight-") as td:
        runtime_template=pathlib.Path(td)
        copy_runtime(runtime_template)
        synthetic={"question_id":"synthetic","turns":["Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json. Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json."]}
        syn=run_one(runtime_template,synthetic)
        if not syn.get("ok"): errors.append("POINT_OF_USE_SYNTHETIC_PREFLIGHT_FAIL:"+str(syn.get("error")))
        else:
            out=syn["out"]
            if out.get("status")!="PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE": errors.append("SYN_STATUS")
            if out.get("cognition_dependency_class")!="MODEL_INDEPENDENT": errors.append("SYN_COGNITION_DEP")
            if int(out.get("model_dependency_count",-1))!=0: errors.append("SYN_MODEL_DEP_COUNT")
        if errors:
            print(json.dumps({"status":"FAIL_CLOSED_PREEXPOSURE","errors":errors},indent=2,sort_keys=True))
            return 2

        lb=pathlib.Path(td)/"LiveBench"
        subprocess.run(["git","clone","-q","https://github.com/LiveBench/LiveBench.git",str(lb)],check=True)
        subprocess.run(["git","-C",str(lb),"checkout","-q",LIVEBENCH_COMMIT],check=True)
        for rel,want in SCORER_BLOBS.items():
            got=subprocess.check_output(["git","-C",str(lb),"rev-parse","HEAD:"+rel],text=True).strip()
            if got!=want: raise RuntimeError("SCORER_BLOB_MISMATCH:"+rel+":"+got+":"+want)

        data=pathlib.Path(td)/"instruction_following.parquet"
        url=f"https://huggingface.co/datasets/livebench/instruction_following/resolve/{DATA_REV}/data/test-00000-of-00001.parquet?download=true"
        subprocess.run(["curl","-fL","--retry","3","-o",str(data),url],check=True)
        if data.stat().st_size!=DATA_BYTES: raise RuntimeError("DATA_SIZE_MISMATCH:"+str(data.stat().st_size))
        got_data_sha=sha256(data)
        if got_data_sha!=DATA_SHA256: raise RuntimeError("DATA_SHA256_MISMATCH:"+got_data_sha)

        import pyarrow.parquet as pq
        rows=pq.read_table(data).to_pylist()
        qids=[str(r["question_id"]) for r in rows]
        if len(qids)!=len(set(qids)): raise RuntimeError("DUPLICATE_QUESTION_IDS")
        active=[]
        for r in rows:
            rd=norm_date(r.get("livebench_release_date"))
            removal=norm_date(r.get("livebench_removal_date"))
            if rd in RELEASES and (not removal or removal>"2026-06-25"):
                active.append(r)
        counts=collections.Counter(str(r["task"]) for r in active)
        if set(counts)!=set(TASKS) or any(counts[t]!=50 for t in TASKS) or len(active)!=200:
            raise RuntimeError("ACTIVE_POPULATION_MISMATCH:"+json.dumps(counts,sort_keys=True)+":"+str(len(active)))
        active.sort(key=lambda r:(str(r["task"]),str(r["question_id"])))

        responses=[]
        for idx,q in enumerate(active,1):
            rr=run_one(runtime_template,q)
            if rr.get("ok"):
                out=rr["out"]; answer=str(out.get("answer") or "")
                row={"question_id":q["question_id"],"task":q["task"],"ok":True,"response":answer,"response_sha256":hashlib.sha256(answer.encode("utf-8")).hexdigest(),"cognition_dependency_class":out.get("cognition_dependency_class"),"model_dependency_count":out.get("model_dependency_count"),"trace":out.get("tool_trace") or []}
            else:
                row={"question_id":q["question_id"],"task":q["task"],"ok":False,"response":"","response_sha256":hashlib.sha256(b"").hexdigest(),"error":rr.get("error")}
            responses.append(row)
            if idx%25==0: print("RESPONSES_GENERATED",idx,flush=True)

        sys.path.insert(0,str(lb))
        evaluation_lib=importlib.import_module("livebench.if_runner.ifbench.evaluation_lib")
        by_id={str(q["question_id"]):q for q in active}
        scores=[]
        for r in responses:
            q=by_id[str(r["question_id"])]
            if not r["ok"]:
                score=0.0; score_error="INFERENCE_FAILURE"
            else:
                try:
                    inp=evaluation_lib.InputExample(key=q.get("key",q.get("question_id",0)),instruction_id_list=q["instruction_id_list"],prompt=q["turns"][0],kwargs=q["kwargs"])
                    result=evaluation_lib.test_instruction_following_strict(inp,r["response"].strip())
                    frac=sum(1 if x else 0 for x in result.follow_instruction_list)/len(result.follow_instruction_list)
                    score=((1.0 if result.follow_all_instructions else 0.0)+frac)/2.0
                    score_error=None
                except BaseException as exc:
                    score=0.0; score_error=type(exc).__name__+":"+str(exc)
            r["score"]=score
            if score_error:r["score_error"]=score_error
            scores.append(score)

        per_task={}
        for t in TASKS:
            xs=[r["score"] for r in responses if r["task"]==t]
            per_task[t]=100.0*sum(xs)/len(xs)
        percent=100.0*sum(scores)/len(scores)
        passed=percent>=THRESHOLD
        receipt={"schema":"PROJECT_BRAIN_LIVEBENCH_IF_TERMINAL_EXECUTION_RECEIPT_V1","date":"2026-10-04","status":"PASS_THRESHOLD" if passed else "FAIL_THRESHOLD","target_predicate":"LIVEBENCH_IF_GE_65_7","benchmark_id":BENCHMARK_ID,"candidate_commit":CANDIDATE_COMMIT,"livebench_commit":LIVEBENCH_COMMIT,"dataset_revision":DATA_REV,"dataset_sha256":got_data_sha,"population_count":len(active),"task_counts":dict(sorted(counts.items())),"threshold_percent":THRESHOLD,"brain_score_percent":percent,"per_task_percent":per_task,"threshold_pass":passed,"inference_failures":sum(1 for r in responses if not r["ok"]),"scorer_failures":sum(1 for r in responses if "score_error" in r and r["score_error"]!="INFERENCE_FAILURE"),"model_dependency_nonzero_cases":sum(1 for r in responses if r.get("model_dependency_count") not in (None,0)),"cognition_dependency_non_model_independent_cases":sum(1 for r in responses if r.get("cognition_dependency_class") not in (None,"MODEL_INDEPENDENT")),"all_200_responses_generated_before_scoring":True,"adaptive_case_selection":False,"case_replacement":False,"terminal_case_tuning":False,"paid_external_model_or_api_used":False,"incremental_spend_usd":0,"predicate_local_execution_authority_used":True,"global_fresh_reality_authority":False,"acceptance_credit_automatically_granted":False,"promotion_authority":False,"runtime_git_blobs":observed,"case_receipt_sha256":None}
        outdir=ROOT/"livebench_terminal_receipt_v1"; outdir.mkdir(exist_ok=True)
        cases_path=outdir/"cases.jsonl.gz"
        with gzip.open(cases_path,"wt",encoding="utf-8") as f:
            for row in responses:f.write(json.dumps(row,sort_keys=True,ensure_ascii=False)+"\n")
        receipt["case_receipt_sha256"]=sha256(cases_path)
        (outdir/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print("LIVEBENCH_TERMINAL_RECEIPT="+json.dumps(receipt,sort_keys=True))
        return 0

if __name__=="__main__":
    raise SystemExit(main())
