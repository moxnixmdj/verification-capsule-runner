from __future__ import annotations
import json
from canonical.runtime import harbor_science_planner_v1 as p

prompt = (
    "Return one JSON object only. On this synthetic zero-case preflight, "
    "provide material_requirements exactly [\"R1\"] and one candidate action "
    "with action_id A1, covers [\"R1\"], command \"echo synthetic\", "
    "and verify_command \"echo synthetic\". No prose."
)
out=p.plan(prompt,timeout_s=180)
obj=p.normalize_proposal_object(p.extract_json_object(out["text"]))
assert obj.get("material_requirements")==["R1"],obj
c=obj.get("candidates")
assert isinstance(c,list) and c,c
row=c[0]
assert row.get("action_id")=="A1",row
assert row.get("covers")==["R1"],row
assert out["model"]=="brain-qwen3.5-9b",out
assert out["backend"]=="LOCAL_LLAMA_SERVER",out
assert out["endpoint"]=="http://127.0.0.1:8080/v1/chat/completions",out
print(json.dumps({
    "status":"PASS",
    "model":out["model"],
    "backend":out["backend"],
    "endpoint":out["endpoint"],
    "proposal":obj,
},sort_keys=True))
