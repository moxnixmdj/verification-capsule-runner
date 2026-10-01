set -e
python3 /app/consolidate.py >/tmp/current.log
python3 - <<'PY'
import torch,math
exec(open('/app/consolidate.py').read().split('state={}')[0])
v=SH[(0,0,0)]['L0.rotary']
std=1.0/(M.rope_theta**(torch.arange(0,M.head_dim,2).float()/M.head_dim))
perm=Q.rotary_freq_permutation(len(std))
print('stored',v[:16].tolist())
print('std',std[:16].tolist())
print('permstd',std[perm][:16].tolist())
print('err_std',float((v-std).abs().max()))
print('err_perm',float((v-std[perm]).abs().max()))
PY
