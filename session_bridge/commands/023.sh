set -e
cd /app
python3 /app/consolidate.py >/tmp/current.log
python3 - <<'PY'
import sys,torch
sys.path[:0]=["/app","/app/reference_model"]
import consolidate as c
target=c.state["embed_tokens.weight"].reshape(-1)[:16].cpu()
print("TARGET",target.tolist())
print("TARGET_STATS",float(c.state["embed_tokens.weight"].min()),float(c.state["embed_tokens.weight"].max()),float(c.state["embed_tokens.weight"].std()))
common=[0,1,2,3,7,10,11,12,13,21,42,69,123,256,512,777,1000,1024,1234,1337,2024,2025,2026,4242,12345,54321,314159]
for seed in common:
    torch.manual_seed(seed)
    x=torch.empty((1000,512))
    torch.nn.init.normal_(x)
    d=(x.reshape(-1)[:16]-target).abs()
    print("SEED",seed,"MAX16",float(d.max()),"MEAN16",float(d.mean()),"HEAD",x.reshape(-1)[:4].tolist())
PY
