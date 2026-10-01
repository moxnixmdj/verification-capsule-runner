set -e
cat >/tmp/grouped_layout_probe.py <<'PY'
import sys,itertools,torch
sys.path.insert(0,"/app"); sys.path.insert(0,"/app/reference_model")
import consolidate as c
from model import build_model

ids=torch.load("/app/reference_output/input_ids.pt",map_location="cpu",weights_only=False)
ref=torch.load("/app/reference_output/logits.pt",map_location="cpu",weights_only=False)
base={k:v.clone() for k,v in c.state.items()}
E=c.M.num_experts//c.P.ep_size
I=c.M.intermediate_size//c.P.tp_size
G=2
H=c.M.hidden_size
dims={"E":E,"I":I,"G":G}

def score(name,w):
    m=build_model("/app/reference_model/config.json")
    m.load_state_dict(w,strict=False)
    m.eval()
    with torch.no_grad():
        y=m(ids)
    d=(y-ref).abs()
    print(name,"MAX",float(d.max()),"MEAN",float(d.mean()),"TOK0",float(d[...,0,:].mean()))

score("BASE",dict(base))
for order in itertools.permutations(("E","I","G")):
    w=dict(base)
    for gl in c.M.moe_layer_indices:
        pp=c.P.get_pp_stage(gl,c.M.num_hidden_layers)
        li=c.P.global_to_local_layer(gl,c.M.num_hidden_layers)
        tag=f"L{li}"
        canonical={}
        for ep in range(c.P.ep_size):
            per_tp=[]
            for tp in range(c.P.tp_size):
                raw=c.SH[(tp,pp,ep)][tag+".grouped_gateup"]
                shaped=raw.reshape(*[dims[a] for a in order],H)
                perm=[order.index(a) for a in ("E","I","G")]+[3]
                per_tp.append(shaped.permute(*perm).contiguous())
            full=torch.cat(per_tp,dim=1)
            for le in range(E):
                ge=c.P.local_expert_to_global(ep,le,c.M.num_experts)
                canonical[ge]=full[le]
        for ge,x in canonical.items():
            w[f"layers.{gl}.moe.experts.{ge}.gate_proj.weight"]=x[:,0,:].contiguous()
            w[f"layers.{gl}.moe.experts.{ge}.up_proj.weight"]=x[:,1,:].contiguous()
    score("ORDER_"+"".join(order),w)
PY
python3 /tmp/grouped_layout_probe.py
