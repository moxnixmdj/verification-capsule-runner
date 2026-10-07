from __future__ import annotations
import argparse, json, math, struct
from pathlib import Path
import numpy as np
import structural_safeguard_packer as base
from canonical.runtime.h100_unichart_lowbit_packer_v1 import _pack_codes

ITERATIONS=5

def optimized_rows(x: np.ndarray, bits: int):
    if x.ndim!=2 or x.shape[1]<1 or x.shape[1]>base.GROUP_SIZE:
        raise base.PackerError('OPT_MATRIX_SHAPE_INVALID')
    if not np.isfinite(x).all():
        raise base.PackerError('NONFINITE_SOURCE_WEIGHT')
    x=x.astype(np.float32,copy=False)
    qmax=np.float32((1<<bits)-1)
    lo=x.min(axis=1); hi=x.max(axis=1)
    scale=(hi-lo)/qmax
    offset=lo.copy()
    constant=(hi==lo)
    scale[constant]=0.0; offset[constant]=lo[constant]
    for _ in range(ITERATIONS):
        with np.errstate(divide='ignore',invalid='ignore',over='ignore'):
            s16=scale.astype(np.float16).astype(np.float32)
            o16=offset.astype(np.float16).astype(np.float32)
        if not np.isfinite(s16).all() or not np.isfinite(o16).all():
            raise base.PackerError('FP16_METADATA_OVERFLOW')
        safe=np.where(s16>0,s16,1.0).astype(np.float32)
        q=np.rint((x-o16[:,None])/safe[:,None])
        q=np.clip(q,0,int(qmax)).astype(np.float32)
        q[constant]=0
        qmean=q.mean(axis=1); xmean=x.mean(axis=1)
        dq=q-qmean[:,None]; dx=x-xmean[:,None]
        var=np.sum(dq*dq,axis=1,dtype=np.float64)
        cov=np.sum(dq*dx,axis=1,dtype=np.float64)
        new_scale=np.where(var>0,cov/var,0.0).astype(np.float32)
        new_scale=np.maximum(new_scale,0.0)
        new_offset=(xmean-new_scale*qmean).astype(np.float32)
        new_scale[constant]=0.0; new_offset[constant]=lo[constant]
        scale,offset=new_scale,new_offset
    s16=scale.astype(np.float16).astype(np.float32)
    o16=offset.astype(np.float16).astype(np.float32)
    if not np.isfinite(s16).all() or not np.isfinite(o16).all():
        raise base.PackerError('FP16_METADATA_OVERFLOW')
    safe=np.where(s16>0,s16,1.0).astype(np.float32)
    q=np.rint((x-o16[:,None])/safe[:,None])
    q=np.clip(q,0,int(qmax)).astype(np.uint8)
    q[constant]=0
    recon=o16[:,None]+s16[:,None]*q.astype(np.float32)
    err=x.astype(np.float64)-recon.astype(np.float64)
    sse=np.sum(err*err,axis=1)
    return sse,s16,o16,q

def opt_sse_rows(x: np.ndarray,bits:int)->np.ndarray:
    return optimized_rows(x,bits)[0]

def opt_quantize_group(values:list[float],bits:int):
    x=np.asarray(values,dtype=np.float32).reshape(1,-1)
    _,s,o,q=optimized_rows(x,bits)
    meta=struct.pack('<ee',float(s[0]),float(o[0]))
    return meta,_pack_codes(q[0].astype(int).tolist(),bits)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',required=True); ap.add_argument('--output',required=True)
    ap.add_argument('--expected-source-sha256',required=True); ap.add_argument('--ancillary-bytes',type=int,required=True)
    ap.add_argument('--result-json')
    a=ap.parse_args()
    old_sse,old_quant=base._sse_rows,base.quantize_group
    base._sse_rows=opt_sse_rows
    base.quantize_group=opt_quantize_group
    try:
        r=base.build(Path(a.source),Path(a.output),a.expected_source_sha256,a.ancillary_bytes)
    finally:
        base._sse_rows,base.quantize_group=old_sse,old_quant
    r['quantizer']='ITERATIVE_SOURCE_ONLY_AFFINE_MSE_FP16_META_V1'
    r['quantizer_iterations']=ITERATIONS
    r['hard_nonclaims'].append('QUANTIZER_DESIGNED_AFTER_DEVELOPMENT_FAILURES__FRESH_HOLDOUT_REQUIRED')
    if a.result_json: Path(a.result_json).write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps(r,indent=2,sort_keys=True))

if __name__=='__main__':
    main()
