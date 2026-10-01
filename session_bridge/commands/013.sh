set -e
cd /app
python3 - <<'PY'
import sys; sys.path.insert(0,'/app')
import torch
from safetensors.torch import load_file
from reference_model.model import build_model
s=load_file('/app/output/model.safetensors')
E=s['embed_tokens.weight'].double()
ref=torch.load('/app/reference_output/logits.pt',map_location='cpu',weights_only=True).squeeze(0).double()
ids=torch.load('/app/reference_output/input_ids.pt',map_location='cpu',weights_only=True)
sol=torch.linalg.lstsq(E, ref.T).solution  # [512,32]
recon=(E@sol).T
res=(recon-ref).abs()
print('EMBED_LSTSQ_REF_RES mean',res.mean().item(),'max',res.max().item(),'refnorm',ref.norm().item(),'resnorm', (recon-ref).norm().item())
m=build_model('/app/reference_model/config.json'); m.load_state_dict(s,strict=False); m.eval()
with torch.no_grad():
 x=m.embed_tokens(ids)
 for layer in m.layers: x=layer(x)
 hn=m.final_layernorm(x).squeeze(0).double()
target=sol.T
d=(hn-target).abs()
print('TARGET_HIDDEN_NORM_STATS',target.mean().item(),target.std().item())
print('CANDIDATE_HIDDEN_DIFF mean',d.mean().item(),'max',d.max().item(),'corr',torch.corrcoef(torch.stack([hn.flatten(),target.flatten()]))[0,1].item())
# Sanity: target hidden should be LayerNorm-normalized if E is exact
print('TARGET_PER_TOKEN_MEAN_MAX',target.mean(-1).abs().max().item())
print('TARGET_PER_TOKEN_STD_RANGE',target.std(-1,unbiased=False).min().item(),target.std(-1,unbiased=False).max().item())
PY
