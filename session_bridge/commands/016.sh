set -e
cd /app
cat > /tmp/layer_map_probe.py <<'PY'
import sys; sys.path.insert(0,'/app')
import torch
from safetensors.torch import load_file
from reference_model.model import build_model
ROOT='/app'; base=load_file(ROOT+'/output/model.safetensors')
inp=torch.load(ROOT+'/reference_output/input_ids.pt',map_location='cpu',weights_only=True)
ref=torch.load(ROOT+'/reference_output/logits.pt',map_location='cpu',weights_only=True)
def score(s):
 m=build_model(ROOT+'/reference_model/config.json'); m.load_state_dict(s,strict=False); m.eval()
 with torch.no_grad(): y=m(inp)
 d=(y-ref).abs(); return d[...,0,:].mean().item(),d.mean().item(),d.max().item()
def remap(mapping):
 s={k:v for k,v in base.items() if not k.startswith('layers.')}
 for dst,src in enumerate(mapping):
  pre=f'layers.{src}.'; outpre=f'layers.{dst}.'
  for k,v in base.items():
   if k.startswith(pre): s[outpre+k[len(pre):]]=v
 return s
maps={
 'current':[0,1,2,3,4,5,6,7],
 'contiguous_pp':[0,1,4,5,2,3,6,7],
 'reverse_virtual_chunks':[4,5,6,7,0,1,2,3],
 'reverse_within_stage_chunks':[4,5,2,3,0,1,6,7],
}
for name,m in maps.items(): print(name,m,score(remap(m)))
print('TRAINING_PROFILE_CHECK')
import os
from framework.config import get_default_config
c=get_default_config()
print('env',os.environ.get('TRAINING_PROFILE'),'virtual_pp_size',c.parallel.virtual_pp_size)
PY
python3 /tmp/layer_map_probe.py
