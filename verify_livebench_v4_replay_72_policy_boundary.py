#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, urllib.request
from diagnose_livebench_template_runtime_postrun_v2 import FILES, git_blob_sha

ROOT=pathlib.Path(__file__).resolve().parent
BENCHMARK_ID="LIVEBENCH_IF_2026_06_25"
DATASET_REV="0868379c4b5cf62aeacaf8be4f08fced815c81bb"
DATASET_SHA256="a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
DATASET_BYTES=537024
POPULATION=200
THRESHOLD_PERCENT=65.7
PREFIX_IDS_SHA256="89ad554201ed3def9d5358aa1f75e926335e32ed63be53c0796491b8d505a6ab"
PREFIX_IDS=[
"006d27d0a338a42a35e7d50e01bfd5b8e502897097c15ab7a4b01a6e38c6bf4b","02b82146fcd90e18dad8f8ef85bd5566a2c7540429fc8e03c73b98dac3f58cf4","0503923535fbd8badfb2ccf38989b36a8ecaa2eda332a4b515bb13932421fecd","05dd93ecefb22fdd5d3a5d396616c472436ffcebfa9c0d95fedda3ff661a11fa","0996be1780ea1ac0e68d98e0bed513b23ec11b212c3461884e28c3a752a00efc","0a0385df33f3d95602ab7f1a78de0bfc276cd8067d27336188e84341cdd02032","0b041d87e0bba1a5db140a69ef8fd4e844f1f0f0b86be7a6ceba5f9edf36d584","0cf5814b25d7aa0420a7d6d8f03e0ccd977c61fb996be04f8c3221153ba1f005","0e3720b5a1a1a2c62bbdf378ec61629fe6c93938afd69454e92e6b87ed9e9823","0f7d9c4e9e52b68d21b2c8a04f685bc992ea144fbf9b9e5441339ef29c40610f","0f90f3ed7d95e22249b1376b7f31afddcf5f6de2f813cd91d64f4f3c47bfb129","12511f1ecaf9b43b03990406cbc2634eb438a570f7083526de0a4ca894d64371","126dc38dc54c62e924d47a259e4236e596583c91d33ef6b22af272e9819c8201","13387ce0db59d53e6fad49b8356fcb3cb58cb4582bd299efd90b5eedbadb0f04","1597a46fa20861cb667a3233363762f3f6df6f4a51fd205fd6b496cfc3f47c09","15a04d320c993aaedd8e2e9918e71683f331884c84b5816719236f373f831e05","15c6b7596ca96c40d0c142303178478af8d3f9d0f780d2fbad65e0fa411970b7","177ccbc243d5867c5dfda52a0dde4585016747ec63e1d3bf8511f109258212ca","17854a4f3ee38888982a95aa5b240ed428714943c35b4ad185f754cebb5b29af","1a06f223c7988766f6c876404f04df808915b4bb08d1fca784eadec17e502973","1b09cc8158b5a64a86811f45c389ae6517d798b89640ad6c6059e98c7dd83b83","1b5fe52ce32803fee6244bb9f3af341e20f4ba1d91f7563d4ae906ef6edd51ce","1d5e9498696d690af72db04177e8469a9fc8adb1b85228735878a9650abd8ae7","1e722a1c202524599d7ba345986b4709bf662b6f8d7f54f9c018e9d9086c1830","1ed6a0a2c7b4b879b3f6b6bdc77f297735aae9c255fbd5210fb4b7bafce80aac","1f2f5fc2ab5a7a257d29e9cf4ddfee43ad6bc343122e11423f1f522912f940ff","1fb8a9d0877b746f95e08dc3e108563fc01d3248e8bb5000fabe88e1f6feaddd","21f4f5c292c5f8ce8c12f0c04b8919ea81af86717e6f03740e21437acf602bfc","257f9f71d60e6b2cd95f6b59d14a0fb876b74ff85708c64a3d95fe6eb7b41eaf","28225eb304ee633f078b9fb205f678e689ec92b0112d3d5f4f9c5d3391f5a67b","290ddccaf7a24527b8bcc08ea3e07ca14d86f7224c9ccbb03442da4efac0840b","2a31c6e6b5ec6b4327e64720d10df1cb390535a102652285ee32e2f07266835c","2c3f86f578e93981bec447960c57fc27daf35b6fd9eaeb6cbf1ca1611853b6e1","2e1fca49ccefcb602c916a6302c061d32aa0eda95112e7cd2ed2506d50811caf","2f6354487148a4a2641e5ed1e0983603374a1f8c66f1d2eebe5892dd9735d1d6","2ff571574542a8b55e3f5f6dde84aaae82a7f75ef56b61fe7f4a09bce170546d","30813a0174cef54c60bb121f95e328f69c750cc63a764b93fdbe26b4c41e5c3e","309f90f2b74f7916a6a280e64232fe19b870f699133ed3f81449870672867fa7","32355cb46ac48786a2c6cf9a092531598565f62f7933e06f77b2bcd464cd2ba6","329f04c43b93f6b787a2ef8a8e23519bc113196e6affc837dd6badb51cd17145","35429a8692dc7256b27f4c45abb36b4b33f86bb982c0c29965faaa6c8cc34d66","35df8fcec24c52c406addabcc9af0ac0b7aef329efb29c4384f53e4ea7a89fb7","35f0f1ed2343d39d4b33f4da26d7c7a0eb846d974a59bcf275cbaf70a12536cd","3738904100c2bdedbff71d56c62b8f08227983077affc498f848087138c6bfff","39b9b97d7dc68b98be2609ea101b96cbd2743f69d1264ea5f36783a153a6e5f3","3bde3f0d0cc7481da49d15758f8c32dbfff6eb2184c2cbd3fbbd15665ec8102d","3c582f6d13ac1cf0b33aa6e3cdc0a1baf42f1cd1da7080f96b0fadebb5a8b71d","3cd2799b94d44aa465eaf78457ad34451b6e6d881809e6cf961ac6ba0ce41d70","3d384d57ad1d293a7747beb55353c83c03472cfc5d03d90acbf2c0f37e6b84c3","3e0515a9b104bc3a165c1fd6eddb70f56449a08b3336eaea4d954674a24e448d","40040515aecaa05f9c4c3bc8c647d6c972bcfe8e364996bf9a2979e788bd129a","410213754fe7db03895021fa4febcc863e254349b5d67646e92beb22ced4150b","425a0c3acd761293fc3d925177333f91e9652fb1ff91b22258f14b086624c838","42df65283184c31527f8de3add005c74c25e06ee43dc24ac9ba69b3c2d38bc9b","441c3b0f98847106a2fccc55234d20485223e87f95fe9887ea6e0e6b978b2d39","44cf13ee8de6e43308289a3df719f2b4dccb2060c4259597ba67c9c29623e41d","45b2b49b7d512ce1d39340eb8ccea81d4ae11d237f25eb3c9599c3e99d0d5e8c","4671725af24cc8ec52ea8f7424c951274b68cefdb18564131d5938060c77dc56","469c2a921e910fce7859e4c351f41c9a4cda6b028386904aa22afa09cbba5351","480806ded46fba8711fafa728041b8e2fd0a40d9f8e4be4ea7c77ec7101e1a50","4a1477836cc454a1cc8b3a9a0e383c3abd8ce837dc670f7e396561b1cdf84f56","4b88c81df93686c39275ffe3bf73852240a06ec4c92f89b8a530f738a3830b87","4c0c2eb1a759ded986ddfbba277e6ac4d0eec9853a8871ae843dffd8c7829a9b","4c41685c0bb5f593ea74fedee931ebb02dad4867184729ca36c036e0f3df0781","4d4a99c7e19822bf77a525e715685d2113afa6b704b2dd4d80e579ad291f75bb","5300030a849d07c65c205b019f44006fd005c433dd06ac2f00e4acf9284b56c2","55b713ae1b78dff614707df952ea42548f543397307c164fccd65561c2a0941e","55c905c1118b25e2f93a98d860be0c3c1735f467d8d2919c982553a564331bac","58a355a7c63a2be44b6181016d32db1d9f209f6d0d82d71f900f4bb5971e42f3","5a6864d656004973677f4ddef001d352f07fa88a69eb555546c5a052ee1b24bc","60190416f20733f1307b983eddd6ef349f1273324e6049ac6e9cfb5a8986b355","62db016c84cdff5830988079bd3618801e6d929f3eac7b99b73fbb250e17a0ce"]

