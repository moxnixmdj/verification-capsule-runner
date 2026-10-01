#!/usr/bin/env python3
import json
from pathlib import Path
from agentdebug.diagnose.pipeline import DiagnosePipeline
from agentdebug.schema import AgentEvent, AgentTrajectory, EventType

HERE=Path(__file__).resolve().parent
capsule=json.loads((HERE/"cases.json").read_text())
pipe=DiagnosePipeline.local_default()
rows=[]
for c in capsule["cases"]:
    t=AgentTrajectory(goal=c["query"],framework="project-brain-c3-terminal-delta")
    t.add_event(AgentEvent(
        trace_id=t.trace_id,event_type=EventType.OBSERVATION,step_index=1,
        agent_name="task",output={"query":c["query"]}
    ))
    t.add_event(AgentEvent(
        trace_id=t.trace_id,event_type=EventType.AGENT_STEP,step_index=2,
        agent_name="router",output={"selected_route":c["selected_route"]}
    ))
    tool_error = (
        c["tool_output"].split("TOOL_ERROR:",1)[1]
        if c["tool_output"].startswith("TOOL_ERROR:")
        else None
    )
    t.add_event(AgentEvent(
        trace_id=t.trace_id,event_type=EventType.TOOL_RESULT,step_index=3,
        agent_name="executor",output=c["tool_output"],
        error=tool_error
    ))
    verifier_error=(
        f"terminal verification mismatch: expected route={c['expected_route']} "
        f"output={c['expected_output']}; observed route={c['selected_route']} "
        f"output={c['tool_output']}"
    )
    t.add_event(AgentEvent(
        trace_id=t.trace_id,event_type=EventType.GUARDRAIL,step_index=4,
        agent_name="verifier",error=verifier_error,
        metadata={"status":"failed"}
    ))
    out=pipe.run(t)
    report=out.report
    observed=report.root_cause_step_index
    rows.append({
      "id":c["id"],
      "expected_root_step":c["expected_root_step"],
      "observed_root_step":observed,
      "root_localization_correct":observed==c["expected_root_step"],
      "root_cause_agent":report.root_cause_agent,
      "finding_modes":[f.failure_mode.mode_id for f in report.findings],
      "finding_steps":[f.step_index for f in report.findings],
      "summary":report.summary
    })
n=len(rows)
result={
  "schema":"PROJECT_BRAIN_AGENTDEBUGX_REAL_SPENT_C3_TRACE_SCREEN_RESULT_V1",
  "status":"SPENT_REAL_TRACE_SCREEN__ZERO_CAPABILITY_CREDIT",
  "package":"agentdebugx","version":"0.5.2","mode":"DiagnosePipeline.local_default",
  "cases":n,
  "root_localization_accuracy":sum(r["root_localization_correct"] for r in rows)/n,
  "wrong_root_cases":[r["id"] for r in rows if not r["root_localization_correct"]],
  "rows":rows,
  "interpretation_rule":"SUCCESS_REQUIRES_LOCALIZING_THE_CAUSAL_ROUTING_DECISION_AT_STEP_2__BLAMING_ONLY_DOWNSTREAM_TOOL_OR_VERIFIER_FAILURE_DOES_NOT_COUNT",
  "capability_credit_delta":0
}
(HERE/"result.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:result[k] for k in ["cases","root_localization_accuracy","wrong_root_cases"]},indent=2))
