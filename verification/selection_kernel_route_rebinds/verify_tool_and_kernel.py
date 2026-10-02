import json,os,subprocess,sys
from pathlib import Path
ROOT=Path("verification/selection_kernel_route_rebinds").resolve()
errors=[]
env=dict(os.environ); env["PYTHONPATH"]=str(ROOT)
for module,label in [
 ("canonical.runtime.terminal_selection_kernel_guard","KERNEL"),
 ("canonical.runtime.tool_discovery_t2_t3_objective_binding_validator","TOOL")
]:
 p=subprocess.run([sys.executable,"-m",module,"."],cwd=ROOT,text=True,capture_output=True,env=env)
 if p.returncode!=0: errors.append(label+":"+p.stdout[-2000:]+p.stderr[-1000:])
print(json.dumps({"pass":not errors,"errors":errors},sort_keys=True))
raise SystemExit(1 if errors else 0)
