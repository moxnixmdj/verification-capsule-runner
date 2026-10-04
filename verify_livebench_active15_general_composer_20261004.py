#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
SUBJECT=ROOT/"subject/livebench_active15_general_composer_20261004"
sys.path.insert(0,str(SUBJECT))

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_general_composer_v1 as composer

SCHEMA="PROJECT_BRAIN_LIVEBENCH_ACTIVE15_GENERAL7296_PUBLIC_VERIFICATION_V1"
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
REGISTRY_BLOB="903ed738398648c7cfac61d5ffa478c22f1f0891"
INSTRUCTIONS_BLOB="4997bab885a676d92545fd91a9a20b48d234a2b2"
GENERAL_ARCHETYPES={"NTH_PARAGRAPH","STAR_PARAGRAPH","SENTENCE","PLAIN"}
EXPECTED_GENERAL_SETS=912
EXPECTED_CASES=7296

BASE_PREFIX=(
 "The following are the beginning sentences of a news article from the Guardian.\n"
 "-------\n"
 "A verified public source describes a system and its measured behavior. "
 "The source contains ordinary prose for deterministic testing.\n"
 "-------\n"
 "Please summarize based on the sentences provided."
)

PROFILES=(
 {"name":"LOWER_BOUNDS_SMALL","existence":["rock","river","signal","system","brain"],"forbidden":["rock","apple","market","glass","shoe"],"paragraphs":2,"words":(120,"at least"),"sentences":(4,"at least"),"nth":(3,2,"river"),"postscript":"P.S.","bullets":2,"sections":("Section",2),"end":"Any other questions?"},
 {"name":"UPPER_BOUNDS_MID","existence":["amber","cedar","orbit","meadow","quartz"],"forbidden":["apple","market","glass","shoe","hotel"],"paragraphs":4,"words":(300,"less than"),"sentences":(8,"less than"),"nth":(4,3,"signal"),"postscript":"P.P.S","bullets":4,"sections":("SECTION",4),"end":"Is there anything else I can help with?"},
 {"name":"LOWER_BOUNDS_HIGH","existence":["western","primary","growth","world","bridge"],"forbidden":["candy","purple","airport","winter","soup"],"paragraphs":5,"words":(500,"at least"),"sentences":(18,"at least"),"nth":(5,5,"world"),"postscript":"P.S.","bullets":5,"sections":("Section",5),"end":"Any other questions?"},
 {"name":"UPPER_BOUNDS_EDGE","existence":["source","proof","stable","result","truth"],"forbidden":["rock","apple","market","glass","shoe"],"paragraphs":1,"words":(100,"less than"),"sentences":(2,"less than"),"nth":(1,1,"source"),"postscript":"P.P.S","bullets":1,"sections":("SECTION",1),"end":"Is there anything else I can help with?"},
)

def blob_sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def kwargs_for(iid:str,p:dict[str,Any])->dict[str,Any]:
    if iid=="keywords:existence": return {"keywords":list(p["existence"])}
    if iid=="keywords:forbidden_words": return {"forbidden_words":list(p["forbidden"])}
    if iid=="length_constraints:number_paragraphs": return {"num_paragraphs":int(p["paragraphs"])}
    if iid=="length_constraints:number_words":
        n,rel=p["words"]; return {"num_words":int(n),"relation":str(rel)}
    if iid=="length_constraints:number_sentences":
        n,rel=p["sentences"]; return {"num_sentences":int(n),"relation":str(rel)}
    if iid=="length_constraints:nth_paragraph_first_word":
        num,nth,first=p["nth"]; return {"num_paragraphs":int(num),"nth_paragraph":int(nth),"first_word":str(first)}
    if iid=="detectable_content:postscript": return {"postscript_marker":str(p["postscript"])}
    if iid=="detectable_format:number_bullet_lists": return {"num_bullets":int(p["bullets"])}
    if iid=="detectable_format:multiple_sections":
        split,n=p["sections"]; return {"section_spliter":str(split),"num_sections":int(n)}
    if iid=="startend:end_checker": return {"end_phrase":str(p["end"])}
    if iid in {"detectable_format:title","startend:quotation"}: return {}
    raise KeyError(iid)

def render_prompt(ids:tuple[str,...],profile:dict[str,Any],registry,reverse:bool):
    ordered=list(ids)
    if reverse: ordered.reverse()
    desc=[]; records=[]
    for iid in ordered:
        inst=registry.INSTRUCTION_DICT[iid](iid)
        kw=kwargs_for(iid,profile)
        desc.append(inst.build_description(**kw))
        records.append({"instruction_id":iid,"kwargs":kw})
    return BASE_PREFIX+" "+" ".join(desc),records

