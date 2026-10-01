set -e
python3 - <<'PY'
import torch
for tp in (0,1):
 a=torch.load(f'/app/checkpoints/shard_tp{tp}_pp0_ep0.pt',map_location='cpu',weights_only=False)['optimizer.flat_param_buffer']
 b=torch.load(f'/app/checkpoints/shard_tp{tp}_pp0_ep1.pt',map_location='cpu',weights_only=False)['optimizer.flat_param_buffer']
 d=(a!=b).to(torch.int8)
 change=(d[1:]!=d[:-1]).nonzero().flatten().tolist()
 pts=[0]+[x+1 for x in change]+[len(d)]
 print('PAIR',tp)
 for s,e in zip(pts,pts[1:]):
  if e-s>=100:
   print('DIFF' if d[s] else 'SAME',s,e,e-s)
PY
