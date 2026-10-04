#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
BENCHMARK_ID = "LIVEBENCH_IF_2026_06_25"
FROZEN_RELEASE = "2026-06-25"
POPULATION = 200
THRESHOLD = 0.657
THRESHOLD_MASS = POPULATION * THRESHOLD
DATASET_REV = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
DATASET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
DATASET_BYTES = 537024
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
AUTHORIZED_ACTIVATION_BLOB = "d410d6952cb34f2fd3fb4dc48bf2a613d11c57d1"
AUTHORIZED_ROOT_BLOB = "601e82d00104b4ed36ee5968ad966a0c02e627c1"
AUTHORIZED_FRONTIER_BLOB = "8c1325dd652b65a7d5c24e041ac06556a84f569c"
PRECOMMIT_BLOB = "66554061f204d8a86b37a30c84d0cf07a525a786"
SCORER_SUPPLEMENT_BLOB = "13105f751550ea89646bb82bd4c1d8325afe2840"
BATCH = 8
REPLAY_LIMIT = 72

RUNTIME_FILES = {
    "astra_runtime": ("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/astra_runtime.py", "7f5d16b1db69cb620954bc778e0ba6e15e687b75", "canonical/runtime/astra_runtime.py"),
    "adapter": ("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py", "7e3885fa7a6e56df656c066e0a8f17cfa21424e7", "canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py"),
    "entrypoint": ("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_external_task_entrypoint_v1.py", "603beefe0db24102b86b7c965e5433bd880392af", "canonical/runtime/root2_external_task_entrypoint_v1.py"),
    "adapter_registry": ("capsules/root2_livebench_astra_adapter_v1/canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json", "afa021a25d2de53e293d10ab6759e55eaabaea21", "canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json"),
    "goal_compiler": ("canonical/runtime/goal_compiler.py", "4b61fe911471854ec15c7900816f61e9e55f602e", "canonical/runtime/goal_compiler.py"),
    "bound_registry": ("canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json", "7badee4878700f2cd4176beb8319d2a6a0bdf782", "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"),
    "capability_planner": ("canonical/runtime/capability_planner.py", "64ff65cb184f50d3336326f33cccfcc0a53301a8", "canonical/runtime/capability_planner.py"),
    "capability_proposal_generators": ("canonical/runtime/capability_proposal_generators.py", "71f2bbfda66a65d8d75e035b9ae073671ebd56e2", "canonical/runtime/capability_proposal_generators.py"),
    "plain_goal_bound_grounding": ("subject/livebench_frozen_generic_closure_v1/canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py", "46e8e7466479ea298c34e5fa682d49c374510ce9", "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py"),
    "broad_objective_decompose": ("subject/livebench_frozen_generic_closure_v1/canonical/runtime/bound_capabilities/broad_objective_decompose.py", "3ded762075ed222228a14877af631f1e2e6d9e4c", "canonical/runtime/bound_capabilities/broad_objective_decompose.py"),
    "grounded_executable_composition": ("subject/livebench_frozen_generic_closure_v1/canonical/runtime/bound_capabilities/grounded_executable_composition.py", "8328e12804f64cab1c0d9509966cb1d2d8fb1f82", "canonical/runtime/bound_capabilities/grounded_executable_composition.py"),
    "grounded_executable_composition_verify": ("subject/livebench_frozen_generic_closure_v1/canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py", "ab9f6fc19937d23edb24dc26a2affed96cea0a9a", "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py"),
    "open_research_source_frontend": ("subject/livebench_frozen_generic_closure_v1/canonical/runtime/bound_capabilities/open_research_source_frontend.py", "830fd35c816140cb6ddb2d3dac9f0886e595d993", "canonical/runtime/bound_capabilities/open_research_source_frontend.py"),
    "semantic_authorities": ("subject/livebench_frozen_generic_closure_v1/canonical/runtime/semantic_authorities.py", "1d74b9c2cdc0e387ab1d64f04c8f38f414f2d80e", "canonical/runtime/semantic_authorities.py"),
    "python_codec_probe": ("subject/livebench_frozen_generic_closure_v1/canonical/runtime/python_codec_probe.py", "fc8b5005a9888422e3cb61f6cf0bd147c740ec84", "canonical/runtime/python_codec_probe.py"),
}

