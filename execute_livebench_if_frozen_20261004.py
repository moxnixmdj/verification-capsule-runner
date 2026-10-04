#!/usr/bin/env python3
from __future__ import annotations
import argparse, ast, hashlib, importlib, importlib.metadata, json, os, pathlib, re, shutil, subprocess, sys, tempfile, urllib.request
from collections import Counter, defaultdict

ROOT=pathlib.Path(__file__).resolve().parent
TARGET_RELEASE="2026-06-25"
TARGET_THRESHOLD=65.7
TARGET_COUNT=200
TASKS=("paraphrase","simplify","story_generation","summarize")
DATASET_URL="https://huggingface.co/datasets/livebench/instruction_following/resolve/0868379c4b5cf62aeacaf8be4f08fced815c81bb/data/test-00000-of-00001.parquet"
DATASET_SHA256="a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
ACTIVATION=("subject/livebench_direct_authority_activation_v1/activation.json","08929577573866dc2bead65a19a856a6b4e152d2")
BLOBS={
 "astra_runtime":("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/astra_runtime.py","7f5d16b1db69cb620954bc778e0ba6e15e687b75"),
 "adapter":("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py","7e3885fa7a6e56df656c066e0a8f17cfa21424e7"),
 "goal_compiler":("canonical/runtime/goal_compiler.py","4b61fe911471854ec15c7900816f61e9e55f602e"),
 "bound_registry":("canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json","7badee4878700f2cd4176beb8319d2a6a0bdf782"),
 "capability_planner":("canonical/runtime/capability_planner.py","64ff65cb184f50d3336326f33cccfcc0a53301a8"),
 "capability_proposal_generators":("canonical/runtime/capability_proposal_generators.py","71f2bbfda66a65d8d75e035b9ae073671ebd56e2"),
}
SCORER_BLOBS={
 "livebench/if_runner/ifbench/evaluation_lib.py":"2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
 "livebench/if_runner/ifbench/instructions.py":"02b2dfeb50f036b89bec3df34522c73f756d8f44",
 "livebench/if_runner/ifbench/instructions_registry.py":"adfed4832877566e62970257b50c6fa32c302fb2",
 "livebench/if_runner/ifbench/instructions_util.py":"21b13c7fcfc2c2de01e80c9e7dd222b9bca81342",
 "livebench/process_results/instruction_following/utils.py":"8ce01747887ec0792c8f024e1972e34ece781676",
}
RELEASES={"2024-06-24","2024-07-26","2024-08-31","2024-11-25","2025-04-02","2025-04-25","2025-05-30","2025-11-25","2025-12-23","2026-01-08","2026-06-25"}

