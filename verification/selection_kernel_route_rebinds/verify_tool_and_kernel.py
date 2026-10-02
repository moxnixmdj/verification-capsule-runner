import json,subprocess,sys
from pathlib import Path
ROOT=Path("verification/selection_kernel_route_rebinds")
errors=[]
for script,label in [
 ("canonical/runtime/terminal_selection_kernel_guard.py","KERNEL"),
 ("canonical/runtime/tool_discovery_t2_t3_objective_binding_validator.py","TOOL")
]:
 p=subprocess.run([sys.executable,script,"."],cwd=ROOT,text=True,capture_output=True)
 if p.returncode!=0: errors.append(label+":"+p.stdout[-2000:]+p.stderr[-1000:])
print(json.dumps({"pass":not errors,"errors":errors},sort_keys=True))
raise SystemExit(1 if errors else 0)
