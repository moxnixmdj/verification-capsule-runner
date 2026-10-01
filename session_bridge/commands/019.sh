set -e
cd /app
cat > /tmp/shared_axis_probe.py <<'PY'
import sys; sys.path.insert(0,'/app')
import itertools, torch
from safetensors.torch import load_file
from reference_model.model import build_model
ROOT='/app'; base=load_file(ROOT+'/output/model.safetensors')
inp=torch.load(ROOT+'/reference_output/input_ids.pt',map_location='cpu',weights_only=True)
ref=torch.load(ROOT+'/reference_output/logits.pt',map_location='cpu',weights_only=True)
TP=4; I=256; H=512
dims={'I':I,'G':2,'H':H}
def score(s):
 m=build_model(ROOT+'/reference_model/config.json'); m.load_state_dict(s,strict=False); m.eval()
 with torch.no_grad(): y=m(inp)
 d=(y-ref).abs(); return d[...,0,:].mean().item(),d.mean().item(),d.max().item()
rows=[]
for order in itertools.permutations(('I','G','H')):
 for down_trans in [0,1]:
  s=dict(base); repl={}
  for L in (1,3,5,7):
   gchunks=[]; uchunks=[]; dchunks=[]
   Gfull=base[f'layers.{L}.moe.shared_expert.gate_proj.weight']
   Ufull=base[f'layers.{L}.moe.shared_expert.up_proj.weight']
   Dfull=base[f'layers.{L}.moe.shared_expert.down_proj.weight']
   for tp in range(TP):
    gc=Gfull[tp*I:(tp+1)*I]; uc=Ufull[tp*I:(tp+1)*I]
    raw=torch.stack([gc,uc],dim=1).contiguous().reshape(-1)
    shaped=raw.reshape(*[dims[a] for a in order])
    perm=[order.index(a) for a in ('I','G','H')]
    can=shaped.permute(*perm).contiguous()
    gchunks.append(can[:,0,:]); uchunks.append(can[:,1,:])
    dc=Dfull[:,tp*I:(tp+1)*I]
    rawd=dc.contiguous().reshape(-1)
    if down_trans:
      canD=rawd.reshape(I,H).t().contiguous()
    else:
      canD=rawd.reshape(H,I)
    dchunks.append(canD)
   repl[f'layers.{L}.moe.shared_expert.gate_proj.weight']=torch.cat(gchunks,0)
   repl[f'layers.{L}.moe.shared_expert.up_proj.weight']=torch.cat(uchunks,0)
   repl[f'layers.{L}.moe.shared_expert.down_proj.weight']=torch.cat(dchunks,1)
  s.update(repl); rows.append((score(s),order,down_trans))
for r in sorted(rows): print(r)
PY
python3 /tmp/shared_axis_probe.py
