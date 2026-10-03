#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,sys,importlib.util
RAW_SHA256="fa764e4d337083050f45ab7453865fd232a37962c9b09ac58952c0c30034bc40"
RECEIPT="canonical/verification/RETRIEVAL_V10_CONTEXTUAL_LIVE_PROVIDER_EPOCH_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
TARGETS={
"V10_FASTAPI":{"GITHUB":{"github:fastapi/fastapi"}},
"V10_TESSERACT":{"GITHUB":{"github:tesseract-ocr/tesseract"}},
"V10_REACT":{"NPM":{"npm:react"},"GITHUB":{"github:facebook/react"}},
"V10_REACT_ROTATE":{"NPM":{"npm:react"},"GITHUB":{"github:facebook/react"}},
"V10_SERDE":{"CRATES":{"crates:serde"},"GITHUB":{"github:serde-rs/serde"}},
"V10_SERDE_ROTATE":{"CRATES":{"crates:serde"},"GITHUB":{"github:serde-rs/serde"}},
"V10_BERT":{"HUGGINGFACE":{"hf:google-bert/bert-base-uncased"}},
"V10_CLIP":{"GITHUB":{"github:openai/clip"},"HUGGINGFACE":{"hf:openai/clip-vit-base-patch32"}},
"V10_ATTENTION":{"OPENALEX":{"openalex:w2626778328"}},
"V10_RESNET":{"OPENALEX":{"openalex:w2194775991"},"CROSSREF":{"doi:10.1109/cvpr.2016.90"}},
"V10_LISTCOMP":{},"V10_RUSTLIFETIME":{},
}
ENTITIES={
"V10_FASTAPI":{"github:fastapi/fastapi":"entity:fastapi"},
"V10_TESSERACT":{"github:tesseract-ocr/tesseract":"entity:tesseract"},
"V10_REACT":{"npm:react":"entity:react","github:facebook/react":"entity:react"},
"V10_REACT_ROTATE":{"npm:react":"entity:react","github:facebook/react":"entity:react"},
"V10_SERDE":{"crates:serde":"entity:serde","github:serde-rs/serde":"entity:serde"},
"V10_SERDE_ROTATE":{"crates:serde":"entity:serde","github:serde-rs/serde":"entity:serde"},
"V10_BERT":{"hf:google-bert/bert-base-uncased":"entity:bert-base-uncased"},
"V10_CLIP":{"github:openai/clip":"entity:openai-clip","hf:openai/clip-vit-base-patch32":"entity:openai-clip"},
"V10_ATTENTION":{"openalex:w2626778328":"entity:attention-is-all-you-need"},
"V10_RESNET":{"openalex:w2194775991":"entity:deep-residual-learning","doi:10.1109/cvpr.2016.90":"entity:deep-residual-learning"},
"V10_LISTCOMP":{},"V10_RUSTLIFETIME":{},
}
LEGACY={"episode_id":"TOOL_DISCOVERY_GITHUB_WAKE_20261003_V1","task_class":"TOOL_DISCOVERY_EVIDENCE","source_id":"GITHUB_CODE_SURFACE","upstream_group":"GITHUB_PUBLIC_INDEX_AND_API","action_id":"GITHUB_CODE_SOURCE_EPOCH_V1","sequence":1,"status":"SUCCESS","candidate_ids":["malob/ai-system-cards:cards/anthropic/claude-opus-5-5/sections/08b-capabilities-2.md","SYuan03/benchboard:data-packs/releases-2026-09-28.js","WaitHZ/toolathlon-website:docs/blog/toolathlon-verified.mdx","WaitHZ/toolathlon-website:task-pages.json"],"candidate_entities":{},"verified_sufficient_candidate_ids":[],"independent_receipt":None,"latency_seconds":0,"request_count":9}

