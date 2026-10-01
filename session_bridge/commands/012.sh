set -e
python3 - <<'PY'
import sys,torch
sys.path.insert(0,"/app/reference_model")
from model import build_model
from safetensors.torch import load_file
w=load_file("/app/output/model.safetensors")
m=build_model("/app/reference_model/config.json")
missing,unexpected=m.load_state_dict(w,strict=False)
ids=torch.load("/app/reference_output/input_ids.pt",map_location="cpu",weights_only=False)
ref=torch.load("/app/reference_output/logits.pt",map_location="cpu",weights_only=False)
m.eval()
with torch.no_grad(): got=m(ids)
d=(got-ref).abs()
print("MISSING",missing)
print("UNEXPECTED",unexpected)
print("MAX_ABS",float(d.max()))
print("MEAN_ABS",float(d.mean()))
print("ALLCLOSE",bool(torch.allclose(got,ref,atol=1e-6,rtol=1e-6)))
PY
