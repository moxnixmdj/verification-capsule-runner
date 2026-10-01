set -e
cd /app
for f in framework/config.py framework/parallel.py framework/precision.py framework/kernels.py framework/distributed.py; do
  echo "===== $f ====="
  cat "$f"
done
echo '===== SAMPLE FLAT BUFFER HEAD/TAIL ====='
python3 - <<'PY'
import glob, torch, os
for p in sorted(glob.glob('/app/checkpoints/*.pt'))[:4]:
    b=torch.load(p,map_location='cpu',weights_only=False)['optimizer.flat_param_buffer']
    print(os.path.basename(p),'numel',b.numel(),'head',b[:12].tolist(),'tail',b[-12:].tolist())
PY
echo MP_DIAGNOSTIC_001_DONE