SCORER_FILES = {
    "livebench/gen_ground_truth_judgment.py": "b36561da5b54380c724c507462d0ee65feefeac8",
    "livebench/if_runner/ifbench/evaluation_lib.py": "2c7bd1290031dbe4ae0f016c53255f4af0ec645b",
    "livebench/if_runner/ifbench/instructions.py": "02b2dfeb50f036b89bec3df34522c73f756d8f44",
    "livebench/if_runner/ifbench/instructions_registry.py": "adfed4832877566e62970257b50c6fa32c302fb2",
    "livebench/if_runner/ifbench/instructions_util.py": "21b13c7fcfc2c2de01e80c9e7dd222b9bca81342",
    "livebench/if_runner/ifbench/README.md": "de771a18e7c7625270768fc284e8931cf40f3009",
    "livebench/if_runner/instruction_following_eval/evaluation_main.py": "4a341984936c4d609644a3b77f8c030ac5aa7269",
    "livebench/if_runner/instruction_following_eval/instructions_registry.py": "903ed738398648c7cfac61d5ffa478c22f1f0891",
    "livebench/if_runner/instruction_following_eval/instructions.py": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "livebench/if_runner/instruction_following_eval/instructions_util.py": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "livebench/process_results/instruction_following/utils.py": "8ce01747887ec0792c8f024e1972e34ece781676",
}

NLTK = {
    "packages/tokenizers/punkt.zip": "da7ffbd1e6fd6cc5c2f6879c2d4da23c7691944c",
    "packages/tokenizers/punkt_tab.zip": "5e5ff6137d5ee6025e400d1c3a7b21914c48b635",
    "packages/corpora/stopwords.zip": "56d35b5d204d64480f71edc0f5f82aebce6730b6",
    "packages/taggers/averaged_perceptron_tagger.zip": "d5bfb6852aa5d288c8f33b3f0ef0fde343afa405",
    "packages/taggers/averaged_perceptron_tagger_eng.zip": "b792e19546a5711218a05f4029ef17c8d62cd839",
}
NLTK_COMMIT = "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"

def git_blob_sha(path: pathlib.Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)

def install_scorer_deps():
    pkgs = [
        "nltk==3.10.3",
        "emoji==2.16.0",
        "syllapy==0.7.2",
        "setuptools==80.9.0",
        "spacy==3.8.16",
        "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl",
        "langdetect==1.0.9",
        "immutabledict==4.3.1",
        "pandas==2.3.3",
    ]
    run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--quiet", *pkgs])

def prepare_nltk(base: pathlib.Path):
    data = base / "nltk_data"
    data.mkdir()
    for rel, expected in NLTK.items():
        dst = base / pathlib.Path(rel).name
        url = f"https://raw.githubusercontent.com/nltk/nltk_data/{NLTK_COMMIT}/{rel}"
        urllib.request.urlretrieve(url, dst)
        got = git_blob_sha(dst)
        if got != expected:
            raise RuntimeError(f"NLTK_BLOB_MISMATCH:{rel}:{got}:{expected}")
        sub = rel.split("/")[1]
        target = data / sub
        target.mkdir(exist_ok=True)
        with zipfile.ZipFile(dst) as z:
            z.extractall(target)
    os.environ["NLTK_DATA"] = str(data)

def clone_livebench(base: pathlib.Path) -> pathlib.Path:
    repo = base / "LiveBench"
    run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", "https://github.com/LiveBench/LiveBench.git", str(repo)])
    run(["git", "-C", str(repo), "fetch", "--quiet", "--depth=1", "origin", LIVEBENCH_COMMIT])
    run(["git", "-C", str(repo), "checkout", "--quiet", "--detach", LIVEBENCH_COMMIT])
    if run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True).stdout.strip() != LIVEBENCH_COMMIT:
        raise RuntimeError("LIVEBENCH_COMMIT_MISMATCH")
    for rel, expected in SCORER_FILES.items():
        got = run(["git", "-C", str(repo), "rev-parse", f"HEAD:{rel}"], capture_output=True).stdout.strip()
        if got != expected:
            raise RuntimeError(f"SCORER_BLOB_MISMATCH:{rel}:{got}:{expected}")
    return repo

def download_dataset(base: pathlib.Path) -> pathlib.Path:
    dst = base / "test.parquet"
    url = f"https://huggingface.co/datasets/livebench/instruction_following/resolve/{DATASET_REV}/data/test-00000-of-00001.parquet?download=true"
    urllib.request.urlretrieve(url, dst)
    if dst.stat().st_size != DATASET_BYTES:
        raise RuntimeError(f"DATASET_SIZE_MISMATCH:{dst.stat().st_size}:{DATASET_BYTES}")
    got = sha256(dst)
    if got != DATASET_SHA256:
        raise RuntimeError(f"DATASET_SHA256_MISMATCH:{got}:{DATASET_SHA256}")
    return dst

