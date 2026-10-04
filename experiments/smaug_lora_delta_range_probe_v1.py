#!/usr/bin/env python3
import json, struct, urllib.request, hashlib
import numpy as np

BASE_REPO="Qwen/Qwen3.8-27B"
BASE_REV="1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
SMAUG_REPO="abacusai/Smaug-Mini"
SMAUG_REV="2750fd9f1e67e004111a53a6d9a39c15fbbd33ef"
SHARD="model-00001-of-00018.safetensors"
PREFERRED=[
 "model.language_model.layers.0.linear_attn.out_proj.weight",
 "model.language_model.layers.0.mlp.down_proj.weight",
 "model.language_model.layers.0.mlp.gate_proj.weight",
 "model.language_model.layers.0.mlp.up_proj.weight",
]
UNCHANGED_PROBE="model.language_model.layers.0.input_layernorm.weight"

def url(repo,rev):
    return f"https://huggingface.co/{repo}/resolve/{rev}/{SHARD}"

def get_range(u,start,end):
    req=urllib.request.Request(u,headers={
      "Range":f"bytes={start}-{end}",
      "User-Agent":"project-brain-smaug-delta-probe/1"
    })
    with urllib.request.urlopen(req,timeout=120) as r:
        data=r.read()
        # Some intermediaries can ignore Range. Fail rather than accidentally
        # download a multi-GB shard.
        if len(data) != end-start+1:
            raise RuntimeError(f"RANGE_NOT_HONORED wanted={end-start+1} got={len(data)}")
        return data

def header(u):
    first=get_range(u,0,7)
    n=struct.unpack("<Q",first)[0]
    if not 0 < n < 50_000_000:
        raise RuntimeError(f"BAD_HEADER_LENGTH {n}")
    raw=get_range(u,8,7+n)
    return n,json.loads(raw.rstrip(b" \t\r\n\0").decode("utf-8"))

def tensor_bytes(u,hdr_len,meta):
    a,b=meta["data_offsets"]
    data0=8+hdr_len
    return get_range(u,data0+a,data0+b-1)

def bf16_to_f32(raw,shape):
    u=np.frombuffer(raw,dtype="<u2")
    bits=(u.astype(np.uint32)<<16)
    return bits.view(np.float32).reshape(shape),u.reshape(shape)

def analyze_matrix(name,bm,sm,bu,su,bh,sh):
    if bm["dtype"]!="BF16" or sm["dtype"]!="BF16":
        return {"name":name,"status":"SKIP_NON_BF16","base_dtype":bm["dtype"],"smaug_dtype":sm["dtype"]}
    if bm["shape"]!=sm["shape"] or len(bm["shape"])!=2:
        return {"name":name,"status":"SKIP_SHAPE_MISMATCH","base_shape":bm["shape"],"smaug_shape":sm["shape"]}
    br=tensor_bytes(bu,bh,bm); sr=tensor_bytes(su,sh,sm)
    B,Bbits=bf16_to_f32(br,bm["shape"]); S,Sbits=bf16_to_f32(sr,sm["shape"])
    D=S-B
    m,n=D.shape
    # Deterministic evenly spread square sketch.  The rank of a submatrix cannot
    # exceed the parent low-rank update rank before BF16 rounding; energy
    # concentration remains a useful falsification/triage diagnostic after it.
    k=min(384,m,n)
    ri=np.linspace(0,m-1,k,dtype=np.int64)
    ci=np.linspace(0,n-1,k,dtype=np.int64)
    sketch=D[np.ix_(ri,ci)].astype(np.float64)
    sv=np.linalg.svd(sketch,compute_uv=False)
    e=sv*sv
    total=float(e.sum())
    def frac(r):
        return float(e[:min(r,len(e))].sum()/total) if total else 1.0
    changed=(Bbits!=Sbits)
    absd=np.abs(D)
    # theoretical factor bytes for BF16 rank-r factors, no exact residual.
    factor_bytes={str(r):int(2*r*(m+n)) for r in (8,16,32,64,128)}
    return {
      "name":name,
      "status":"PASS_DIAGNOSTIC",
      "shape":[int(m),int(n)],
      "tensor_bytes_each":len(br),
      "bitwise_changed_fraction":float(changed.mean()),
      "delta_abs_mean":float(absd.mean()),
      "delta_abs_max":float(absd.max()),
      "base_abs_mean":float(np.abs(B).mean()),
      "sketch_size":k,
      "sketch_top_energy_fraction":{
        "8":frac(8),"16":frac(16),"32":frac(32),"64":frac(64),"128":frac(128)
      },
      "sketch_singular_value_ratio_s128_s1":float(sv[min(127,len(sv)-1)]/sv[0]) if sv[0] else 0.0,
      "bf16_factor_storage_bytes_no_residual":factor_bytes,
      "hard_nonclaim":"ENERGY_CONCENTRATION_IS_NOT_EXACT_PATCH_RECOVERY_OR_BENCHMARK_CAPABILITY_PROOF"
    }

