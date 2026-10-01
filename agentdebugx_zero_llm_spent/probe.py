#!/usr/bin/env python3
import json
from pathlib import Path

from agentdebug.diagnose.pipeline import DiagnosePipeline
from agentdebug.schema import AgentEvent, AgentTrajectory, EventType

HERE=Path(__file__).resolve().parent
capsule=json.loads((HERE/"cases.json").read_text())
pipeline=DiagnosePipeline.local_default()
rows=[]

for case in capsule["cases"]:
    trace=AgentTrajectory(goal=case["goal"], framework="project-brain-spent-screen")
    for raw in case["events"]:
        trace.add_event(AgentEvent(
            trace_id=trace.trace_id,
            event_type=EventType(raw["event_type"]),
            step_index=raw.get("step_index"),
            agent_name=raw.get("agent_name","agent"),
            input=raw.get("input"),
            output=raw.get("output"),
            error=raw.get("error"),
            metadata=raw.get("metadata",{}),
        ))
    result=pipeline.run(trace)
    report=result.report
    primary_mode=report.findings[0].failure_mode.mode_id if report.findings else None
    root_step=report.root_cause_step_index
    attribution_step=(
        result.attribution.hypotheses[0].step_index
        if result.attribution and result.attribution.hypotheses
        else None
    )
    row={
        "id":case["id"],
        "expected_root_step":case["expected_root_step"],
        "observed_root_step":root_step,
        "expected_primary_mode":case["expected_primary_mode"],
        "observed_primary_mode":primary_mode,
        "attribution_step":attribution_step,
        "root_step_correct":root_step==case["expected_root_step"],
        "primary_mode_correct":primary_mode==case["expected_primary_mode"],
        "attribution_consistent":attribution_step==root_step,
        "finding_count":len(report.findings),
        "summary":report.summary,
    }
    rows.append(row)

n=len(rows)
result={
  "schema":"PROJECT_BRAIN_AGENTDEBUGX_ZERO_LLM_SPENT_SCREEN_RESULT_V1",
  "status":"MEASUREMENT_ONLY__ZERO_CAPABILITY_CREDIT",
  "package":"agentdebugx",
  "version":"0.5.2",
  "mode":"DiagnosePipeline.local_default",
  "cases":n,
  "root_step_accuracy":sum(r["root_step_correct"] for r in rows)/n,
  "primary_mode_accuracy":sum(r["primary_mode_correct"] for r in rows)/n,
  "attribution_consistency":sum(r["attribution_consistent"] for r in rows)/n,
  "wrong_root_cases":[r["id"] for r in rows if not r["root_step_correct"]],
  "wrong_mode_cases":[r["id"] for r in rows if not r["primary_mode_correct"]],
  "rows":rows,
  "capability_credit_delta":0
}
(HERE/"result.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:result[k] for k in [
  "cases","root_step_accuracy","primary_mode_accuracy","attribution_consistency",
  "wrong_root_cases","wrong_mode_cases"
]},indent=2))
