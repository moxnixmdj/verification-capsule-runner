"""Standalone public verifier packer for UniChart ChartQA H100 candidate.

Public inputs only. Parses a safetensors file, verifies its exact tensor census,
then creates a deterministic mixed-precision packed file:
  encoder.* F32 -> W4 affine group-256
  decoder.* F32 -> W3 affine group-256
  I64 -> lossless raw bytes

No Brain-private runtime is imported.
"""
from __future__ import annotations
import argparse, hashlib, json, math, mmap, struct
from pathlib import Path
import numpy as np

MAGIC=b"H100CQ01"
GROUP=256
EXPECTED_SOURCE_BYTES=809_095_376
EXPECTED_MANIFEST_SHA="8b32480b8f7981f3c8413941e522034f3779bef1187374f2ca836bc29af314c5"
EXPECTED_F32=201_858_168
EXPECTED_I64=200_000
EXPECTED_ENCODER=74_180_728
EXPECTED_DECODER=127_677_440
BUDGET=100_000_000

class PackError(RuntimeError): pass

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()

def parse_header(path:Path):
    if path.stat().st_size!=EXPECTED_SOURCE_BYTES:
        raise PackError(f"SOURCE_SIZE:{path.stat().st_size}")
    with path.open("rb") as f:
        p=f.read(8)
        if len(p)!=8: raise PackError("HEADER_PREFIX")
        n=struct.unpack("<Q",p)[0]
        if not 0<n<16_000_000: raise PackError("HEADER_LENGTH")
        raw=f.read(n)
    hdr=json.loads(raw.decode())
    rows=[]
    cursor=0
    for name,meta in hdr.items():
        if name=="__metadata__": continue
        dtype=meta["dtype"]; shape=meta["shape"]; a,b=meta["data_offsets"]
        numel=math.prod(shape)
        unit={"F32":4,"I64":8}.get(dtype)
        if unit is None: raise PackError(f"DTYPE:{name}:{dtype}")
        if b-a != numel*unit: raise PackError(f"BYTE_MISMATCH:{name}")
        if a!=cursor: raise PackError(f"PAYLOAD_GAP:{name}:{a}!={cursor}")
        cursor=b
        rows.append({"name":name,"dtype":dtype,"shape":shape,"numel":numel,"data_start":a,"data_end":b})
    rows.sort(key=lambda x:x["name"])
    manifest=json.dumps(rows,sort_keys=True,separators=(",",":")).encode()
    msha=hashlib.sha256(manifest).hexdigest()
    f32=sum(x["numel"] for x in rows if x["dtype"]=="F32")
    i64=sum(x["numel"] for x in rows if x["dtype"]=="I64")
    enc=sum(x["numel"] for x in rows if x["dtype"]=="F32" and x["name"].startswith("encoder."))
    dec=sum(x["numel"] for x in rows if x["dtype"]=="F32" and x["name"].startswith("decoder."))
    other=[x["name"] for x in rows if x["dtype"]=="F32" and not (x["name"].startswith("encoder.") or x["name"].startswith("decoder."))]
    if msha!=EXPECTED_MANIFEST_SHA: raise PackError(f"MANIFEST_SHA:{msha}")
    if (f32,i64,enc,dec)!=(EXPECTED_F32,EXPECTED_I64,EXPECTED_ENCODER,EXPECTED_DECODER):
        raise PackError(f"COUNTS:{f32}:{i64}:{enc}:{dec}")
    if other: raise PackError(f"OTHER_FLOAT:{other[:3]}")
    return rows,8+n,msha

def bits_for(row):
    if row["dtype"]=="I64": return None
    return 4 if row["name"].startswith("encoder.") else 3

def code_bytes(bits): return 128 if bits==4 else 96

def pack_codes(q,bits):
    q=np.asarray(q,dtype=np.uint8).reshape(-1,GROUP)
    if bits==4:
        return (q[:,0::2] | (q[:,1::2]<<4)).astype(np.uint8,copy=False)
    x=q.reshape(q.shape[0],32,8).astype(np.uint32)
    w=x[:,:,0]|(x[:,:,1]<<3)|(x[:,:,2]<<6)|(x[:,:,3]<<9)|(x[:,:,4]<<12)|(x[:,:,5]<<15)|(x[:,:,6]<<18)|(x[:,:,7]<<21)
    out=np.empty((q.shape[0],96),dtype=np.uint8)
    out[:,0::3]=(w&255).astype(np.uint8); out[:,1::3]=((w>>8)&255).astype(np.uint8); out[:,2::3]=((w>>16)&255).astype(np.uint8)
    return out

def qblock(block,bits):
    if not np.isfinite(block).all(): raise PackError("NONFINITE")
    levels=(1<<bits)-1
    mn=block.min(axis=1).astype(np.float32); mx=block.max(axis=1).astype(np.float32)
    scale=((mx-mn)/np.float32(levels)).astype(np.float16); off=mn.astype(np.float16)
    varying=mx!=mn
    if np.any(varying & (scale==0)): raise PackError("SCALE_UNDERFLOW")
    if not np.isfinite(scale).all() or not np.isfinite(off).all(): raise PackError("META_NONFINITE")
    sf=scale.astype(np.float32); of=off.astype(np.float32)
    q=np.zeros(block.shape,dtype=np.uint8)
    if np.any(varying):
        q[varying]=np.clip(np.rint((block[varying]-of[varying,None])/sf[varying,None]),0,levels).astype(np.uint8)
    recon=of[:,None]+sf[:,None]*q.astype(np.float32); err=block-recon
    meta=np.empty((block.shape[0],2),dtype="<f2"); meta[:,0]=scale; meta[:,1]=off
    return meta.view(np.uint8).reshape(block.shape[0],4),pack_codes(q,bits),{
        "sse":float(np.sum(err*err,dtype=np.float64)),
        "ss":float(np.sum(block*block,dtype=np.float64)),
        "sae":float(np.sum(np.abs(err),dtype=np.float64)),
        "max":float(np.max(np.abs(err))) if err.size else 0.0,
        "n":int(block.size),
    }

