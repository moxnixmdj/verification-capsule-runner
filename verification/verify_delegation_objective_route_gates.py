import importlib.util, json
from pathlib import Path

spec=importlib.util.spec_from_file_location("oodc","verification/objective_oracle_dominance_compiler.py")
mod=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)
payload=json.loads(Path("verification/objective_oracle_live_input.json").read_text())
out=mod.compile_dominance(payload)
errors=[]
if out.get("pass") is not True: errors.append("COMPILER_FAIL")
rows={r["behavior_id"]:r for r in out.get("contracts",[])}
d=rows.get("TASK_TO_DELEGATION_GRAPH_001")
if not d: errors.append("DELEGATION_ROW_MISSING")
else:
    if d.get("objective_spec_complete") is not True: errors.append("DELEGATION_SPEC_INCOMPLETE")
    if d.get("prewave_route_ready_for_promotion_law") is not True: errors.append("DELEGATION_NOT_READY")
    if d.get("weaker_comparator_deletion_authorized_now") is not True: errors.append("COMPARATOR_NOT_DELETABLE")
    if d.get("open_route_gates") != []: errors.append("OPEN_GATES")
if out.get("execution_authority") is not False: errors.append("EXEC_AUTHORITY")
if out.get("promotion_authority") is not False: errors.append("PROMOTION_AUTHORITY")
if out.get("fresh_terminal_evidence_consumed") != 0: errors.append("FRESH_EVIDENCE")
print(json.dumps({"pass":not errors,"errors":errors,"status":out.get("status"),"delegation":d},sort_keys=True))
raise SystemExit(1 if errors else 0)