def git_blob_sha(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def sha256_file(path:pathlib.Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()

def point_of_use_preflight()->dict:
    errors=[]
    if sys.version_info[:2]!=(3,12):
        errors.append("PYTHON_VERSION_MISMATCH:"+sys.version.split()[0])
    if str(os.environ.get("GITHUB_ACTIONS","")).lower()!="true":
        errors.append("NOT_GITHUB_ACTIONS")
    if str(os.environ.get("RUNNER_OS",""))!="Linux":
        errors.append("RUNNER_OS_NOT_LINUX")
    if str(os.environ.get("REPOSITORY_PRIVATE","")).lower()!="false":
        errors.append("PUBLIC_REPOSITORY_CONTEXT_NOT_PROVED")
    ap,asha=ACTIVATION
    p=ROOT/ap
    if not p.is_file() or git_blob_sha(p)!=asha:
        errors.append("ACTIVATION_BLOB_MISMATCH")
    else:
        a=json.loads(p.read_text(encoding="utf-8"))
        if a.get("active") is not True: errors.append("ACTIVATION_NOT_ACTIVE")
        auth=a.get("authority") or {}
        if auth.get("execution") is not True or auth.get("predicate_local_fresh_reality") is not True:
            errors.append("SCOPED_EXECUTION_AUTHORITY_NOT_ACTIVE")
        if auth.get("global_fresh_reality") is not False:
            errors.append("GLOBAL_FRESH_REALITY_MUST_REMAIN_FALSE")
        if a.get("authorized_predicates")!=["LIVEBENCH_IF_GE_65_7"]:
            errors.append("AUTHORIZED_PREDICATE_SCOPE_DRIFT")
    actual={}
    for key,(rel,want) in BLOBS.items():
        p=ROOT/rel
        if not p.is_file():
            errors.append("MISSING_RUNTIME_BLOB:"+key); continue
        got=git_blob_sha(p); actual[key]=got
        if got!=want: errors.append("RUNTIME_BLOB_MISMATCH:"+key)
    for pkg,ver in {
      "nltk":"3.10.3","emoji":"2.16.0","syllapy":"0.7.2",
      "setuptools":"80.9.0","spacy":"3.8.16","en-core-web-sm":"3.8.0",
      "pyarrow":"21.0.0",
    }.items():
        try: got=importlib.metadata.version(pkg)
        except Exception: got=None
        if got!=ver: errors.append("PACKAGE_VERSION_MISMATCH:"+pkg+":"+str(got))
    return {"pass":not errors,"errors":errors,"runtime_blobs":actual}

def clone_livebench(dst:pathlib.Path):
    subprocess.run(["git","init",str(dst)],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","-C",str(dst),"remote","add","origin","https://github.com/LiveBench/LiveBench.git"],check=True)
    subprocess.run(["git","-C",str(dst),"fetch","--depth","1","origin",LIVEBENCH_COMMIT],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","-C",str(dst),"checkout","--detach","FETCH_HEAD"],check=True,stdout=subprocess.DEVNULL)
    got=subprocess.check_output(["git","-C",str(dst),"rev-parse","HEAD"],text=True).strip()
    if got!=LIVEBENCH_COMMIT: raise RuntimeError("LIVEBENCH_COMMIT_MISMATCH")
    for rel,want in SCORER_BLOBS.items():
        got=subprocess.check_output(["git","-C",str(dst),"hash-object",rel],text=True).strip()
        if got!=want: raise RuntimeError("SCORER_BLOB_MISMATCH:"+rel+":"+got)

def load_score_results_function(utils_path:pathlib.Path):
    tree=ast.parse(utils_path.read_text(encoding="utf-8"),filename=str(utils_path))
    target=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="score_results"]
    if len(target)!=1: raise RuntimeError("SCORE_RESULTS_FUNCTION_NOT_UNIQUE")
    mod=ast.Module(body=target,type_ignores=[])
    ns={}
    exec(compile(mod,str(utils_path),"exec"),ns,ns)
    return ns["score_results"]

def materialize_candidate(temp:pathlib.Path):
    (temp/"canonical/runtime").mkdir(parents=True)
    (temp/"canonical/__init__.py").write_text("",encoding="utf-8")
    (temp/"canonical/runtime/__init__.py").write_text("",encoding="utf-8")
    mapping={
      BLOBS["astra_runtime"][0]:"canonical/runtime/astra_runtime.py",
      BLOBS["adapter"][0]:"canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py",
      BLOBS["goal_compiler"][0]:"canonical/runtime/goal_compiler.py",
      BLOBS["bound_registry"][0]:"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
      BLOBS["capability_planner"][0]:"canonical/runtime/capability_planner.py",
      BLOBS["capability_proposal_generators"][0]:"canonical/runtime/capability_proposal_generators.py",
    }
    for src,dst in mapping.items():
        q=temp/dst; q.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/src,q)

def norm_date(v):
    if v in (None,""): return ""
    if hasattr(v,"strftime"): return v.strftime("%Y-%m-%d")
    return str(v)

def normalize_obj(v):
    if isinstance(v,dict): return {k:normalize_obj(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)): return [normalize_obj(x) for x in v]
    if hasattr(v,"strftime"): return v.strftime("%Y-%m-%d")
    return v

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="livebench_if_frozen_20261004_result.json")
    args=ap.parse_args()

    pre=point_of_use_preflight()
    if not pre["pass"]:
        print(json.dumps({"status":"FAIL_CLOSED_PREFLIGHT","preflight":pre},sort_keys=True))
        return 2

    # Terminal-case content is not touched until every point-of-use gate above passes.
    lb=pathlib.Path("/tmp/LiveBench-production")
    if lb.exists(): shutil.rmtree(lb)
    clone_livebench(lb)

    dataset=pathlib.Path("/tmp/livebench_instruction_following_frozen.parquet")
    with urllib.request.urlopen(DATASET_URL,timeout=60) as r, dataset.open("wb") as f:
        shutil.copyfileobj(r,f)
    if sha256_file(dataset)!=DATASET_SHA256:
        raise RuntimeError("DATASET_SHA256_MISMATCH")

    import pyarrow.parquet as pq
    rows=[normalize_obj(x) for x in pq.read_table(dataset).to_pylist()]
    active=[]
    for row in rows:
        rd=norm_date(row.get("livebench_release_date"))
        rem=norm_date(row.get("livebench_removal_date"))
        if rd in RELEASES and (rem=="" or rem>TARGET_RELEASE) and row.get("task") in TASKS:
            active.append(row)
    active.sort(key=lambda r:(str(r.get("task")),str(r.get("question_id"))))
    counts=Counter(str(r.get("task")) for r in active)
    if len(active)!=TARGET_COUNT or counts!=Counter({x:50 for x in TASKS}):
        raise RuntimeError("ACTIVE_POPULATION_MISMATCH:"+repr(counts)+":"+str(len(active)))
    ids=[str(r.get("question_id")) for r in active]
    if len(ids)!=len(set(ids)):
        raise RuntimeError("DUPLICATE_QUESTION_IDS")
    for row in active:
        turns=row.get("turns")
        if not isinstance(turns,list) or len(turns)!=1 or not isinstance(turns[0],str) or not turns[0].strip():
            raise RuntimeError("UNSUPPORTED_TURN_SHAPE:"+str(row.get("question_id")))
        if str(row.get("system_prompt") or "").strip():
            raise RuntimeError("NONEMPTY_SYSTEM_PROMPT_UNSUPPORTED:"+str(row.get("question_id")))
        if not isinstance(row.get("instruction_id_list"),list) or not isinstance(row.get("kwargs"),list):
            raise RuntimeError("IFBENCH_FIELDS_MISSING:"+str(row.get("question_id")))

    sys.path.insert(0,str(lb))
    from livebench.if_runner.ifbench import evaluation_lib
    score_results=load_score_results_function(lb/"livebench/process_results/instruction_following/utils.py")

    with tempfile.TemporaryDirectory(prefix="brain-livebench-prod-") as td:
        temp=pathlib.Path(td)
        materialize_candidate(temp)
        old_path=list(sys.path)
        try:
            sys.path.insert(0,str(temp))
            for name in list(sys.modules):
                if name=="canonical" or name.startswith("canonical."):
                    sys.modules.pop(name,None)
            adapter=importlib.import_module("canonical.runtime.root2_livebench_if_astra_inference_adapter_v1")
            receipts=[]
            scores=[]
            task_scores=defaultdict(list)
            for idx,row in enumerate(active):
                qid=str(row["question_id"])
                prompt=row["turns"][0]
                error=None
                answer=""
                trace_types=[]
                try:
                    out=adapter.infer({
                      "benchmark_id":"LIVEBENCH_IF_2026_06_25",
                      "task_id":qid,
                      "allowed_tools":[],
                      "task_payload":{"instruction":prompt},
                    })
                    if out.get("cognition_dependency_class")!="MODEL_INDEPENDENT" or int(out.get("model_dependency_count",-1))!=0:
                        raise RuntimeError("MODEL_DEPENDENCY_FORBIDDEN")
                    answer=str(out.get("answer") or "")
                    trace_types=[str((x.get("plan") or {}).get("type") or "") for x in (out.get("tool_trace") or []) if isinstance(x,dict)]
                    inp=evaluation_lib.InputExample(
                        key=row.get("key",row.get("question_id",0)),
                        instruction_id_list=row["instruction_id_list"],
                        prompt=prompt,
                        kwargs=[dict(x) for x in row["kwargs"]],
                    )
                    # Exact pinned IF result semantics: strip optional solution tags, strict checker,
                    # then the exact score_results function extracted from pinned upstream source.
                    m=re.search(r"<solution>(.*?)</solution>",answer,re.DOTALL)
                    response=m.group(1).strip() if m else answer.strip()
                    judged=evaluation_lib.test_instruction_following_strict(inp,response)
                    score=float(score_results(judged.follow_all_instructions,judged.follow_instruction_list))
                except BaseException as exc:
                    error=type(exc).__name__+":"+str(exc)
                    score=0.0
                scores.append(score)
                task=str(row["task"]); task_scores[task].append(score)
                receipts.append({
                  "ordinal":idx,
                  "question_id":qid,
                  "task":task,
                  "prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),
                  "response_sha256":hashlib.sha256(answer.encode()).hexdigest(),
                  "score":score,
                  "error":error,
                  "trace_types":trace_types,
                  "candidate_commit":"d5de4f5808dced840da34d051e3f9a5ff06e2e54",
                })
        finally:
            sys.path[:]=old_path

    per_task={k:(sum(v)/len(v))*100.0 for k,v in sorted(task_scores.items())}
    score_percent=(sum(scores)/len(scores))*100.0
    # Equal 50-case task populations make this identical to the arithmetic mean of task means.
    task_mean=sum(per_task.values())/len(TASKS)
    if abs(task_mean-score_percent)>1e-9:
        raise RuntimeError("AGGREGATION_IDENTITY_FAILURE")

    result={
      "schema":"PROJECT_BRAIN_LIVEBENCH_IF_FROZEN_2026_06_25_DIRECT_RESULT_V1",
      "status":"PASS_EXECUTION_COMPLETE",
      "target_predicate":"LIVEBENCH_IF_GE_65_7",
      "candidate_commit":"d5de4f5808dced840da34d051e3f9a5ff06e2e54",
      "benchmark_id":"LIVEBENCH_IF_2026_06_25",
      "dataset_revision":"0868379c4b5cf62aeacaf8be4f08fced815c81bb",
      "dataset_sha256":DATASET_SHA256,
      "population_count":len(scores),
      "task_counts":dict(sorted(counts.items())),
      "per_task_score_percent":per_task,
      "score_percent":score_percent,
      "threshold_percent":TARGET_THRESHOLD,
      "threshold_pass":score_percent>=TARGET_THRESHOLD,
      "error_case_count":sum(1 for x in receipts if x["error"] is not None),
      "case_receipts":receipts,
      "cognition_dependency_class":"MODEL_INDEPENDENT",
      "paid_external_model_or_api_used":False,
      "incremental_spend_usd":0,
      "terminal_cases_consumed":TARGET_COUNT,
      "adaptive_case_selection":False,
      "case_replacement":False,
      "terminal_case_tuning":False,
      "promotion_authority":False,
      "acceptance_credit_delta":0,
    }
    outp=pathlib.Path(args.output)
    outp.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result_sha=sha256_file(outp)
    print("LIVEBENCH_FROZEN_RESULT_SHA256="+result_sha)
    print("LIVEBENCH_SCORE_PERCENT="+format(score_percent,".12f"))
    print("LIVEBENCH_THRESHOLD_PERCENT="+format(TARGET_THRESHOLD,".1f"))
    print("LIVEBENCH_THRESHOLD_PASS="+("true" if result["threshold_pass"] else "false"))
    print("LIVEBENCH_ERROR_CASE_COUNT="+str(result["error_case_count"]))
    print("LIVEBENCH_POPULATION_COUNT="+str(result["population_count"]))
    print("LIVEBENCH_PER_TASK="+json.dumps(per_task,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
