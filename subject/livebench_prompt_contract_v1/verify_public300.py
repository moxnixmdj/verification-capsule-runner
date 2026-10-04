#!/usr/bin/env python3
from __future__ import annotations
import collections, hashlib, importlib.util, json, os, pathlib, subprocess, sys, tempfile, types, urllib.request, zipfile

ROOT=pathlib.Path(__file__).resolve().parent
SOLVER=ROOT/"livebench_prompt_contract_synthesizer_v1.py"
RATIO=ROOT/"livebench_ratio_reference_free_constructor_v1.py"
EXPECTED={
    "solver":"4ccda5d7b15b6bdc05caed571a9f60c68039c24a",
    "ratio":"b7fc14cb8ba707cf20d07c2d0d1d5cc891558164",
}
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
IFBENCH_URL="https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_BLOB="a8e343ed928d8b4e649b9dba651fed7757ccacc3"
NLTK_COMMIT="550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"
NLTK_FILES=[
    "packages/tokenizers/punkt.zip",
    "packages/tokenizers/punkt_tab.zip",
    "packages/corpora/stopwords.zip",
    "packages/taggers/averaged_perceptron_tagger.zip",
    "packages/taggers/averaged_perceptron_tagger_eng.zip",
]

def blob_bytes(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def blob_path(p:pathlib.Path)->str:
    return blob_bytes(p.read_bytes())
def fetch(url:str)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req,timeout=60) as h:
        return h.read()
def load_subject():
    assert blob_path(SOLVER)==EXPECTED["solver"],(blob_path(SOLVER),EXPECTED["solver"])
    assert blob_path(RATIO)==EXPECTED["ratio"],(blob_path(RATIO),EXPECTED["ratio"])
    canonical=types.ModuleType("canonical"); canonical.__path__=[]
    runtime=types.ModuleType("canonical.runtime"); runtime.__path__=[]
    canonical.runtime=runtime
    sys.modules["canonical"]=canonical
    sys.modules["canonical.runtime"]=runtime
    name="canonical.runtime.livebench_ratio_reference_free_constructor_v1"
    spec=importlib.util.spec_from_file_location(name,RATIO); mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod; setattr(runtime,"livebench_ratio_reference_free_constructor_v1",mod); spec.loader.exec_module(mod)
    name2="canonical.runtime.livebench_prompt_contract_synthesizer_v1"
    spec2=importlib.util.spec_from_file_location(name2,SOLVER); solver=importlib.util.module_from_spec(spec2)
    sys.modules[name2]=solver; setattr(runtime,"livebench_prompt_contract_synthesizer_v1",solver); spec2.loader.exec_module(solver)
    return solver
def prepare_nltk(base:pathlib.Path):
    data=base/"nltk_data"; data.mkdir()
    for rel in NLTK_FILES:
        raw=fetch(f"https://raw.githubusercontent.com/nltk/nltk_data/{NLTK_COMMIT}/{rel}")
        zpath=base/pathlib.Path(rel).name; zpath.write_bytes(raw)
        sub=rel.split("/")[1]; target=data/sub; target.mkdir(exist_ok=True)
        with zipfile.ZipFile(zpath) as z: z.extractall(target)
    os.environ["NLTK_DATA"]=str(data)
def clone_livebench(base:pathlib.Path)->pathlib.Path:
    dst=base/"LiveBench"
    subprocess.run(["git","clone","--quiet","--filter=blob:none","--no-checkout","https://github.com/LiveBench/LiveBench.git",str(dst)],check=True)
    subprocess.run(["git","-C",str(dst),"fetch","--quiet","--depth=1","origin",LIVEBENCH_COMMIT],check=True)
    subprocess.run(["git","-C",str(dst),"checkout","--quiet","--detach",LIVEBENCH_COMMIT],check=True)
    head=subprocess.check_output(["git","-C",str(dst),"rev-parse","HEAD"],text=True).strip()
    assert head==LIVEBENCH_COMMIT,(head,LIVEBENCH_COMMIT)
    return dst

