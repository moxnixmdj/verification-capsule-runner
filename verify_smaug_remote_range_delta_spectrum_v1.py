#!/usr/bin/env python3
"""Remote-range reverse-LoRA spectrum probe for Smaug-Mini vs Qwen3.8-27B.

Reads pinned index JSON, Safetensors headers, and bounded row ranges from a few
language-trunk matrices. It never downloads a whole shard. The purpose is to
measure whether the merged finetune delta has a sharply low-rank spectrum before
spending tens of GB on full-checkpoint extraction.
"""
from __future__ import annotations
import hashlib, json, math, os, re, struct
from pathlib import Path
from typing import Any

import numpy as np
import requests

BASE_REPO="Qwen/Qwen3.8-27B"
BASE_REV="1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
FT_REPO="abacusai/Smaug-Mini"
FT_REV="2750fd9f1e67e004111a53a6d9a39c15fbbd33ef"
ROW_SAMPLE=128
MAX_TENSORS=7
MAX_WEIGHT_BYTES=96_000_000
TIMEOUT=120

def url(repo:str, rev:str, path:str)->str:
    return f"https://huggingface.co/{repo}/resolve/{rev}/{path}?download=true"

def get_json(u:str)->dict[str,Any]:
    r=requests.get(u,timeout=TIMEOUT,headers={"User-Agent":"project-brain-range-probe/1"})
    r.raise_for_status()
    return r.json()

def ranged(u:str,start:int,end:int)->bytes:
    if end < start: raise ValueError("bad range")
    r=requests.get(
        u, headers={"Range":f"bytes={start}-{end}","User-Agent":"project-brain-range-probe/1"},
        timeout=TIMEOUT, stream=True, allow_redirects=True,
    )
    # Fail closed instead of accidentally downloading a multi-GB shard.
    if r.status_code != 206:
        r.close()
        raise RuntimeError(f"RANGE_NOT_HONORED:{r.status_code}:{u}")
    cr=r.headers.get("Content-Range","")
    if not cr.startswith(f"bytes {start}-{end}/"):
        r.close()
        raise RuntimeError(f"CONTENT_RANGE_MISMATCH:{cr}")
    out=r.content
    if len(out)!=(end-start+1):
        raise RuntimeError(f"RANGE_LENGTH_MISMATCH:{len(out)}")
    return out

def header(repo:str,rev:str,shard:str)->tuple[int,dict[str,Any]]:
    u=url(repo,rev,shard)
    n=struct.unpack("<Q",ranged(u,0,7))[0]
    if n<=0 or n>16_000_000:
        raise RuntimeError(f"UNREASONABLE_HEADER:{shard}:{n}")
    raw=ranged(u,8,7+n)
    return n,json.loads(raw.decode("utf-8").rstrip())

def layer_of(name:str)->int:
    m=re.search(r"\.layers\.(\d+)\.",name)
    return int(m.group(1)) if m else -1

def module_type(name:str)->str|None:
    marks=("q_proj","k_proj","v_proj","o_proj","down_proj","up_proj","gate_proj",
           "in_proj_qkvz","out_proj")
    return next((m for m in marks if f".{m}.weight" in name),None)

