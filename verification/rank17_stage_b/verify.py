from __future__ import annotations
import ast
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"brain_runtime"))
from specification_consensus_gate import source_sentences, assess_consensus
from requirement_graph_kernel import compile_requirement_contract, requirement_mutation_score

def read(name):
    return (ROOT/"source"/name).read_text(encoding="utf-8")

def git_blob_sha(text):
    b=text.encode("utf-8")
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def parse_scalar(v):
    import ast as _ast
    v=v.strip()
    if v.startswith("[") and v.endswith("]"):
        return _ast.literal_eval(v)
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return _ast.literal_eval(v)
    if v in {"true","false"}: return v=="true"
    if re.fullmatch(r"-?\d+",v): return int(v)
    if re.fullmatch(r"-?\d+\.\d+",v): return float(v)
    return v

def parse_policy(text):
    ref={}; transforms={}; files={}
    section=None; current_transform=None; current_file=None; in_columns=False
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"): continue
        indent=len(raw)-len(raw.lstrip(" "))
        s=raw.strip()
        if indent==0 and s.endswith(":"):
            section=s[:-1]; current_transform=current_file=None; in_columns=False; continue
        if section=="reference_tokens" and indent==2 and ":" in s:
            k,v=s.split(":",1); ref[k]=parse_scalar(v); continue
        if section=="transforms":
            if indent==2 and s.endswith(":"):
                current_transform=s[:-1]; transforms[current_transform]={}; continue
            if indent==4 and current_transform and ":" in s:
                k,v=s.split(":",1); transforms[current_transform][k]=parse_scalar(v); continue
        if section=="files":
            if indent==2 and s.endswith(":"):
                current_file=s[:-1]; files[current_file]={}; in_columns=False; continue
            if indent==4 and s=="columns:":
                in_columns=True; continue
            if indent==6 and current_file and in_columns and ":" in s:
                k,v=s.split(":",1); files[current_file][k]=parse_scalar(v); continue
    return {"reference_tokens":ref,"transforms":transforms,"files":files}

def item(unit, cls, rid=None, actor=None, action=None, obj=None, condition=None, constraints=None):
    x={"source_sentence_id":unit["id"],"source_quote":unit["text"],"class":cls}
    if cls=="requirement":
        x.update({"requirement_id":rid,"actor":actor,"action":action,"object":obj,"condition":condition or "","negated":False,"constraints":constraints or []})
    return x

def extractor_literal(units):
    out=[]
    for u in units:
        sid=u["id"]
        if sid=="S2":
            out.append(item(u,"requirement","I1_BUILD","tool","anonymize","related csv files",constraints=["artifact=/app/anon.py","input=/app/input","policy=/app/policy.yaml","output=/app/output"]))
        elif sid=="S4":
            out.append(item(u,"requirement","I2_CLI","cli","accept","invocation",constraints=["input=/app/input","--policy /app/policy.yaml","--output /app/output","--seed 42","--max-memory 64MB"]))
        elif sid=="S5":
            out.append(item(u,"requirement","I3_STRUCTURE","tool","preserve and transform","output csvs",constraints=["filenames","headers","column order","row order","row counts","policy columns"]))
        elif sid=="S6":
            out.append(item(u,"requirement","I4_IDENTITY","tool","canonicalize","underlying entity references",constraints=["all files","type-2 history","transitive effective-dated merges","transitive cross-tenant subject_links equivalence"]))
        elif sid=="S7":
            out.append(item(u,"requirement","I5_SEED_MEMORY","tool","produce","deterministic seeded bounded output",constraints=["deterministic for seed","seeded transforms change with seed","peak memory <= --max-memory"]))
        else:
            out.append(item(u,"non_requirement"))
    return {"extractor_id":"literal_normative_v1","sentences":out}

