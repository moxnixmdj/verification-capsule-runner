set -e
cd /app
python3 - <<'PY'
import torch
seed=42
sizes=[1,2,4,8,16,32,64,128,256,512,1024,2048,4096,8192,16384,65536,512000]
for n in sizes:
    torch.manual_seed(seed)
    x=torch.empty(n)
    torch.nn.init.normal_(x)
    print(n,x[:4].tolist())
PY