def main()->int:
    solver=load_subject()
    raw=fetch(IFBENCH_URL)
    assert blob_bytes(raw)==IFBENCH_BLOB,(blob_bytes(raw),IFBENCH_BLOB)
    rows=[json.loads(x) for x in raw.decode().splitlines() if x.strip()]
    assert len(rows)==300
    with tempfile.TemporaryDirectory(prefix="lb-public300-") as td:
        base=pathlib.Path(td)
        prepare_nltk(base)
        lb=clone_livebench(base)
        sys.path.insert(0,str(lb))
        from livebench.if_runner.ifbench import evaluation_lib

        total=0.0; full=0; recognized=0; exceptions=0
        by_id=collections.defaultdict(lambda:{"n":0,"recognized":0,"full":0,"score":0.0})
        by_route=collections.Counter()
        blocked=collections.Counter()
        for row in rows:
            ids=list(row.get("instruction_id_list") or [])
            assert ids
            iid="|".join(ids)
            st=by_id[iid]; st["n"]+=1
            out=solver.synthesize(row["prompt"])
            if out.get("status")!="PASS":
                blocked[str(out.get("reason"))]+=1
                continue
            recognized+=1; st["recognized"]+=1
            by_route[str(out.get("route"))]+=1
            try:
                inp=evaluation_lib.InputExample(
                    key=row["key"],
                    instruction_id_list=ids,
                    prompt=row["prompt"],
                    kwargs=[dict(x or {}) for x in row["kwargs"]],
                )
                result=evaluation_lib.test_instruction_following_strict(inp,str(out["response"]))
                k=len(result.follow_instruction_list)
                g=sum(bool(x) for x in result.follow_instruction_list)
                score=((1.0 if result.follow_all_instructions else 0.0)+(g/k))/2.0
            except Exception as exc:
                exceptions+=1
                blocked["SCORER_EXCEPTION:"+type(exc).__name__]+=1
                score=0.0
                result=None
            total+=score; st["score"]+=score
            if result is not None and result.follow_all_instructions:
                full+=1; st["full"]+=1

        mean=total/len(rows)
        receipt={
            "schema":"PROJECT_BRAIN_LIVEBENCH_PROMPT_CONTRACT_PUBLIC300_EXACT_SCORER_VERIFICATION_V1",
            "status":"PASS",
            "subject_git_blobs":EXPECTED,
            "source_livebench_commit":LIVEBENCH_COMMIT,
            "source_ifbench_git_blob":IFBENCH_BLOB,
            "public_cases":len(rows),
            "recognized_cases":recognized,
            "full_pass_cases":full,
            "scorer_exceptions":exceptions,
            "score_mass":total,
            "mean_score":mean,
            "mean_percent":100.0*mean,
            "ge_65_7_on_public300":mean>=0.657,
            "route_counts":dict(sorted(by_route.items())),
            "blocked_counts":dict(sorted(blocked.items())),
            "instruction_summary":{k:{
                "n":v["n"],"recognized":v["recognized"],"full":v["full"],
                "mean_score":v["score"]/v["n"] if v["n"] else 0.0,
            } for k,v in sorted(by_id.items())},
            "hard_nonclaims":[
                "PUBLIC_300_PREQUALIFICATION_IS_NOT_THE_FROZEN_200_CASE_TERMINAL_SCORE",
                "NO_UNEXPOSED_TERMINAL_LIVEBENCH_CASES_WERE_READ",
                "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            ],
            "accounting":{"incremental_spend_usd":0,"terminal_cases_consumed":0,"acceptance_credit_delta":0},
        }
        pathlib.Path("livebench_prompt_contract_public300_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
        print(json.dumps(receipt,sort_keys=True))
        # The verifier itself must be trustworthy even if the candidate score is poor.
        assert recognized>0
        assert exceptions==0
    return 0
if __name__=="__main__":
    raise SystemExit(main())