def exact_check(response:str,records:list[dict[str,Any]],registry):
    failed=[]
    for rec in records:
        iid=rec["instruction_id"]
        inst=registry.INSTRUCTION_DICT[iid](iid)
        inst.build_description(**rec["kwargs"])
        try: ok=bool(inst.check_following(response))
        except Exception as exc:
            failed.append(iid+":EXCEPTION:"+type(exc).__name__); continue
        if not ok: failed.append(iid)
    return not failed,failed

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--livebench-root",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--max-failures",type=int,default=200)
    ns=ap.parse_args()
    outp=Path(ns.output)
    try:
        lb=Path(ns.livebench_root).resolve()
        legacy=lb/"livebench/if_runner/instruction_following_eval"
        assert blob_sha(legacy/"instructions_registry.py")==REGISTRY_BLOB
        assert blob_sha(legacy/"instructions.py")==INSTRUCTIONS_BLOB
        sys.path.insert(0,str(lb/"livebench/if_runner"))
        from instruction_following_eval import instructions_registry as registry

        sets=tuple(x for x in archetypes.enumerate_compatible_sets() if archetypes.archetype(x) in GENERAL_ARCHETYPES)
        assert len(sets)==EXPECTED_GENERAL_SETS,(len(sets),EXPECTED_GENERAL_SETS)

        total=passed=runtime_block=exact_fail=0
        by_arch=defaultdict(Counter); errors=Counter(); failed_ids=Counter(); samples=[]
        for ids in sets:
            arch=archetypes.archetype(ids)
            for profile in PROFILES:
                for reverse in (False,True):
                    total+=1
                    prompt,records=render_prompt(ids,profile,registry,reverse)
                    got=composer.compose_visible_prompt(prompt)
                    if got.get("status")!="PASS_CANDIDATE_GENERAL_BRANCH":
                        runtime_block+=1
                        err=str(got.get("error") or got.get("status"))
                        errors[err]+=1; by_arch[arch]["runtime_block"]+=1
                        if len(samples)<ns.max_failures:
                            samples.append({"ids":list(ids),"arch":arch,"profile":profile["name"],"reverse":reverse,"stage":"runtime","error":err})
                        continue
                    ok,failed=exact_check(str(got.get("response") or ""),records,registry)
                    if ok:
                        passed+=1; by_arch[arch]["pass"]+=1
                    else:
                        exact_fail+=1; by_arch[arch]["exact_fail"]+=1
                        for iid in failed: failed_ids[iid]+=1
                        if len(samples)<ns.max_failures:
                            samples.append({"ids":list(ids),"arch":arch,"profile":profile["name"],"reverse":reverse,"stage":"checker","failed_ids":failed})
        assert total==EXPECTED_CASES,(total,EXPECTED_CASES)
        receipt={
          "schema":SCHEMA,
          "status":"PASS__ALL_7296_GENERAL_SYNTHETIC_CASES" if passed==total else "FAIL_CLOSED__GENERAL_REPAIR_LEDGER",
          "bindings":{"livebench_commit":LIVEBENCH_COMMIT,"registry_blob":REGISTRY_BLOB,"instructions_blob":INSTRUCTIONS_BLOB},
          "scope":{"general_set_count":len(sets),"synthetic_cases":total,"archetypes":sorted(GENERAL_ARCHETYPES),"profiles":len(PROFILES),"orders":2,"terminal_rows_read":0},
          "results":{"pass":passed,"runtime_block":runtime_block,"exact_fail":exact_fail,"pass_fraction":passed/total},
          "by_archetype":{k:dict(v) for k,v in sorted(by_arch.items())},
          "runtime_errors":dict(errors.most_common()),
          "exact_failed_instruction_ids":dict(failed_ids.most_common()),
          "failure_samples":samples,
          "hard_nonclaims":["ZERO_TERMINAL_ROW_EVIDENCE","GENERAL_FOUR_ARCHETYPES_ONLY","NO_ACCEPTANCE_CREDIT"],
        }
        outp.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps({"status":receipt["status"],**receipt["results"]},sort_keys=True))
        return 0 if passed==total else 1
    except Exception as exc:
        import traceback
        receipt={"schema":SCHEMA,"status":"EXCEPTION__FAIL_CLOSED","exception_type":type(exc).__name__,"exception_message":str(exc),"traceback":traceback.format_exc(),"terminal_rows_read":0}
        outp.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps({"status":receipt["status"],"exception_type":receipt["exception_type"],"exception_message":receipt["exception_message"]},sort_keys=True))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
