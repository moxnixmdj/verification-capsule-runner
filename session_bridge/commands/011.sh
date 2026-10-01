set -e
cd /app
python3 - <<'PY'
import torch, sys
sys.path.insert(0,'/app')
from safetensors.torch import load_file
from reference_model.model import build_model
s=load_file('/app/output/model.safetensors')
m=build_model('/app/reference_model/config.json'); m.load_state_dict(s,strict=False); m.eval()
ids=torch.load('/app/reference_output/input_ids.pt',map_location='cpu',weights_only=True)
ref=torch.load('/app/reference_output/logits.pt',map_location='cpu',weights_only=True)
with torch.no_grad(): y=m(ids)
print('input_shape',tuple(ids.shape),'logits_shape',tuple(ref.shape),'ids',ids.tolist())
print('ref_stats',ref.mean().item(),ref.std().item(),ref.abs().max().item())
for pos in range(ref.shape[-2]):
 d=(y[...,pos,:]-ref[...,pos,:]).abs()
 yc=y[...,pos,:].flatten().double(); rc=ref[...,pos,:].flatten().double()
 corr=torch.corrcoef(torch.stack([yc,rc]))[0,1].item()
 print('POS',pos,'mean',d.mean().item(),'max',d.max().item(),'corr',corr)
PY