CASE_DRIVER=r"""
import hashlib,json,sys
from canonical.runtime import astra_runtime
class PolicyBoundaryReached(RuntimeError): pass
def blocked():
    raise PolicyBoundaryReached("POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN_BY_FROZEN_LIVEBENCH_POLICY")
astra_runtime._load_auto_capability_acquisition=blocked
from canonical.runtime.root2_livebench_if_astra_inference_adapter_v1 import infer
req=json.loads(sys.stdin.read())
try:
    out=infer(req)
except Exception as exc:
    msg=type(exc).__name__+":"+str(exc)
    if "POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN_BY_FROZEN_LIVEBENCH_POLICY" in msg:
        print(json.dumps({"classification":"POLICY_BLOCKED_AT_ACQUISITION_BOUNDARY"},sort_keys=True)); raise SystemExit(0)
    print(json.dumps({"classification":"RUNTIME_OR_OTHER_ERROR","error_type":type(exc).__name__,"error_sha256":hashlib.sha256(msg.encode()).hexdigest()},sort_keys=True)); raise SystemExit(0)
if out.get("status")=="PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE":
    answer=str(out.get("answer") or "")
    print(json.dumps({"classification":"VALID_RESPONSE","response_sha256":hashlib.sha256(answer.encode()).hexdigest(),"response_nonempty":bool(answer)},sort_keys=True))
else:
    raw=json.dumps(out,sort_keys=True,default=str)
    print(json.dumps({"classification":"NONPASS_RESPONSE","status":str(out.get("status")),"output_sha256":hashlib.sha256(raw.encode()).hexdigest()},sort_keys=True))
"""

