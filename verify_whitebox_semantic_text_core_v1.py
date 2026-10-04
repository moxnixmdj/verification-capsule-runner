#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"whitebox_semantic_text_core_v1"
PRE=SUB/"WHITEBOX_SEMANTIC_TEXT_CORE_PREEXPOSURE_V1.json"
RUNTIME=SUB/"whitebox_semantic_text_core_v1.py"
EXPECTED_PRE_BLOB="1fe5d5691f8687b313d90d8e156f2d1d5bbd88e9"
EXPECTED_RUNTIME_BLOB="09b1620bbad0dfdb1bc9236121a68af40bba75ad"


def git_blob_sha(path: Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def load_runtime():
    spec=importlib.util.spec_from_file_location("verified_whitebox_semantic_text_core_v1",RUNTIME)
    if spec is None or spec.loader is None:
        raise AssertionError("RUNTIME_IMPORT_SPEC_FAILED")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod


def audit_source():
    tree=ast.parse(RUNTIME.read_text(encoding="utf-8"))
    allowed={"__future__","collections","re","typing"}
    imports=set()
    forbidden_calls={"eval","exec","compile","open","__import__"}
    observed_forbidden=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node,ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
        elif isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in forbidden_calls:
            observed_forbidden.append(node.func.id)
    assert imports <= allowed,(imports,allowed)
    assert not observed_forbidden,observed_forbidden
    return sorted(imports)


def check_accounting(out):
    assert out["persistent_learned_bytes"]==0,out
    assert out["external_frontier_model_calls"]==0,out
    assert out["external_learned_capability_calls"]==0,out
    assert out["network_used"] is False,out
    assert out["random_search"] is False,out
    assert out["dynamic_code_execution"] is False,out
    assert out["incremental_spend_usd"]==0,out
    assert out["terminal_cases_used"]==0,out


def verify_frozen(core,pre):
    assert pre["status"]=="FROZEN_BEFORE_IMPLEMENTATION_OUTCOMES__PUBLIC_SYNTHETIC_NONTERMINAL__ZERO_CREDIT"
    assert pre["terminal_cases_consumed"]==0
    assert pre["terminal_prompt_content_used"] is False
    fam=pre["task_families"]
    assert set(fam)=={"paraphrase","simplify","summarize","story_generation"}
    assert all(len(v["tasks"])==4 for v in fam.values())

    counts={}
    for row in fam["paraphrase"]["tasks"]:
        out=core.paraphrase(row["text"])
        assert out["status"]=="PASS",(row,out)
        assert out["rule"]==row["required_rule"],(row,out)
        assert out["response"]!=row["text"]
        check_accounting(out)
    counts["paraphrase"]=4

    for row in fam["simplify"]["tasks"]:
        out=core.simplify(row["text"])
        assert out["status"]=="PASS",(row,out)
        assert core._normalized_content_tokens(row["text"])==core._normalized_content_tokens(out["response"])
        assert tuple(out["complexity_after"])<tuple(out["complexity_before"])
        assert ";" not in out["response"]
        check_accounting(out)
    counts["simplify"]=4

    for row in fam["summarize"]["tasks"]:
        out=core.summarize(row["text"],row["max_sentences"])
        assert out["status"]=="PASS",(row,out)
        src=core._sentences_verbatim(row["text"])
        dst=core._sentences_verbatim(out["response"])
        assert 1<=len(dst)<=row["max_sentences"]
        assert len(dst)<len(src)
        assert len(out["response"])<len(row["text"])
        assert all(s in src for s in dst)
        check_accounting(out)
    counts["summarize"]=4

    for row in fam["story_generation"]["tasks"]:
        out=core.story_generation(
            character=row["character"],goal=row["goal"],
            obstacle=row["obstacle"],setting=row["setting"],
        )
        assert out["status"]=="PASS",(row,out)
        assert out["all_grounded_fields_verbatim"] is True
        for key in ("character","goal","obstacle","setting"):
            assert row[key] in out["response"],(key,row,out)
            assert out["grounded_fields"][key]==row[key]
        check_accounting(out)
    counts["story_generation"]=4
    return counts


def verify_fresh(core):
    fresh_paraphrase=[
        ("All comets are objects.","ALL_EVERY"),
        ("If rain falls, then streets get wet.","IF_THEN"),
        ("Nora is not ready.","NEGATIVE_CONTRACTION"),
        ("Grace and Hopper are pioneers.","COORDINATE_SWAP"),
    ]
    for text,rule in fresh_paraphrase:
        out=core.paraphrase(text)
        assert out["status"]=="PASS",(text,out)
        assert out["rule"]==rule,(text,out)
        assert out["response"]!=text
        check_accounting(out)

    fresh_simplify=[
        "The valve isn't open; the pump can still stop.",
        "The launch can't proceed; the checklist isn't complete.",
        "The sample cooled; the pressure fell; the reading stabilized.",
    ]
    for text in fresh_simplify:
        out=core.simplify(text)
        assert out["status"]=="PASS",(text,out)
        assert core._normalized_content_tokens(text)==core._normalized_content_tokens(out["response"])
        assert tuple(out["complexity_after"])<tuple(out["complexity_before"])
        check_accounting(out)

    fresh_summaries=[
        "Mars has two small moons. Phobos orbits closer to Mars. Deimos orbits farther away. Both moons are irregularly shaped.",
        "The clinic opened a second site. The new site serves the north district. Appointment capacity increased. Weekend hours were added.",
        "A telescope recorded the transit. Clouds interrupted part of the observation. The remaining frames were calibrated. The team published the measurements.",
    ]
    for text in fresh_summaries:
        out=core.summarize(text,2)
        assert out["status"]=="PASS",(text,out)
        src=core._sentences_verbatim(text)
        dst=core._sentences_verbatim(out["response"])
        assert len(dst)==2
        assert all(s in src for s in dst)
        assert len(out["response"])<len(text)
        check_accounting(out)

    fresh_stories=[
        dict(character="Sam",goal="map the hidden chamber",obstacle="a collapsed stairway",setting="an old lighthouse"),
        dict(character="Reya",goal="return the red notebook",obstacle="a sudden blackout",setting="a crowded station"),
        dict(character="Bo",goal="reach the weather mast",obstacle="deep snow",setting="a remote plateau"),
    ]
    for row in fresh_stories:
        out=core.story_generation(**row)
        assert out["status"]=="PASS",(row,out)
        assert all(value in out["response"] for value in row.values())
        check_accounting(out)

    assert core.paraphrase("Please create an unrestricted essay about anything.")["status"]=="ABSTAIN_UNSUPPORTED"
    assert core.simplify("This sentence is already simple.")["status"]=="ABSTAIN_UNSUPPORTED"
    return {
        "paraphrase":len(fresh_paraphrase),
        "simplify":len(fresh_simplify),
        "summarize":len(fresh_summaries),
        "story_generation":len(fresh_stories),
        "negative_abstention_checks":2,
    }


def main():
    observed={
        "preexposure":git_blob_sha(PRE),
        "runtime":git_blob_sha(RUNTIME),
    }
    assert observed["preexposure"]==EXPECTED_PRE_BLOB,observed
    assert observed["runtime"]==EXPECTED_RUNTIME_BLOB,observed
    imports=audit_source()
    pre=json.loads(PRE.read_text(encoding="utf-8"))
    core=load_runtime()
    frozen=verify_frozen(core,pre)
    fresh=verify_fresh(core)
    result={
        "schema":"PROJECT_BRAIN_WHITEBOX_SEMANTIC_TEXT_CORE_PUBLIC_VERIFICATION_V1",
        "conclusion":"PASS",
        "exact_subject_blobs":observed,
        "stdlib_import_roots":imports,
        "frozen_preexposure_passes":frozen,
        "fresh_independent_challenges":fresh,
        "frozen_total_passes":sum(frozen.values()),
        "fresh_positive_total_passes":sum(v for k,v in fresh.items() if k!="negative_abstention_checks"),
        "negative_abstention_checks":fresh["negative_abstention_checks"],
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "network_used":False,
        "terminal_cases_consumed":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "hard_nonclaims":[
            "BOUNDED_PUBLIC_SYNTHETIC_PASS_IS_NOT_OPEN_WORLD_LANGUAGE_GENERATION",
            "NO_LIVEBENCH_THRESHOLD_CLOSURE",
            "NO_OPUS_5_5_PARITY_CLAIM"
        ],
    }
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