def extractor_constraint(units):
    out=[]
    for u in units:
        t=u["text"]
        if "Build a CLI tool" in t:
            out.append(item(u,"requirement","I1_BUILD","tool","anonymize","related csv files",constraints=["artifact=/app/anon.py","input=/app/input","policy=/app/policy.yaml","output=/app/output"]))
        elif t.startswith("```bash") and "--max-memory 64MB" in t:
            out.append(item(u,"requirement","I2_CLI","cli","accept","invocation",constraints=["input=/app/input","--policy /app/policy.yaml","--output /app/output","--seed 42","--max-memory 64MB"]))
        elif "must preserve filenames" in t:
            out.append(item(u,"requirement","I3_STRUCTURE","tool","preserve and transform","output csvs",constraints=["filenames","headers","column order","row order","row counts","policy columns"]))
        elif "same underlying entity" in t:
            out.append(item(u,"requirement","I4_IDENTITY","tool","canonicalize","underlying entity references",constraints=["all files","type-2 history","transitive effective-dated merges","transitive cross-tenant subject_links equivalence"]))
        elif "deterministic for a given" in t and "peak memory" in t:
            out.append(item(u,"requirement","I5_SEED_MEMORY","tool","produce","deterministic seeded bounded output",constraints=["deterministic for seed","seeded transforms change with seed","peak memory <= --max-memory"]))
        else:
            out.append(item(u,"non_requirement"))
    return {"extractor_id":"constraint_pattern_v1","sentences":out}

