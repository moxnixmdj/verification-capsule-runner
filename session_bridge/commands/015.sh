set -e
cd /app
cat > /tmp/grouped_axis4_probe.py <<'PY'
import sys; sys.path.insert(0,'/app')
import itertools, torch
from safetensors.torch import load_file
from reference_model.model import build_model
ROOT='/app'; base=load_file(ROOT+'/output/model.safetensors')
inp=torch.load(ROOT+'/reference_output/input_ids.pt',map_location='cpu',weights_only=True)
ref=torch.load(ROOT+'/reference_output/logits.pt',map_location='cpu',weights_only=True)
TP=4; localI=256; pairs={0:[0,2],1:[1,3]}
dims={'E':2,'I':localI,'G':2,'H':512}
def score(s):
 m=build_model(ROOT+'/reference_model/config.json'); m.load_state_dict(s,strict=False); m.eval()
 with torch.no_grad(): y=m(inp)
 d=(y-ref).abs(); return d[...,0,:].mean().item(),d.mean().item(),d.max().item()
rows=[]
for order in itertools.permutations(('E','I','G','H')):
 s=dict(base); repl={}
 for L in (1,3,5,7):
  chunks={e:{'gate':[],'up':[]} for e in range(4)}
  for ep,gids in pairs.items():
   for tp in range(TP):
    canonical=[]
    for gid in gids:
     gate=base[f'layers.{L}.moe.experts.{gid}.gate_proj.weight'][tp*localI:(tp+1)*localI]
     up=base[f'layers.{L}.moe.experts.{gid}.up_proj.weight'][tp*localI:(tp+1)*localI]
     canonical.append(torch.stack([gate,up],dim=1)) # [I,G,H]
    raw=torch.stack(canonical,dim=0).contiguous().reshape(-1) # exact raw under current E,I,G,H read
    shaped=raw.reshape(*[dims[a] for a in order])
    perm=[order.index(a) for a in ('E','I','G','H')]
    can=shaped.permute(*perm).contiguous()
    for le,gid in enumerate(gids):
     chunks[gid]['gate'].append(can[le,:,0,:])
     chunks[gid]['up'].append(can[le,:,1,:])
  for gid in range(4):
   repl[f'layers.{L}.moe.experts.{gid}.gate_proj.weight']=torch.cat(chunks[gid]['gate'],0)
   repl[f'layers.{L}.moe.experts.{gid}.up_proj.weight']=torch.cat(chunks[gid]['up'],0)
 s.update(repl); rows.append((score(s),order))
for r in sorted(rows)[:12]: print(r)
PY
python3 /tmp/grouped_axis4_probe.py
