set -e
cd /app
python3 - <<'PY'
import torch
from framework.config import get_default_config
c=get_default_config().checkpoint
for tp in range(4):
  for pp in range(2):
    a=torch.load(f'/app/checkpoints/shard_tp{tp}_pp{pp}_ep0.pt',map_location='cpu',weights_only=False)[c.flat_buffer_key]
    b=torch.load(f'/app/checkpoints/shard_tp{tp}_pp{pp}_ep1.pt',map_location='cpu',weights_only=False)[c.flat_buffer_key]
    eq=(a==b)
    # maximal unequal/equal runs, print only runs >=128 and all transitions around layer-scale regions
    runs=[]; start=0; cur=bool(eq[0])
    for i in range(1,eq.numel()):
      v=bool(eq[i])
      if v!=cur:
        runs.append((start,i,cur))
        start=i; cur=v
    runs.append((start,eq.numel(),cur))
    print('===',tp,pp,'numel',a.numel(),'equal_frac',eq.float().mean().item(),'===')
    for s,e,v in runs:
      if e-s>=128:
        print('EQ' if v else 'DIFF',s,e,'len',e-s)
PY
echo EP_BOUNDARY_SCAN_DONE
