set -e
cd /app
cat > /tmp/expert_perm_probe.py <<'PY'
import sys; sys.path.insert(0,'/app')
import itertools, torch
from safetensors.torch import load_file
from reference_model.model import build_model
ROOT='/app'
base=load_file(ROOT+'/output/model.safetensors')
inp=torch.load(ROOT+'/reference_output/input_ids.pt',map_location='cpu',weights_only=True)
ref=torch.load(ROOT+'/reference_output/logits.pt',map_location='cpu',weights_only=True)
def score(state):
 m=build_model(ROOT+'/reference_model/config.json'); m.load_state_dict(state,strict=False); m.eval()
 with torch.no_grad(): y=m(inp)
 return (y-ref).abs().mean().item(), (y-ref).abs().max().item()
best=[]
for perm in itertools.permutations(range(4)):
 s={k:v for k,v in base.items()}
 # copy only experts, keep router fixed
 repl={}
 for L in (1,3,5,7):
  for i,src in enumerate(perm):
   for part in ('gate_proj','up_proj','down_proj'):
    repl[f'layers.{L}.moe.experts.{i}.{part}.weight']=base[f'layers.{L}.moe.experts.{src}.{part}.weight']
 s=dict(s); s.update(repl)
 mean,maxd=score(s); best.append((mean,maxd,perm))
for row in sorted(best)[:10]: print(row)
PY
python3 /tmp/expert_perm_probe.py
