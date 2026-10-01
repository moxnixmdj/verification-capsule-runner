set -e
cd /app
python3 - <<'PY'
import torch
p='/app/checkpoints/shard_tp1_pp0_ep0.pt'
b=torch.load(p,map_location='cpu',weights_only=False)['optimizer.flat_param_buffer']
start=1966208
for label,s,e in [
 ('tail_first_2048',start,start+2048),
 ('tail_rest_131072',start+2048,start+133120),
 ('tail_first_131072',start,start+131072),
 ('tail_last_2048',start+131072,start+133120),
]:
 x=b[s:e].float()
 print(label,'n',x.numel(),'mean',x.mean().item(),'std',x.std().item(),'min',x.min().item(),'max',x.max().item(),'head',x[:8].tolist())
PY
