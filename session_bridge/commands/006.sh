set -e
python3 - <<'PY'
import torch
for tp in (0,1):
 a=torch.load(f'/app/checkpoints/shard_tp{tp}_pp0_ep0.pt',map_location='cpu',weights_only=False)['optimizer.flat_param_buffer']
 b=torch.load(f'/app/checkpoints/shard_tp{tp}_pp0_ep1.pt',map_location='cpu',weights_only=False)['optimizer.flat_param_buffer']
 d=(a!=b)
 idx=d.nonzero().flatten()
 print('PAIR',tp,'N',len(a),'DIFF',len(idx),'FIRST',idx[:30].tolist(),'LAST',idx[-30:].tolist())
 # summarize 4096-element blocks
 for s in range(0,len(a),4096):
  n=int(d[s:s+4096].sum())
  if n: print(s,s+4096,n)
PY
