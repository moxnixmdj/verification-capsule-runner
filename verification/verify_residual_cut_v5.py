import json
from pathlib import Path
from minimum_reality_cut import solve

data=json.loads(Path("residual_cut_input_v5.json").read_text())
out=solve(data)
assert out["status"]=="EXACT_MINIMUM",out
assert out["exact_minimum"] is True
assert out["selected_observations"]==[
    "A_M0A_SPECIALIZED_WHITE_BOX_COMPOSED_V1",
    "A_M1A_VERIFIED_DETERMINISTIC_FRONTIER_V1",
    "A_M1B_IDENTIFIABLE_CONTINUOUS_GEOMETRY_AND_TOLERANCE_V2",
],out
assert out["observation_count"]==3,out
assert out["total_cost"]==2.0,out
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
