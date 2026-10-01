set -e
cd /app
cat > /tmp/moe_pair_probe.py <<'PY'
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
 d=(y-ref).abs()
 return d[...,0,:].mean().item(),d.mean().item(),d.max().item()

pairs=((0,2),(1,3))
rows=[]
for swap_gu0,swap_gu1,swap_d0,swap_d1 in itertools.product([0,1],repeat=4):
 s=dict(base)
 for L in (1,3,5,7):
  for pi,(a,b) in enumerate(pairs):
   if (swap_gu0,swap_gu1)[pi]:
    for part in ('gate_proj','up_proj'):
     ka=f'layers.{L}.moe.experts.{a}.{part}.weight'; kb=f'layers.{L}.moe.experts.{b}.{part}.weight'
     s[ka],s[kb]=base[kb],base[ka]
   if (swap_d0,swap_d1)[pi]:
    part='down_proj'
    ka=f'layers.{L}.moe.experts.{a}.{part}.weight'; kb=f'layers.{L}.moe.experts.{b}.{part}.weight'
    s[ka],s[kb]=base[kb],base[ka]
 rows.append((score(s),(swap_gu0,swap_gu1,swap_d0,swap_d1)))
for r in sorted(rows)[:16]: print(r)
PY
python3 /tmp/moe_pair_probe.py
