from __future__ import annotations
import asyncio, hashlib, json, pathlib, sys
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from canonical.runtime import harbor_science_agent_v1 as s

class Receipt:
    def __init__(self,returncode=0,stdout="ok",stderr=""):
        self.returncode=returncode; self.stdout=stdout; self.stderr=stderr
class Env:
    def __init__(self): self.commands=[]
    async def exec(self,command,timeout_sec=None,**kwargs):
        self.commands.append(command); return Receipt()

def goal(n):
    return "\n".join(f"Create verified artifact {i}." for i in range(n))

errors=[]
def need(cond,msg):
    if not cond: errors.append(msg)

g=goal(87)
contract,localized,rows=s._compile_lossless_task_scope(g)
summary=s._planner_raw_task_manifest_summary(g,contract,localized,rows)
required=contract["acceptance_contract"]["required_obligation_ids"]
need(len(rows)==87 and len(required)==87,"FULL_87_OBLIGATIONS_NOT_PRESERVED")
need(localized["accounted_obligation_count"]==87,"LOCALIZATION_NOT_87")
need(summary["required_obligation_count"]==87,"SUMMARY_COUNT_NOT_87")
need(summary["objective_route_obligation_count"]+summary["semantic_residual_obligation_count"]==87,"PARTITION_NOT_TOTAL")
need(summary["brain_retains_full_per_obligation_acceptance_contract"] is True,"FULL_CONTRACT_NOT_RETAINED")
need(summary["every_original_obligation_still_requires_independent_acceptance"] is True,"ACCEPTANCE_WEAKENED")
need(summary["planner_acceptance_or_finish_authority"] is False,"PLANNER_AUTHORITY_ESCALATED")

normalized=[{
    "obligation_id":row["obligation_id"],
    "segment_sha256":row["segment_sha256"],
    "segment_index":row["segment_index"],
    "span":row["span"],
    "acceptance_route_status":row["acceptance_route_status"],
    "acceptance_receipt_required":True,
} for row in rows]
expected=hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
need(summary["ordered_manifest_sha256"]==expected,"MANIFEST_HASH_MISMATCH")

bad=[dict(x) for x in rows]; bad[0]["segment_sha256"]="0"*64
try:
    s._planner_raw_task_manifest_summary(g,contract,localized,bad)
    errors.append("TAMPERED_SOURCE_HASH_ACCEPTED")
except RuntimeError as exc:
    need("SOURCE_HASH_MISMATCH" in str(exc),"TAMPER_FAILED_FOR_WRONG_REASON")

old_bytes=len(json.dumps(rows,sort_keys=True).encode())
new_bytes=len(json.dumps(summary,sort_keys=True).encode())
need(new_bytes*5 < old_bytes,f"METADATA_COMPRESSION_INSUFFICIENT:{old_bytes}:{new_bytes}")
need(contract["acceptance_contract"]["raw_source_is_final_semantic_reference"] is True,"RAW_SOURCE_NOT_FINAL")
need(contract["nonwhitespace_source_coverage_complete"] is True,"RAW_SOURCE_COVERAGE_INCOMPLETE")

seen=[]
def plan(prompt,timeout_s=20):
    seen.append(prompt)
    return {"text":json.dumps({
        "material_requirements":["R1"],
        "candidates":[{"action_id":"a","covers":["R1"],"command":"echo work","verify_command":"echo verify"}],
    }),"model":"synthetic-fixed-substrate"}

with patch.object(s.science_planner,"plan",plan):
    result=asyncio.run(s.run_science_goal(g,Env(),max_cycles=1))
need(len(seen)==1,"PLANNER_CALL_COUNT")
need(("Goal: "+g) in seen[0],"EXACT_GOAL_MISSING_FROM_PROMPT")
need("PROJECT_BRAIN_SCIENCE_RAW_TASK_PLANNER_MANIFEST_SUMMARY_V1" in seen[0],"SUMMARY_SCHEMA_MISSING")
need('"obligation_id": "RAWREQ:' not in seen[0],"RAWREQ_ROWS_STILL_DUMPED")
need(result["raw_task_required_obligation_count"]==87,"RESULT_OBLIGATION_COUNT_DRIFT")
need(bool(result.get("raw_task_prompt_manifest_sha256")),"RESULT_MANIFEST_HASH_MISSING")
need(result["task_completion_claimed"] is False,"FALSE_COMPLETION")
need(result["finish_authority"]=="RAW_TASK_ACCEPTANCE_V1_REQUIRED","FINISH_AUTHORITY_DRIFT")

out={
  "schema":"PROJECT_BRAIN_TB_SCIENCE_PLANNER_MANIFEST_SUMMARY_VERIFY_V1",
  "pass":not errors,
  "status":"PASS__87_OF_87_ACCEPTANCE_PRESERVED__PLANNER_METADATA_GT5X_SMALLER__RAWREQ_DUMP_REMOVED__ZERO_BENCHMARK_EXPOSURE" if not errors else "FAIL_CLOSED",
  "errors":errors,
  "agent_blob_expected":"d397324f411d002bdbdca348aaad708b5b40c9c2",
  "synthetic_obligation_count":87,
  "old_metadata_bytes":old_bytes,
  "new_metadata_bytes":new_bytes,
  "metadata_reduction_ratio":old_bytes/new_bytes,
  "benchmark_task_exposure":0,
  "benchmark_trials_executed":0,
  "acceptance_credit_delta":0,
  "terminal_credit_delta":0,
}
print(json.dumps(out,sort_keys=True))
pathlib.Path("RANK14_PLANNER_MANIFEST_SUMMARY_VERIFY.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
raise SystemExit(0 if not errors else 1)
