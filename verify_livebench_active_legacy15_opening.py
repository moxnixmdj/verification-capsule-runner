#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, json, urllib.request
from pathlib import Path

LB_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
LEGACY_URL=f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LB_COMMIT}/livebench/if_runner/instruction_following_eval/instructions_registry.py"
MODERN_URL=f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LB_COMMIT}/livebench/if_runner/ifbench/instructions_registry.py"
LEGACY_BLOB="903ed738398648c7cfac61d5ffa478c22f1f0891"
MODERN_BLOB="adfed4832877566e62970257b50c6fa32c302fb2"
EXPECTED_SET_COMMITMENT="af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"

ACTIVE_IDS=(
    "keywords:existence",
    "keywords:forbidden_words",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:number_sentences",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:title",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "combination:repeat_prompt",
    "combination:two_responses",
    "startend:end_checker",
    "startend:quotation",
)

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read()

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def eval_str(node, env):
    if isinstance(node, ast.Constant) and isinstance(node.value,str): return node.value
    if isinstance(node, ast.Name) and node.id in env: return env[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op,ast.Add):
        a,b=eval_str(node.left,env),eval_str(node.right,env)
        if isinstance(a,str) and isinstance(b,str): return a+b
    return None

def registry_keys(src: str) -> set[str]:
    tree=ast.parse(src)
    env={}
    for n in tree.body:
        if isinstance(n,(ast.Assign,ast.AnnAssign)):
            value=n.value
            targets=n.targets if isinstance(n,ast.Assign) else [n.target]
            v=eval_str(value,env)
            if isinstance(v,str):
                for t in targets:
                    if isinstance(t,ast.Name): env[t.id]=v
    out=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Assign):
            for t in n.targets:
                if isinstance(t,ast.Name) and t.id=="INSTRUCTION_DICT" and isinstance(n.value,ast.Dict):
                    for k in n.value.keys:
                        v=eval_str(k,env)
                        if isinstance(v,str): out.add(v)
        if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.target.id=="INSTRUCTION_DICT" and isinstance(n.value,ast.Dict):
            for k in n.value.keys:
                v=eval_str(k,env)
                if isinstance(v,str): out.add(v)
    return out

def main():
    legacy_raw=fetch(LEGACY_URL)
    modern_raw=fetch(MODERN_URL)
    assert git_blob(legacy_raw)==LEGACY_BLOB
    assert git_blob(modern_raw)==MODERN_BLOB
    legacy=registry_keys(legacy_raw.decode())
    modern=registry_keys(modern_raw.decode())
    assert len(legacy)==25, len(legacy)
    assert set(ACTIVE_IDS) <= legacy, sorted(set(ACTIVE_IDS)-legacy)
    assert not (set(ACTIVE_IDS)&modern), sorted(set(ACTIVE_IDS)&modern)
    commitment=hashlib.sha256(json.dumps(sorted(ACTIVE_IDS)).encode()).hexdigest()
    assert commitment==EXPECTED_SET_COMMITMENT
    out={
      "schema":"PROJECT_BRAIN_LIVEBENCH_ACTIVE_LEGACY15_OPENING_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS__EXISTING_TERMINAL_SET_COMMITMENT_OPENED_TO_15_PINNED_LEGACY_IDS",
      "pinned_source":{
        "livebench_commit":LB_COMMIT,
        "legacy_registry_git_blob_sha":git_blob(legacy_raw),
        "modern_registry_git_blob_sha":git_blob(modern_raw),
        "legacy_registry_count":len(legacy),
        "modern_registry_count":len(modern),
      },
      "opening":{
        "active_ids":list(ACTIVE_IDS),
        "active_distinct_id_count":len(set(ACTIVE_IDS)),
        "recomputed_sha256":commitment,
        "expected_sha256":EXPECTED_SET_COMMITMENT,
        "all_active_ids_in_legacy_registry":True,
        "active_modern_intersection_count":0,
      },
      "firewall":{
        "terminal_dataset_downloaded":False,
        "terminal_prompt_content_read":False,
        "terminal_kwargs_read":False,
        "terminal_question_ids_read":False,
        "terminal_responses_generated":0,
      },
      "hard_nonclaims":[
        "NO_CASE_FREQUENCY_OR_COMBINATION_INFERENCE",
        "NO_LIVEBENCH_PASS_OR_SCORE",
        "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
      ],
      "accounting":{"incremental_spend_usd":0,"new_terminal_cases_exposed":0,"acceptance_credit_delta":0},
    }
    Path("livebench_active_legacy15_opening_receipt.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