def parse_population(base: pathlib.Path, parquet: pathlib.Path) -> list[dict]:
    venv = base / "loader"
    run([sys.executable, "-m", "venv", str(venv)])
    py = venv / "bin" / "python"
    run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "--quiet", "pyarrow==19.0.1"])
    out = base / "questions.jsonl"
    code = r'''
import datetime, json, pyarrow.parquet as pq, sys
src,out=sys.argv[1],sys.argv[2]
valid={"2024-06-24","2024-07-26","2024-08-31","2024-11-25","2025-04-02","2025-04-25","2025-05-30","2025-11-25","2025-12-23","2026-01-08","2026-06-25"}
release="2026-06-25"
rows=pq.read_table(src).to_pylist()
def iso(v):
    if isinstance(v,(datetime.date,datetime.datetime)): return v.strftime("%Y-%m-%d")
    return "" if v is None else str(v)[:10]
sel=[]
for q in rows:
    q["livebench_release_date"]=iso(q.get("livebench_release_date"))
    q["livebench_removal_date"]=iso(q.get("livebench_removal_date"))
    if q["livebench_release_date"] not in valid: continue
    rem=q["livebench_removal_date"]
    if rem and rem <= release: continue
    sel.append(q)
sel=sorted(sel,key=lambda q:str(q["question_id"]))
assert len(sel)==200,("POPULATION_COUNT",len(sel))
assert len({str(q["question_id"]) for q in sel})==200
assert all(q.get("category")=="instruction_following" for q in sel)
with open(out,"w",encoding="utf-8") as f:
    for q in sel:
        f.write(json.dumps(q,sort_keys=True,default=str)+"\n")
'''
    run([str(py), "-c", code, str(parquet), str(out)])
    return [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]

def build_runtime_template(base: pathlib.Path) -> pathlib.Path:
    root = base / "runtime_template"
    (root / "canonical/runtime").mkdir(parents=True)
    (root / "canonical/governance").mkdir(parents=True)
    (root / "canonical/astra_runtime/state").mkdir(parents=True)
    (root / "canonical/astra_runtime/evidence").mkdir(parents=True)
    (root / "canonical/__init__.py").write_text("", encoding="utf-8")
    (root / "canonical/runtime/__init__.py").write_text("", encoding="utf-8")
    for _name,(src_rel,expected_blob,dst_rel) in RUNTIME_FILES.items():
        src = ROOT / src_rel
        if git_blob_sha(src) != expected_blob:
            raise RuntimeError("RUNTIME_BLOB_DRIFT:"+src_rel)
        dst = root / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src,dst)
    return root

CASE_DRIVER = r'''
import json,sys
from canonical.runtime import astra_runtime

def _policy_block(*args,**kwargs):
    raise astra_runtime.Blocker("LIVEBENCH_EXTERNAL_TOOLS_FORBIDDEN_BY_PRECOMMIT")

# Enforce the already-frozen LiveBench no-external-tools boundary at the
# environment/harness layer. Candidate bytes are unchanged.
astra_runtime._load_auto_capability_acquisition = _policy_block
astra_runtime._load_capability_discovery = _policy_block
astra_runtime._run_open_research_source_frontend = _policy_block
astra_runtime._external_tool_bridge = _policy_block

from canonical.runtime.root2_livebench_if_astra_inference_adapter_v1 import infer,Root2InferenceBlocked
req=json.loads(sys.stdin.read())
try:
    out=infer(req)
    print(json.dumps({"kind":"response","out":out},sort_keys=True))
except Root2InferenceBlocked as exc:
    msg=str(exc)
    if "LIVEBENCH_EXTERNAL_TOOLS_FORBIDDEN_BY_PRECOMMIT" in msg:
        print(json.dumps({"kind":"policy_block","reason":"EXTERNAL_TOOLS_FORBIDDEN_BY_PRECOMMIT"},sort_keys=True))
    else:
        raise
'''

