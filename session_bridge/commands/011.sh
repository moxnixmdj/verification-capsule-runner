set -e
cat >>/app/consolidate.py <<'PY'
expected=json.load(open("/app/reference_output/expected_keys.json"))
if set(state)!=set(expected):
    raise RuntimeError((sorted(set(expected)-set(state)),sorted(set(state)-set(expected))))
state={k:state[k].contiguous() for k in expected}
os.makedirs("/app/output",exist_ok=True)
from safetensors.torch import save_file
save_file(state,"/app/output/model.safetensors")
print("SAVED",len(state),os.path.getsize("/app/output/model.safetensors"))
PY
python3 /app/consolidate.py
