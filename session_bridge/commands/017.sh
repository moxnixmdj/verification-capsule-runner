set -e
cd /app
cat > /tmp/attn_transpose_probe.py <<'PY'
import sys; sys.path.insert(0,'/app')
import itertools, torch
from safetensors.torch import load_file
from reference_model.model import build_model
ROOT='/app'; base=load_file(ROOT+'/output/model.safetensors')
inp=torch.load(ROOT+'/reference_output/input_ids.pt',map_location='cpu',weights_only=True)
ref=torch.load(ROOT+'/reference_output/logits.pt',map_location='cpu',weights_only=True)
def score(s):
 m=build_model(ROOT+'/reference_model/config.json'); m.load_state_dict(s,strict=False); m.eval()
 with torch.no_grad(): y=m(inp)
 d=(y-ref).abs(); return d[...,0,:].mean().item(),d.mean().item(),d.max().item()
parts=('q_proj','k_proj','v_proj','o_proj')
rows=[]
for bits in itertools.product([0,1],repeat=4):
 s=dict(base)
 for L in range(8):
  for bit,part in zip(bits,parts):
   if bit:
    k=f'layers.{L}.self_attn.{part}.weight'
    s[k]=base[k].t().contiguous()
 rows.append((score(s),bits))
for r in sorted(rows): print(r)
PY
python3 /tmp/attn_transpose_probe.py
