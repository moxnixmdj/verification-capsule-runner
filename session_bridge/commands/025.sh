set -e
cd /app
python3 - <<'PY'
import torch,time
target=torch.tensor([1.7902404069900513,-2.406756639480591,-0.08145789802074432,0.38213399052619934],dtype=torch.float32)
x=torch.empty(16)
start=time.time()
hits=[]
for seed in range(1_000_000):
    torch.manual_seed(seed)
    torch.nn.init.normal_(x)
    if torch.equal(x[:4],target):
        hits.append(seed)
        print("EXACT_SEED",seed)
        break
    if seed and seed%100000==0:
        print("PROGRESS",seed,"SEC",round(time.time()-start,3))
print("DONE","HITS",hits,"SEC",round(time.time()-start,3))
PY