def load_ledger(path:pathlib.Path):
 spec=importlib.util.spec_from_file_location("ledger_v3",path)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 root=pathlib.Path(__file__).resolve().parent
 raw=root/"input"/"retrieval_v10_live_epoch_v2.json"
 b=raw.read_bytes()
 assert hashlib.sha256(b).hexdigest()==RAW_SHA256
 obj=json.loads(b)
 assert obj["schema"]=="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_EPOCH_V2"
 assert obj["event_count"]==30 and obj["episode_count"]==12
 corrected=[]
 for e in obj["events"]:
  ep=e["episode_id"];src=e["source_id"];ids=list(e["candidate_ids"])
  expected=TARGETS[ep].get(src,set())
  suff=sorted(set(ids)&set(expected))
  em={cid:ENTITIES[ep][cid] for cid in ids if cid in ENTITIES[ep]}
  x={k:v for k,v in e.items() if k not in {"verified_sufficient_candidate_ids","independent_receipt"}}
  x["candidate_entities"]=em
  x["verified_sufficient_candidate_ids"]=suff
  x["independent_receipt"]=RECEIPT if suff else None
  corrected.append(x)
 events=[LEGACY]+corrected
 outdir=root/"subjects"/"v10e";outdir.mkdir(parents=True,exist_ok=True)
 state=outdir/"retrieval_live_events_v3.jsonl"
 state.write_text("\n".join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")) for x in events)+"\n",encoding="utf-8")
 ledger=load_ledger(outdir/"retrieval_live_event_ledger_v3.py")
 cal=ledger.aggregate(events)
 assert cal["event_count"]==31
 assert cal["episode_count"]==13
 assert cal["task_class_count"]==7
 assert sum(x["status"]=="SUCCESS" for x in corrected)==28
 assert sum(x["status"]=="FAILED_RETRYABLE" for x in corrected)==2
 assert sum(bool(x["verified_sufficient_candidate_ids"]) for x in corrected)==7
 assert cal["task_class_source_stats"]["CODE_REPOSITORY"]["GITHUB"]["sufficient_witness_actions"]==2
 assert cal["task_class_source_stats"]["CODE_REPOSITORY"]["CODEBERG"]["failures"]==2
 assert cal["task_class_source_stats"]["MODEL_HUB"]["HUGGINGFACE"]["sufficient_witness_actions"]==1
 assert cal["task_class_source_stats"]["SCHOLARLY_WORK"]["OPENALEX"]["sufficient_witness_actions"]==2
 assert cal["task_class_source_stats"]["SCHOLARLY_WORK"]["CROSSREF"]["sufficient_witness_actions"]==1
 scholarly=cal["task_class_pairwise_candidate_overlap"]["SCHOLARLY_WORK"]
 pair=next(x for x in scholarly if {x["source_a"],x["source_b"]}=={"CROSSREF","OPENALEX"})
 assert pair["intersection_entity_observations"]>=1
 manifest={"schema":"PROJECT_BRAIN_RETRIEVAL_V10_LIVE_STATE_DERIVATION_V1","raw_artifact":{"workflow_run_id":37157325986,"artifact_id":11285937655,"sha256":RAW_SHA256,"raw_event_count":30},"derived_state":{"event_count":31,"episode_count":13,"task_class_count":7,"source_count":len({x["source_id"] for x in events}),"live_success_count":28,"live_retryable_failure_count":2,"verified_sufficient_event_count":7,"state_sha256":hashlib.sha256(state.read_bytes()).hexdigest()},"corrections":["TITLE_ONLY_SCHOLARLY_SUFFICIENCY_REMOVED","SUFFICIENCY_REQUIRES_FROZEN_EXACT_TARGET_ID","EXPLICIT_CROSS_SOURCE_ENTITY_EQUIVALENCE_APPLIED","UNMAPPED_CANDIDATES_REMAIN_SOURCE_SCOPED"],"open_world_completeness_claim":False,"incremental_spend_usd":0}
 (outdir/"retrieval_v10_live_state_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps(manifest,sort_keys=True))
if __name__=="__main__":main()
