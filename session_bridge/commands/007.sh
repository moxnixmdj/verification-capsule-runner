set -e
cd /app
echo '===== TARGETED DOCS ====='
grep -RniE 'fused_params|transpose_output|permute_rotary|rotary_freq|grouped_gate|shared_expert|router|embedding|vocab' framework --include='*.py' --include='*.md' --include='*.txt' || true
echo '===== PARAM SCALE DIAGNOSTICS ====='
python3 - <<'PY'
import torch, json
from safetensors.torch import load_file
s=load_file('/app/output/model.safetensors')
for k in [
'embed_tokens.weight',
'layers.0.input_layernorm.weight','layers.0.input_layernorm.bias',
'layers.0.self_attn.q_proj.weight','layers.0.self_attn.k_proj.weight','layers.0.self_attn.v_proj.weight','layers.0.self_attn.o_proj.weight',
'layers.0.mlp.gate_proj.weight','layers.0.mlp.up_proj.weight','layers.0.mlp.down_proj.weight',
'layers.1.moe.router.weight','layers.1.moe.expert_bias',
'layers.1.moe.experts.0.gate_proj.weight','layers.1.moe.experts.0.up_proj.weight','layers.1.moe.experts.0.down_proj.weight',
'layers.1.moe.shared_expert.gate_proj.weight','layers.1.moe.shared_expert.down_proj.weight',
'final_layernorm.weight','final_layernorm.bias'
]:
 x=s[k].float()
 print(k,tuple(x.shape),'mean',x.mean().item(),'std',x.std().item(),'min',x.min().item(),'max',x.max().item(),'head',x.flatten()[:6].tolist())
PY