def infer_one(template: pathlib.Path, q: dict) -> tuple[str,str,str|None]:
    qid = str(q["question_id"])
    with tempfile.TemporaryDirectory(prefix="lb-case-") as td:
        case = pathlib.Path(td)
        shutil.copytree(template, case / "root", dirs_exist_ok=True)
        root = case / "root"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        req = {
            "benchmark_id": BENCHMARK_ID,
            "task_id": qid,
            "task_payload": {"instruction": q["turns"][0]},
            "allowed_tools": [],
        }
        try:
            cp = subprocess.run(
                [sys.executable, "-c", CASE_DRIVER],
                input=json.dumps(req),
                text=True,
                capture_output=True,
                cwd=root,
                env=env,
                timeout=45,
            )
            if cp.returncode != 0:
                return qid, "", "RUNTIME_ERROR:INFERENCE_EXIT_"+str(cp.returncode)+":"+hashlib.sha256(cp.stderr.encode()).hexdigest()
            envelope=json.loads(cp.stdout)
            if envelope.get("kind")=="policy_block":
                return qid,"","POLICY_BLOCKED_EXTERNAL_TOOLS"
            if envelope.get("kind")!="response":
                return qid,"","RUNTIME_ERROR:INVALID_DRIVER_ENVELOPE"
            out=envelope.get("out") or {}
            if out.get("status") != "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE":
                return qid, "", "RUNTIME_ERROR:INFERENCE_STATUS:"+str(out.get("status"))
            return qid, str(out.get("answer") or ""), None
        except Exception as exc:
            return qid, "", "RUNTIME_ERROR:"+type(exc).__name__+":"+str(exc)[:300]

def case_score(legacy_eval, ifbench_eval, q: dict, answer: str) -> tuple[float,bool,int,int,str|None]:
    try:
        release=str(q.get("livebench_release_date") or "")
        prompt=q["turns"][0]
        ids=list(q["instruction_id_list"])
        if release < "2025-11-25":
            processed=re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()
            kwargs=[{k:v for k,v in dict(x or {}).items() if v is not None} for x in q["kwargs"]]
            inp=legacy_eval.InputExample(
                key=q.get("key",q.get("question_id")),
                instruction_id_list=ids,
                prompt=prompt,
                kwargs=kwargs,
            )
            out=legacy_eval.test_instruction_following_strict(inp,{prompt:processed})
        else:
            m=re.search(r"<solution>(.*?)</solution>",answer,flags=re.DOTALL)
            processed=(m.group(1).strip() if m else answer.strip())
            inp=ifbench_eval.InputExample(
                key=q.get("key",q.get("question_id")),
                instruction_id_list=ids,
                prompt=prompt,
                kwargs=list(q["kwargs"]),
            )
            out=ifbench_eval.test_instruction_following_strict(inp,processed)
        n=len(out.follow_instruction_list)
        followed=sum(1 for x in out.follow_instruction_list if x)
        score=((1.0 if out.follow_all_instructions else 0.0)+(followed/n))/2.0
        return score,bool(out.follow_all_instructions),n,followed,None
    except Exception as exc:
        return 0.0,False,len(q.get("instruction_id_list") or []),0,type(exc).__name__+":"+str(exc)[:300]