def main():
    bu,su=url(BASE_REPO,BASE_REV),url(SMAUG_REPO,SMAUG_REV)
    bh,bhobj=header(bu); sh,shobj=header(su)
    base={k:v for k,v in bhobj.items() if k!="__metadata__"}
    smaug={k:v for k,v in shobj.items() if k!="__metadata__"}
    common=sorted(set(base)&set(smaug))
    matrices=[]
    for name in PREFERRED:
        if name in base and name in smaug:
            matrices.append(analyze_matrix(name,base[name],smaug[name],bu,su,bh,sh))
    # Compare one nominally non-LoRA scalar/vector parameter as a control.
    control=None
    if UNCHANGED_PROBE in base and UNCHANGED_PROBE in smaug:
        bm,sm=base[UNCHANGED_PROBE],smaug[UNCHANGED_PROBE]
        br=tensor_bytes(bu,bh,bm); sr=tensor_bytes(su,sh,sm)
        control={
          "name":UNCHANGED_PROBE,
          "shape":bm["shape"],
          "bytes":len(br),
          "bitwise_equal":br==sr,
          "base_sha256":hashlib.sha256(br).hexdigest(),
          "smaug_sha256":hashlib.sha256(sr).hexdigest(),
        }
    receipt={
      "schema":"PROJECT_BRAIN_SMAUG_MINI_LORA_DELTA_RANGE_PROBE_V1",
      "status":"PASS_DIAGNOSTIC" if matrices else "FAIL_NO_TARGET_MATRICES",
      "sources":{
        "base":{"repo":BASE_REPO,"revision":BASE_REV,"shard":SHARD},
        "smaug":{"repo":SMAUG_REPO,"revision":SMAUG_REV,"shard":SHARD},
      },
      "method":{
        "whole_shards_downloaded":False,
        "http_range_only":True,
        "shared_tensor_name_count":len(common),
        "benchmark_cases_consumed":0,
        "terminal_cases_consumed":0,
        "incremental_spend_usd":0,
      },
      "control":control,
      "matrices":matrices,
      "decision_rule":{
        "strong_low_rank_signal":"TOP_64_SKETCH_ENERGY_CLOSE_TO_1_ACROSS_MULTIPLE_CHANGED_LINEAR_MATRICES",
        "falsifier":"BROAD_SINGULAR_SPECTRUM_WITHOUT_MEANINGFUL_LOW_RANK_ENERGY_CONCENTRATION",
        "next_if_positive":"DESIGN_TENSORWISE_LOW_RANK_PLUS_EXACT_RESIDUAL_PATCH_AND_MEASURE_TOTAL_PATCH_BYTES",
      },
      "hard_nonclaims":[
        "NO_CLAIM_ORIGINAL_LORA_RANK_IS_KNOWN",
        "NO_CLAIM_SKETCH_RANK_EQUALS_FULL_TENSOR_RANK",
        "NO_CLAIM_EXACT_BF16_RECONSTRUCTION",
        "NO_LIVEBENCH_OR_AUTOMATIONBENCH_CREDIT",
        "NO_ACCEPTANCE_OR_OWNERSHIP_CREDIT"
      ]
    }
    open("smaug_lora_delta_range_probe_v1.json","w").write(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0 if receipt["status"]=="PASS_DIAGNOSTIC" else 1

if __name__=="__main__":
    raise SystemExit(main())