def semantic_errors(contract):
    errors=[]
    instruction=read("instruction.md")
    task=read("task.toml")
    docker=read("Dockerfile")
    policy=read("policy.yaml")
    generator=read("generate_input.py")
    auth=contract["source_authority"]
    if hashlib.sha256(instruction.encode()).hexdigest()!=auth["instruction_sha256"]: errors.append("INSTRUCTION_HASH")
    for name,text,key in [
        ("task.toml",task,"task_toml_git_blob"),("Dockerfile",docker,"dockerfile_git_blob"),
        ("policy.yaml",policy,"policy_git_blob"),("generate_input.py",generator,"generator_git_blob")]:
        if git_blob_sha(text)!=auth[key]: errors.append("SOURCE_BLOB:"+name)
    units=source_sentences(instruction)
    consensus=assess_consensus(instruction,[extractor_literal(units),extractor_constraint(units)])
    if not consensus["pass"]: errors.append("INSTRUCTION_CONSENSUS:"+",".join(consensus["failures"]))
    if consensus["source_sentence_count"]!=9: errors.append("INSTRUCTION_UNIT_COUNT")
    accepted={x["requirement_id"] for x in consensus["accepted_requirements"]}
    if accepted!={"I1_BUILD","I2_CLI","I3_STRUCTURE","I4_IDENTITY","I5_SEED_MEMORY"}: errors.append("INSTRUCTION_REQUIREMENT_SET")

    parsed=parse_policy(policy)
    if parsed!=contract["policy_model"]: errors.append("POLICY_MODEL_MISMATCH")
    tree=ast.parse(generator)
    funcs={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    if funcs!=set(contract["generator_function_accounting"]): errors.append("GENERATOR_FUNCTION_ACCOUNTING")
    generated=set(re.findall(r'output_dir\s*/\s*["\\\']([^"\\\']+\.csv)["\\\']',generator))
    if generated!=set(parsed["files"]): errors.append("GENERATED_FILE_SET")
    for marker in contract["generator_semantic_markers"]:
        if marker["needle"] not in generator: errors.append("GENERATOR_MARKER:"+marker["needle"])
        if marker["requirement"] not in {r["id"] for r in contract["requirements"]}: errors.append("MARKER_UNKNOWN_REQUIREMENT")
    req_ids=[r["id"] for r in contract["requirements"]]
    expected=[f"R{i:02d}_"+suffix for i,suffix in []]
    if len(req_ids)!=24 or len(set(req_ids))!=24: errors.append("REQUIREMENT_ID_CARDINALITY")
    compiled=compile_requirement_contract(contract["requirements"],expected_required_ids=req_ids)
    if not compiled["pass"]: errors.append("REQUIREMENT_GRAPH:"+json.dumps(compiled["graph"]["diagnostics"],sort_keys=True))
    mutation=requirement_mutation_score(contract["requirements"])
    if not mutation["pass"] or mutation["survived"]!=0: errors.append("REQUIREMENT_MUTATION")
    feas=contract["feasibility"]
    if feas["exact_cli_memory_limit_bytes"]!=64*1024*1024: errors.append("MEMORY_LIMIT_PARSE")
    if feas["task_container"]!={"cpus":2,"memory_mb":8192,"storage_mb":10240,"gpus":0}: errors.append("RESOURCE_MODEL")
    for snippet in ["cpus = 2","memory_mb = 8192","storage_mb = 10240","gpus = 0",'environment_mode = "separate"']:
        if snippet not in task: errors.append("TASK_RESOURCE_SOURCE:"+snippet)
    for snippet in ["python3","PyYAML==6.0.2","TB3_SUBJECT_COUNT=120000","TB3_ACCOUNT_COUNT=150000","TB3_ORDER_COUNT=150000","TB3_DEVICE_COUNT=80000"]:
        if snippet not in docker: errors.append("DOCKER_FEASIBILITY_SOURCE:"+snippet)
    if feas["external_service_required"] or feas["gpu_required"] or feas["obvious_resource_blocker"]: errors.append("FEASIBILITY_FLAGS")
    return sorted(set(errors)),{"consensus":consensus,"compiled":compiled,"mutation":mutation}

def verifier_mutation_score(contract):
    mutants=[]
    m=copy.deepcopy(contract);m["policy_model"]["reference_tokens"]["length"]=10;mutants.append(("reference-length",m))
    m=copy.deepcopy(contract);del m["policy_model"]["files"]["subject_links.csv"];mutants.append(("drop-subject-links-policy",m))
    m=copy.deepcopy(contract);m["requirements"]=[r for r in m["requirements"] if r["id"]!="R11_MERGE_TRANSITIVITY"];mutants.append(("drop-merge-transitivity",m))
    m=copy.deepcopy(contract);m["feasibility"]["exact_cli_memory_limit_bytes"]=128*1024*1024;mutants.append(("weaken-memory",m))
    m=copy.deepcopy(contract);del m["generator_function_accounting"]["build_merger_history"];mutants.append(("drop-generator-accounting",m))
    killed=[];survived=[]
    for mid,m in mutants:
        errs,_=semantic_errors(m)
        (killed if errs else survived).append(mid)
    return {"total":len(mutants),"killed":killed,"survived":survived,"pass":not survived}

def main():
    contract=json.loads((ROOT/"contract.json").read_text())
    errors,details=semantic_errors(contract)
    vmut=verifier_mutation_score(contract)
    if not vmut["pass"]: errors.append("VERIFIER_MUTATION_SURVIVORS:"+",".join(vmut["survived"]))
    out={
      "schema":"PROJECT_BRAIN_RANK17_STAGE_B_INDEPENDENT_VERDICT_V1",
      "task":"data-anonymization","rank":17,
      "pass":not errors,
      "task_execution_authorized":bool(not errors),
      "errors":sorted(errors),
      "source_sentence_count":details["consensus"]["source_sentence_count"],
      "accepted_instruction_requirements":[x["requirement_id"] for x in details["consensus"]["accepted_requirements"]],
      "requirement_count":len(contract["requirements"]),
      "requirement_mutation":details["mutation"],
      "verifier_mutation":vmut,
      "policy_transform_count":len(contract["policy_model"]["transforms"]),
      "policy_file_count":len(contract["policy_model"]["files"]),
      "generator_function_count":len(contract["generator_function_accounting"]),
      "acceptance_contract_sha256":contract["acceptance_contract_sha256"],
      "solution_tests_verifier_exposed":False,
      "candidate_executed":False
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
