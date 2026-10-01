set -e
cd /app
echo '===== TOP LEVEL ====='
find . -maxdepth 2 -type f -printf '%p %s bytes\n' | sort | head -300
echo '===== REFERENCE MODEL ====='
sed -n '1,500p' reference_model/model.py
echo '===== CONFIG ====='
cat reference_model/config.json
echo '===== EXPECTED KEYS ====='
cat reference_output/expected_keys.json
echo '===== FRAMEWORK FILES ====='
find framework -maxdepth 4 -type f -printf '%p %s bytes\n' | sort
echo '===== FRAMEWORK PARALLELISM / SPLITTING SOURCES ====='
grep -RniE 'tensor.parallel|pipeline.parallel|expert.parallel|split|shard|partition|expert|column|row' framework --include='*.py' --include='*.md' --include='*.txt' | head -500 || true
echo '===== SHARD METADATA ====='
python3 - <<'PY'
import glob, os, torch
for p in sorted(glob.glob('/app/checkpoints/*')):
    print('FILE',os.path.basename(p),os.path.getsize(p))
    obj=torch.load(p,map_location='cpu',weights_only=False)
    print('TYPE',type(obj))
    if isinstance(obj,dict):
        print('TOPKEYS',list(obj)[:50])
        sd=obj.get('state_dict',obj.get('model',obj))
        if isinstance(sd,dict):
            for k,v in sd.items():
                if hasattr(v,'shape'):
                    print(k,tuple(v.shape),getattr(v,'dtype',None))
                else:
                    print(k,type(v).__name__)
    print('---')
PY
echo MP_DIAGNOSTIC_000_DONE