def choose(weight_map:dict[str,str])->list[str]:
    groups:dict[str,list[str]]={}
    for name in weight_map:
        if "model.language_model.layers." not in name: continue
        typ=module_type(name)
        if typ: groups.setdefault(typ,[]).append(name)
    chosen=[]
    priority=("q_proj","o_proj","down_proj","up_proj","gate_proj","in_proj_qkvz","out_proj")
    for typ in priority:
        xs=sorted(groups.get(typ,[]),key=lambda n:(layer_of(n),n))
        if xs:
            chosen.append(xs[len(xs)//2])
        if len(chosen)>=MAX_TENSORS: break
    if not chosen:
        raise RuntimeError("NO_LANGUAGE_MATRIX_CANDIDATES")
    return chosen

def decode(raw:bytes,dtype:str,shape:tuple[int,int])->np.ndarray:
    if dtype=="BF16":
        u=np.frombuffer(raw,dtype="<u2").astype(np.uint32)
        return (u<<16).view(np.float32).reshape(shape)
    if dtype=="F16":
        return np.frombuffer(raw,dtype="<f2").astype(np.float32).reshape(shape)
    if dtype=="F32":
        return np.frombuffer(raw,dtype="<f4").astype(np.float32).reshape(shape)
    raise RuntimeError(f"UNSUPPORTED_DTYPE:{dtype}")

def item_bytes(dtype:str)->int:
    return {"BF16":2,"F16":2,"F32":4}.get(dtype,0)

def read_rows(repo:str,rev:str,shard:str,hdr_n:int,meta:dict[str,Any],row0:int,rows:int)->bytes:
    shape=meta["shape"]; dtype=meta["dtype"]; b=item_bytes(dtype)
    if len(shape)!=2 or b==0: raise RuntimeError("UNSUPPORTED_MATRIX")
    cols=int(shape[1])
    rel0=int(meta["data_offsets"][0])
    data0=8+hdr_n+rel0
    start=data0+row0*cols*b
    end=start+rows*cols*b-1
    return ranged(url(repo,rev,shard),start,end)

def energy_rank(s:np.ndarray,p:float)->int:
    e=np.square(s.astype(np.float64)); total=float(e.sum())
    if total==0: return 0
    return int(np.searchsorted(np.cumsum(e),p*total)+1)

def main():
    base_idx=get_json(url(BASE_REPO,BASE_REV,"model.safetensors.index.json"))
    ft_idx=get_json(url(FT_REPO,FT_REV,"model.safetensors.index.json"))
    bw=base_idx["weight_map"]; fw=ft_idx["weight_map"]
    if set(bw)!=set(fw):
        raise RuntimeError(f"WEIGHT_NAME_SET_MISMATCH:{len(set(bw)^set(fw))}")
    selected=choose(bw)
    cache={}
    rows_out=[]; weight_bytes=0
    for name in selected:
        bs,bfs=bw[name],fw[name]
        key=("b",bs)
        if key not in cache: cache[key]=header(BASE_REPO,BASE_REV,bs)
        key2=("f",bfs)
        if key2 not in cache: cache[key2]=header(FT_REPO,FT_REV,bfs)
        bhn,bh=cache[key]; fhn,fh=cache[key2]
        if name not in bh or name not in fh: raise RuntimeError(f"TENSOR_HEADER_MISSING:{name}")
        bm,fm=bh[name],fh[name]
        if bm["shape"]!=fm["shape"] or bm["dtype"]!=fm["dtype"]:
            raise RuntimeError(f"TENSOR_ABI_MISMATCH:{name}")
        shape=tuple(map(int,bm["shape"]))
        if len(shape)!=2: continue
        rows=min(ROW_SAMPLE,shape[0])
        row0=max(0,(shape[0]-rows)//2)
        br=read_rows(BASE_REPO,BASE_REV,bs,bhn,bm,row0,rows)
        fr=read_rows(FT_REPO,FT_REV,bfs,fhn,fm,row0,rows)
        weight_bytes+=len(br)+len(fr)
        if weight_bytes>MAX_WEIGHT_BYTES:
            raise RuntimeError(f"WEIGHT_RANGE_BUDGET_EXCEEDED:{weight_bytes}")
        b=decode(br,bm["dtype"],(rows,shape[1]))
        f=decode(fr,fm["dtype"],(rows,shape[1]))
        d=f-b
        dn=float(np.linalg.norm(d))
        bn=float(np.linalg.norm(b))
        if dn==0:
            s=np.zeros(1,dtype=np.float32)
        else:
            s=np.linalg.svd(d,full_matrices=False,compute_uv=False)
        row={
            "tensor":name,"module_type":module_type(name),"layer":layer_of(name),
            "shape":list(shape),"dtype":bm["dtype"],"base_shard":bs,"finetune_shard":bfs,
            "sample_row_start":row0,"sample_row_count":rows,
            "sample_payload_bytes_pair":len(br)+len(fr),
            "delta_fro_norm":dn,"base_fro_norm":bn,
            "relative_delta_fro":(dn/bn if bn else None),
            "sample_exactly_identical":bool(np.array_equal(b,f)),
            "rank_energy_90":energy_rank(s,0.90),
            "rank_energy_95":energy_rank(s,0.95),
            "rank_energy_99":energy_rank(s,0.99),
            "rank_energy_999":energy_rank(s,0.999),
            "top_singular_values":[float(x) for x in s[:12]],
        }
        rows_out.append(row)
    nonzero=[r for r in rows_out if not r["sample_exactly_identical"]]
    receipt={
      "schema":"PROJECT_BRAIN_SMAUG_MINI_REMOTE_RANGE_DELTA_SPECTRUM_V1",
      "status":"PASS__BOUNDED_REMOTE_RANGE_DELTA_SPECTRUM_MEASURED",
      "base":{"repo":BASE_REPO,"revision":BASE_REV},
      "finetune":{"repo":FT_REPO,"revision":FT_REV},
      "method":{
        "safetensors_header_only_then_tensor_row_ranges":True,
        "whole_shard_downloads":0,
        "sample_rows_per_tensor_max":ROW_SAMPLE,
        "sampled_tensor_count":len(rows_out),
        "weight_payload_bytes_downloaded":weight_bytes,
        "weight_payload_budget_bytes":MAX_WEIGHT_BYTES,
      },
      "results":rows_out,
      "summary":{
        "nonzero_sample_count":len(nonzero),
        "max_rank99_across_nonzero_samples":max((r["rank_energy_99"] for r in nonzero),default=0),
        "median_rank99_across_nonzero_samples":(
          float(np.median([r["rank_energy_99"] for r in nonzero])) if nonzero else 0.0
        ),
        "low_rank_signal_candidate":bool(nonzero and max(r["rank_energy_99"] for r in nonzero)<=64),
      },
      "hard_nonclaims":[
        "ROW_BLOCK_SPECTRA_DO_NOT_PROVE_GLOBAL_MATRIX_RANK",
        "BF16_MERGE_ROUNDING_CAN_CREATE_FULL_NUMERICAL_RANK",
        "LOW_RANK_SIGNAL_DOES_NOT_PROVE_A_RECOVERED_ADAPTER_PRESERVES_CAPABILITY",
        "NO_LIVEBENCH_AUTOMATIONBENCH_ACCEPTANCE_OR_OWNERSHIP_CREDIT",
        "NO_TERMINAL_CASE_CONTENT_READ",
      ],
    }
    Path("smaug_remote_range_delta_spectrum_v1.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
