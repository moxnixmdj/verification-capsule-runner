set -e
for f in /app/framework/*.py /app/reference_model/model.py /app/reference_model/config.json /app/reference_output/expected_keys.json; do
  echo "===== $f ====="
  cat "$f"
done
python3 - <<'PY'
import torch,glob,os,json
for p in sorted(glob.glob('/app/checkpoints/*.pt')):
    x=torch.load(p,map_location='cpu',weights_only=False)
    print("SHARD",os.path.basename(p),"TYPE",type(x).__name__)
    if isinstance(x,dict):
        for k,v in x.items():
            if torch.is_tensor(v):
                print(" ",k,tuple(v.shape),str(v.dtype))
            elif isinstance(v,dict):
                print(" ",k,"dict",list(v)[:30])
            else:
                print(" ",k,type(v).__name__,repr(v)[:160])
PY