def receipts_root(receipts:list[dict])->str:
    raw=json.dumps(receipts,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def verify_local_authority_transport():
    local = {
        ROOT / "subject/livebench_threshold_root_transport_v1/activation_v2.json": AUTHORIZED_ACTIVATION_BLOB,
        ROOT / "subject/root2_output_only_threshold_activation_v1_20261004/TERMINAL_ROOT_CAUSE_STATE_V1.json": AUTHORIZED_ROOT_BLOB,
        ROOT / "subject/livebench_threshold_root_transport_v1/threshold_projection_verification.json": "eef494009e47b758a99ab48649e050c332e4988a",
        ROOT / "subject/livebench_threshold_root_transport_v1/prior_activation_verification.json": "34e65d54026fd246c76e0dc3ded8f9f8a1b2a4d9",
    }
    for p,expected in local.items():
        if not p.is_file() or git_blob_sha(p)!=expected:
            raise SystemExit("FAIL_CLOSED:AUTHORITY_TRANSPORT_BLOB_DRIFT:"+str(p))
    act=json.loads((ROOT / "subject/livebench_threshold_root_transport_v1/activation_v2.json").read_text())
    if act.get("authorized_predicates") != ["LIVEBENCH_IF_GE_65_7"]:
        raise SystemExit("FAIL_CLOSED:AUTHORITY_SCOPE_DRIFT")
    if (act.get("authority") or {}).get("execution") is not True:
        raise SystemExit("FAIL_CLOSED:EXECUTION_AUTHORITY_FALSE")
    if (act.get("authority") or {}).get("global_fresh_reality") is not False:
        raise SystemExit("FAIL_CLOSED:GLOBAL_FRESH_REALITY_WIDENED")
    if (act.get("authority_basis") or {}).get("root_state",{}).get("git_blob_sha") != AUTHORIZED_ROOT_BLOB:
        raise SystemExit("FAIL_CLOSED:ROOT_BINDING_DRIFT")

def main(*, authorized: bool=False) -> int:
    if authorized is not True:
        raise SystemExit("FAIL_CLOSED:VERIFIED_RETRY_EPOCH_LAUNCHER_REQUIRED")
    if os.environ.get("GITHUB_ACTIONS") != "true" or str(os.environ.get("REPOSITORY_PRIVATE","")).lower() != "false":
        raise SystemExit("FAIL_CLOSED:PUBLIC_STANDARD_GITHUB_RUNNER_REQUIRED")
    if sys.version_info[:2] != (3,12):
        raise SystemExit("FAIL_CLOSED:PYTHON_3_12_REQUIRED")

    verify_local_authority_transport()

    # All zero-case component checks already ran in the invoking carrier verifier.
    # Recheck exact frozen bytes here before any terminal-case download/read.
    for _, (rel, expected) in RUNTIME_FILES.items():
        p=ROOT/rel
        if not p.is_file() or git_blob_sha(p)!=expected:
            raise SystemExit("FAIL_CLOSED:RUNTIME_COMPONENT_DRIFT:"+rel)

    with tempfile.TemporaryDirectory(prefix="livebench-terminal-") as td:
        base=pathlib.Path(td)

        # Point-of-use dependency/scorer readiness, still before terminal case read.
        install_scorer_deps()
        prepare_nltk(base)
        lb=clone_livebench(base)
        sys.path.insert(0,str(lb/"livebench/if_runner"))
        from instruction_following_eval import evaluation_main as legacy_eval
        from instruction_following_eval import instructions_registry as legacy_registry
        sys.path.insert(0,str(lb))
        from livebench.if_runner.ifbench import evaluation_lib as ifbench_eval
        from livebench.if_runner.ifbench import instructions_registry as ifbench_registry

        # Dual-family synthetic scorer smoke, still zero terminal cases.
        legacy_synth=legacy_eval.InputExample(
            key=0,
            instruction_id_list=["punctuation:no_comma"],
            prompt="synthetic legacy prompt",
            kwargs=[{}],
        )
        legacy_out=legacy_eval.test_instruction_following_strict(
            legacy_synth,{"synthetic legacy prompt":"hello world"})
        if legacy_out.follow_all_instructions is not True:
            raise SystemExit("FAIL_CLOSED:SYNTHETIC_LEGACY_SCORER_SMOKE")
        modern_synth=ifbench_eval.InputExample(
            key=0,
            instruction_id_list=["format:no_whitespace"],
            prompt="synthetic modern prompt",
            kwargs=[{}],
        )
        modern_out=ifbench_eval.test_instruction_following_strict(modern_synth,"helloworld")
        if modern_out.follow_all_instructions is not True:
            raise SystemExit("FAIL_CLOSED:SYNTHETIC_IFBENCH_SCORER_SMOKE")

        # Terminal case exposure begins only after all preceding gates pass.
        parquet=download_dataset(base)
        questions=parse_population(base,parquet)
        unknown_legacy=set()
        unknown_ifbench=set()
        for q in questions:
            registry=(legacy_registry.INSTRUCTION_DICT
                      if str(q.get("livebench_release_date") or "") < "2025-11-25"
                      else ifbench_registry.INSTRUCTION_DICT)
            dest=(unknown_legacy
                  if str(q.get("livebench_release_date") or "") < "2025-11-25"
                  else unknown_ifbench)
            for iid in q.get("instruction_id_list") or []:
                if iid not in registry:
                    dest.add(iid)
        if unknown_legacy or unknown_ifbench:
            payload={"legacy":sorted(unknown_legacy),"ifbench":sorted(unknown_ifbench)}
            raise SystemExit("FAIL_CLOSED:DISPATCHED_UNKNOWN_INSTRUCTION_IDS:"+
                             hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest())

        template=build_runtime_template(base)
        receipts=[]
        cumulative=0.0
        verdict=None
        consumed=0

        # Fixed question-id order. No adaptive selection or replacement.
        for start in range(0,REPLAY_LIMIT,BATCH):
            batch=questions[start:start+BATCH]
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(BATCH,os.cpu_count() or 2)) as ex:
                raw=list(ex.map(lambda q: infer_one(template,q),batch))
            by_id={qid:(answer,err) for qid,answer,err in raw}
            for q in batch:
                qid=str(q["question_id"])
                answer,inf_err=by_id[qid]
                if inf_err and inf_err.startswith("RUNTIME_ERROR:"):
                    raise SystemExit("FAIL_CLOSED:"+inf_err)
                if inf_err=="POLICY_BLOCKED_EXTERNAL_TOOLS":
                    score,allok,n,followed,score_err=0.0,False,len(q.get("instruction_id_list") or []),0,None
                elif inf_err:
                    raise SystemExit("FAIL_CLOSED:UNCLASSIFIED_INFERENCE_ERROR:"+hashlib.sha256(inf_err.encode()).hexdigest())
                else:
                    score,allok,n,followed,score_err=case_score(legacy_eval,ifbench_eval,q,answer)
                rec={
                    "question_id":qid,
                    "response_sha256":hashlib.sha256(answer.encode()).hexdigest(),
                    "score":score,
                    "follow_all":allok,
                    "instruction_count":n,
                    "instructions_followed":followed,
                    "inference_error":inf_err,
                    "scoring_error":score_err,
                }
                receipts.append(rec)
                cumulative+=score
                consumed+=1
                print("LIVEBENCH_CASE_RECEIPT="+json.dumps(rec,sort_keys=True),flush=True)

            remaining=POPULATION-consumed
            lower=cumulative
            upper=cumulative+remaining
            if lower >= THRESHOLD_MASS:
                verdict="PASS_FORCED"
                break
            if upper < THRESHOLD_MASS:
                verdict="FAIL_FORCED"
                break

        if verdict is None:
            verdict="REPLAY_PREFIX_INCONCLUSIVE"
        if consumed != REPLAY_LIMIT:
            raise SystemExit("FAIL_CLOSED:REPLAY_PREFIX_COUNT_MISMATCH")

        summary={
            "schema":"PROJECT_BRAIN_LIVEBENCH_IF_THRESHOLD_EXECUTION_RESULT_V2",
            "benchmark_id":BENCHMARK_ID,
            "status":verdict,
            "population_count":POPULATION,
            "terminal_cases_consumed":consumed,
            "case_order":"QUESTION_ID_ASCENDING_FIXED_PREEXECUTION",
            "adaptive_case_selection":False,
            "case_replacement":False,
            "threshold_percent":65.7,
            "threshold_mass":THRESHOLD_MASS,
            "observed_score_mass":cumulative,
            "observed_mean_percent":100.0*cumulative/consumed if consumed else 0.0,
            "conservative_full_population_lower_percent":100.0*cumulative/POPULATION,
            "conservative_full_population_upper_percent":100.0*(cumulative+(POPULATION-consumed))/POPULATION,
            "predicate_pass_forced":cumulative >= THRESHOLD_MASS,
            "predicate_fail_forced":cumulative+(POPULATION-consumed) < THRESHOLD_MASS,
            "receipts_sha256":receipts_root(receipts),
            "dataset_revision":DATASET_REV,
            "dataset_sha256":DATASET_SHA256,
            "livebench_commit":LIVEBENCH_COMMIT,
            "activation_blob_sha":AUTHORIZED_ACTIVATION_BLOB,
            "bound_root_blob_sha":AUTHORIZED_ROOT_BLOB,
            "bound_frontier_blob_sha":AUTHORIZED_FRONTIER_BLOB,
            "precommit_blob_sha":PRECOMMIT_BLOB,
            "scorer_supplement_blob_sha":SCORER_SUPPLEMENT_BLOB,
            "scorer_dispatch":"PUBLIC_UPSTREAM_RELEASE_DATE_SPLIT__LEGACY_IFEVAL_BEFORE_2025_11_25__IFBENCH_OTHERWISE",
            "retry_epoch_authorized_by_verified_launcher":True,
            "replay_prefix_limit":REPLAY_LIMIT,
            "new_case_exposure":False,
            "runtime_error_scored_as_zero":False,
            "policy_block_scored_as_zero":True,
            "incremental_spend_usd":0,
            "paid_external_model_or_api_used":False,
            "cognition_dependency_class":"MODEL_INDEPENDENT",
            "promotion_authority":False,
            "acceptance_credit_authority":False,
        }
        print("LIVEBENCH_TERMINAL_RESULT="+json.dumps(summary,sort_keys=True),flush=True)
        return 0

if __name__=="__main__":
    raise SystemExit("FAIL_CLOSED:VERIFIED_RETRY_EPOCH_LAUNCHER_REQUIRED")