def partial(values,bits):
    values=np.asarray(values,dtype=np.float32)
    levels=(1<<bits)-1; mn=np.float32(values.min()); mx=np.float32(values.max())
    scale=np.float16(0.0 if mx==mn else (mx-mn)/np.float32(levels)); off=np.float16(mn)
    if mx!=mn and scale==0: raise PackError("SCALE_UNDERFLOW")
    sf=np.float32(scale); of=np.float32(off)
    qreal=np.zeros(values.size,dtype=np.uint8)
    if mx!=mn: qreal=np.clip(np.rint((values-of)/sf),0,levels).astype(np.uint8)
    recon=of+sf*qreal.astype(np.float32); err=values-recon
    q=np.zeros((1,GROUP),dtype=np.uint8); q[0,:values.size]=qreal
    meta=np.asarray([scale,off],dtype="<f2").view(np.uint8).tobytes()
    return meta+pack_codes(q,bits).tobytes(),{
        "sse":float(np.sum(err*err,dtype=np.float64)),
        "ss":float(np.sum(values*values,dtype=np.float64)),
        "sae":float(np.sum(np.abs(err),dtype=np.float64)),
        "max":float(np.max(np.abs(err))) if err.size else 0.0,
        "n":int(values.size),
    }

def addstat(a,b):
    for k in ("sse","ss","sae","n"): a[k]+=b[k]
    a["max"]=max(a["max"],b["max"])

def pack(source:Path,out:Path,chunk_groups=4096):
    rows,base,msha=parse_header(source)
    ordered=sorted(rows,key=lambda x:(x["data_start"],x["name"]))
    cursor=0; entries=[]
    for r in ordered:
        bits=bits_for(r); n=r["numel"]
        if bits is None: groups=0; rec=0; length=n*8
        else: groups=math.ceil(n/GROUP) if n else 0; rec=4+code_bytes(bits); length=groups*rec
        entries.append({**r,"bits":bits,"groups":groups,"record_bytes":rec,"packed_start":cursor,"packed_end":cursor+length})
        cursor+=length
    header={"schema":"H100_CHARTQA_PACK_V1","source_manifest_sha256":msha,"payload_bytes":cursor,"tensors":entries,
            "quantization":{"encoder_bits":4,"decoder_bits":3,"group":256,"meta":"F16_SCALE_F16_OFFSET","rounding":"RINT_TIES_EVEN"}}
    hb=json.dumps(header,sort_keys=True,separators=(",",":")).encode()
    stats={k:{"sse":0.0,"ss":0.0,"sae":0.0,"max":0.0,"n":0} for k in ("encoder","decoder")}
    with source.open("rb") as sf,out.open("wb") as fo:
        mm=mmap.mmap(sf.fileno(),0,access=mmap.ACCESS_READ)
        try:
            fo.write(MAGIC); fo.write(struct.pack("<Q",len(hb))); fo.write(hb)
            for r in entries:
                n=r["numel"]; off=base+r["data_start"]; bits=r["bits"]
                if bits is None:
                    fo.write(mm[off:off+n*8]); continue
                part="encoder" if bits==4 else "decoder"; full=n//GROUP; rem=n%GROUP; done=0
                while done<full:
                    g=min(chunk_groups,full-done); start=done*GROUP
                    view=np.frombuffer(mm,dtype="<f4",count=g*GROUP,offset=off+start*4)
                    block=np.array(view,dtype=np.float32,copy=True).reshape(g,GROUP); del view
                    meta,codes,st=qblock(block,bits)
                    recs=np.empty((g,4+code_bytes(bits)),dtype=np.uint8); recs[:,:4]=meta; recs[:,4:]=codes
                    fo.write(recs.tobytes()); addstat(stats[part],st); done+=g
                if rem:
                    view=np.frombuffer(mm,dtype="<f4",count=rem,offset=off+full*GROUP*4)
                    vals=np.array(view,dtype=np.float32,copy=True); del view
                    rec,st=partial(vals,bits); fo.write(rec); addstat(stats[part],st)
        finally: mm.close()
    expected=len(MAGIC)+8+len(hb)+cursor; actual=out.stat().st_size
    if actual!=expected: raise PackError(f"OUTPUT_SIZE:{actual}!={expected}")
    for s in stats.values():
        n=s["n"]; s["rmse"]=math.sqrt(s["sse"]/n); s["mae"]=s["sae"]/n; s["relative_mse"]=s["sse"]/s["ss"] if s["ss"] else 0.0
    return {"status":"PASS__REAL_CHARTQA_W4_W3_PACK_CREATED","source_manifest_sha256":msha,"tensor_count":len(rows),
            "packed_bytes":actual,"packed_sha256":sha256_file(out),"budget":BUDGET,"margin":BUDGET-actual,
            "quant_error":stats,"h100_credit_delta":0}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--source",required=True); ap.add_argument("--output",required=True); ap.add_argument("--receipt",required=True)
    a=ap.parse_args(); r=pack(Path(a.source),Path(a.output)); Path(a.receipt).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n"); print(json.dumps(r,indent=2,sort_keys=True))
if __name__=="__main__": main()