def sha256(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

def build_template(base):
    root=base/"runtime_template"
    for src_rel,(dst_rel,expected) in FILES.items():
        src=ROOT/src_rel
        if not src.is_file(): raise RuntimeError("MISSING_FROZEN_CLOSURE_SOURCE:"+src_rel)
        got=git_blob_sha(src)
        if got!=expected: raise RuntimeError("FROZEN_CLOSURE_BLOB_DRIFT:"+src_rel+":"+got+":"+expected)
        dst=root/dst_rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
    (root/"canonical/__init__.py").write_text("")
    (root/"canonical/runtime/__init__.py").write_text("")
    (root/"canonical/astra_runtime/state").mkdir(parents=True,exist_ok=True)
    (root/"canonical/astra_runtime/evidence").mkdir(parents=True,exist_ok=True)
    return root

def download_dataset(base):
    dst=base/"test.parquet"
    url="https://huggingface.co/datasets/livebench/instruction_following/resolve/"+DATASET_REV+"/data/test-00000-of-00001.parquet?download=true"
    urllib.request.urlretrieve(url,dst)
    if dst.stat().st_size!=DATASET_BYTES: raise RuntimeError("DATASET_SIZE_MISMATCH")
    if sha256(dst)!=DATASET_SHA256: raise RuntimeError("DATASET_SHA256_MISMATCH")
    return dst

def load_prefix(p):
    import pyarrow.parquet as pq
    if hashlib.sha256("\n".join(PREFIX_IDS).encode()).hexdigest()!=PREFIX_IDS_SHA256: raise RuntimeError("PREFIX_DIGEST_MISMATCH")
    table=pq.read_table(p,columns=["question_id","turns"],filters=[("question_id","in",PREFIX_IDS)])
    rows=table.to_pylist(); by={str(x["question_id"]):x for x in rows}
    if set(by)!=set(PREFIX_IDS): raise RuntimeError("PREFIX_ROW_SET_MISMATCH")
    return [by[x] for x in PREFIX_IDS]

def classify(template,q):
    qid=str(q["question_id"])
    with tempfile.TemporaryDirectory(prefix="lb-v4-replay-") as td:
        root=pathlib.Path(td)/"root"; shutil.copytree(template,root,dirs_exist_ok=True)
        env=os.environ.copy(); env["PYTHONPATH"]=str(root)
        req={"benchmark_id":BENCHMARK_ID,"task_id":qid,"task_payload":{"instruction":q["turns"][0]},"allowed_tools":[]}
        try:
            cp=subprocess.run([sys.executable,"-c",CASE_DRIVER],input=json.dumps(req),text=True,capture_output=True,cwd=root,env=env,timeout=45)
        except Exception as exc:
            return {"question_id":qid,"classification":"HARNESS_ERROR","error_type":type(exc).__name__,"error_sha256":hashlib.sha256(str(exc).encode()).hexdigest()}
        if cp.returncode!=0:
            return {"question_id":qid,"classification":"HARNESS_ERROR","returncode":cp.returncode,"stderr_sha256":hashlib.sha256(cp.stderr.encode()).hexdigest()}
        try: obj=json.loads(cp.stdout.strip().splitlines()[-1])
        except Exception:
            return {"question_id":qid,"classification":"HARNESS_ERROR","stdout_sha256":hashlib.sha256(cp.stdout.encode()).hexdigest(),"stderr_sha256":hashlib.sha256(cp.stderr.encode()).hexdigest()}
        obj["question_id"]=qid; return obj

def main():
    if os.environ.get("GITHUB_ACTIONS")!="true": raise SystemExit("GITHUB_ACTIONS_REQUIRED")
    if str(os.environ.get("REPOSITORY_PRIVATE","")).lower()!="false": raise SystemExit("PUBLIC_INDEPENDENT_RUNNER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="lb-v4-replay-root-") as td:
        base=pathlib.Path(td); template=build_template(base); rows=load_prefix(download_dataset(base))
        if len(rows)!=72: raise RuntimeError("PREFIX_ROW_COUNT_MISMATCH")
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8,os.cpu_count() or 2)) as ex:
            results=list(ex.map(lambda q: classify(template,q),rows))
    counts={}
    for r in results: counts[r["classification"]]=counts.get(r["classification"],0)+1
    blocked=counts.get("POLICY_BLOCKED_AT_ACQUISITION_BOUNDARY",0); valid=counts.get("VALID_RESPONSE",0); other=len(results)-blocked-valid
    max_success=POPULATION-blocked; max_pct=100.0*max_success/POPULATION
    forced=blocked==72 and valid==0 and other==0 and max_pct<THRESHOLD_PERCENT
    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_V4_REPLAY_72_POLICY_BOUNDARY_RESULT_V1",
      "status":"FAIL_FORCED_BY_ALREADY_EXPOSED_POLICY_BLOCKED_PREFIX" if forced else "REPLAY_INCONCLUSIVE_FAIL_CLOSED",
      "benchmark_id":BENCHMARK_ID,"candidate_commit":"d5de4f5808dced840da34d051e3f9a5ff06e2e54","candidate_tree":"fd39e966d4686c7317b9a1558b360eb0c58ad76f",
      "frozen_runtime_closure_file_count":len(FILES),"dataset_revision":DATASET_REV,"dataset_sha256":DATASET_SHA256,
      "population_count":POPULATION,"threshold_percent":THRESHOLD_PERCENT,"replay_case_count":len(results),"replay_case_ids_sha256":PREFIX_IDS_SHA256,
      "replay_scope":"EXACT_ALREADY_ATTEMPTED_72_PREFIX_ONLY","new_case_ids_passed_to_candidate":0,"post_prompt_capability_acquisition_allowed":False,
      "policy_boundary_interception":"HARNESS_BLOCKS_ONLY_ASTRA_RUNTIME__LOAD_AUTO_CAPABILITY_ACQUISITION",
      "classification_counts":counts,"maximum_possible_successes_if_ALL_UNREPLAYED_CASES_PASS":max_success,
      "maximum_possible_percent_if_ALL_UNREPLAYED_CASES_PASS":max_pct,"predicate_fail_forced":forced,
      "root1_reopen_authorized_by_this_receipt":False,"acceptance_credit_authorized_by_this_receipt":False,"promotion_authority":False,
      "case_receipts":results,
      "hard_nonclaims":["NO_NEW_CASE_ID_PASSED_TO_FROZEN_CANDIDATE","NO_POST_PROMPT_CAPABILITY_ACQUISITION_OR_DISCOVERY_EXECUTED","NO_CANDIDATE_BYTES_MUTATED","NO_ROOT1_REOPEN_WITHOUT_SEPARATE_INDEPENDENT_REDUCTION","NO_ACCEPTANCE_OR_PROMOTION_FROM_THIS_REPLAY_ALONE"],
      "accounting":{"incremental_spend_usd":0,"new_terminal_case_ids_consumed":0,"replayed_previously_attempted_case_ids":len(results),"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0}}
    out=ROOT/"LIVEBENCH_V4_REPLAY_72_POLICY_BOUNDARY_RESULT.json"; out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":receipt["status"],"classification_counts":counts,"maximum_possible_percent":max_pct,"predicate_fail_forced":forced,"receipt_sha256":sha256(out)},sort_keys=True))
    return 0 if forced else 2
if __name__=="__main__": raise SystemExit(main())
