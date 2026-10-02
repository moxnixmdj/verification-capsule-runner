import json
from pathlib import Path
R=Path("verification/selection_kernel_route_rebinds")
old=json.loads((R/"delegation_prior_verified.json").read_text())
new=json.loads((R/"delegation_current.json").read_text())
kernel=json.loads((R/"canonical/governance/GLOBAL_TERMINAL_SELECTION_KERNEL_V1.json").read_text())
errors=[]
def norm(x):
    x=json.loads(json.dumps(x))
    eb=x.get("exact_bound_blobs",{})
    eb.pop("population_protocol",None); eb.pop("selection_kernel",None)
    for k in ["selection_semantics","prior_independent_verification","revalidation_reason","independent_verification"]:
        x.pop(k,None)
    x["status"]="NORMALIZED"
    if "route_gates" in x: x["route_gates"]["independent_verification_pass"]=False
    x["prewave_admissible"]=False
    return x
if norm(old)!=norm(new): errors.append("BEHAVIOR_SEMANTICS_CHANGED")
sel=new.get("exact_bound_blobs",{}).get("selection_kernel",{})
if sel.get("path")!="canonical/governance/GLOBAL_TERMINAL_SELECTION_KERNEL_V1.json": errors.append("KERNEL_PATH")
if sel.get("blob_sha")!="669afcde50302e76c1b0a1f6b186aaafa8730515": errors.append("KERNEL_SHA")
if kernel.get("execution_authority") is not False or kernel.get("promotion_authority") is not False: errors.append("KERNEL_AUTHORITY")
print(json.dumps({"pass":not errors,"errors":errors,"prior_blob":"65cf321cb1d08c06a236cd4d818dfdec3eb77c95","current_blob":"a1e441567b132d71713ed55dfc51f01d8de112d1"},sort_keys=True))
raise SystemExit(1 if errors else 0)
