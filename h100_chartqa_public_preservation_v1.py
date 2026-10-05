"""Evaluate FP32 vs exact decoded H100 packed UniChart ChartQA on frozen public cases."""
from __future__ import annotations
import argparse, json, math, struct
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel

import h100_chartqa_safetensors_pack_v1 as packer

def norm_text(x:str)->str:
    return str(x).strip().strip("%").strip()

def to_float(x:str):
    try: return float(norm_text(x).replace(",",""))
    except Exception: return None

def relaxed(target:str,pred:str)->float:
    t=norm_text(target); p=norm_text(pred)
    tf=to_float(t); pf=to_float(p)
    if tf is not None and pf is not None:
        if tf==0.0: return 1.0 if pf==0.0 else 0.0
        return 1.0 if abs(pf-tf)/abs(tf) <= 0.05 else 0.0
    return 1.0 if t.lower()==p.lower() else 0.0

def read_header(path:Path):
    with path.open("rb") as f:
        magic=f.read(len(packer.MAGIC))
        if magic!=packer.MAGIC: raise RuntimeError("PACKED_MAGIC_MISMATCH")
        n=struct.unpack("<Q",f.read(8))[0]
        raw=f.read(n)
    return json.loads(raw.decode()),len(packer.MAGIC)+8+n

def unpack_codes(blob:bytes,bits:int,groups:int)->np.ndarray:
    if bits==4:
        b=np.frombuffer(blob,dtype=np.uint8).reshape(groups,128)
        q=np.empty((groups,packer.GROUP),dtype=np.uint8)
        q[:,0::2]=b&15; q[:,1::2]=(b>>4)&15
        return q
    b=np.frombuffer(blob,dtype=np.uint8).reshape(groups,96)
    lo=b[:,0::3].astype(np.uint32); mi=b[:,1::3].astype(np.uint32); hi=b[:,2::3].astype(np.uint32)
    w=lo|(mi<<8)|(hi<<16)
    q=np.empty((groups,32,8),dtype=np.uint8)
    for i in range(8): q[:,:,i]=((w>>(3*i))&7).astype(np.uint8)
    return q.reshape(groups,packer.GROUP)

def apply_packed(model,packed:Path,chunk_groups:int=2048):
    hdr,base=read_header(packed)
    state=model.state_dict(keep_vars=True)
    seen=0
    with packed.open("rb") as f, torch.no_grad():
        for row in hdr["tensors"]:
            name=row["name"]
            if name not in state: raise RuntimeError(f"MODEL_KEY_MISSING:{name}")
            target=state[name]
            if list(target.shape)!=row["shape"]: raise RuntimeError(f"MODEL_SHAPE_MISMATCH:{name}")
            n=int(row["numel"]); bits=row["bits"]; flat=target.view(-1)
            f.seek(base+int(row["packed_start"]))
            if bits is None:
                raw=f.read(n*8)
                if len(raw)!=n*8: raise RuntimeError(f"RAW_TRUNCATED:{name}")
                arr=np.frombuffer(raw,dtype="<i8").copy()
                flat.copy_(torch.from_numpy(arr).to(dtype=flat.dtype))
                seen+=n; continue
            rec=int(row["record_bytes"]); groups=int(row["groups"]); done=0; written=0
            while done<groups:
                g=min(chunk_groups,groups-done)
                blob=f.read(g*rec)
                if len(blob)!=g*rec: raise RuntimeError(f"QUANT_TRUNCATED:{name}:{done}")
                records=np.frombuffer(blob,dtype=np.uint8).reshape(g,rec)
                meta=records[:,:4].copy().view("<f2").reshape(g,2).astype(np.float32)
                codes=records[:,4:].copy().tobytes()
                q=unpack_codes(codes,int(bits),g).astype(np.float32)
                recon=meta[:,1,None]+meta[:,0,None]*q
                remain=n-written; take=min(remain,g*packer.GROUP)
                values=np.ascontiguousarray(recon.reshape(-1)[:take],dtype=np.float32)
                flat[written:written+take].copy_(torch.from_numpy(values).to(dtype=flat.dtype))
                written+=take; done+=g
            if written!=n: raise RuntimeError(f"WRITE_COUNT_MISMATCH:{name}:{written}!={n}")
            seen+=n
    return {"tensors":len(hdr["tensors"]),"elements_written":seen,"source_manifest_sha256":hdr["source_manifest_sha256"]}

def generate_answer(model,processor,image_path:Path,question:str)->str:
    image=Image.open(image_path).convert("RGB")
    prompt=f"<chartqa> {question} <s_answer>"
    ids=processor.tokenizer(prompt,add_special_tokens=False,return_tensors="pt").input_ids
    pixels=processor(image,return_tensors="pt").pixel_values
    with torch.inference_mode():
        out=model.generate(
            pixels,
            decoder_input_ids=ids,
            max_length=model.decoder.config.max_position_embeddings,
            early_stopping=True,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=4,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
            return_dict_in_generate=True,
        )
    seq=processor.batch_decode(out.sequences)[0]
    seq=seq.replace(processor.tokenizer.eos_token,"").replace(processor.tokenizer.pad_token,"")
    if "<s_answer>" not in seq: return ""
    return seq.split("<s_answer>",1)[1].strip()

def evaluate(model,processor,cases,image_root:Path):
    rows=[]; total=0.0
    for c in cases:
        pred=generate_answer(model,processor,image_root/c["imgname"],c["query"])
        score=relaxed(c["label"],pred); total+=score
        rows.append({"id":c["id"],"gold":c["label"],"prediction":pred,"score":score})
    return rows,total/len(cases)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model-dir",required=True); ap.add_argument("--packed",required=True); ap.add_argument("--cases",required=True); ap.add_argument("--image-root",required=True); ap.add_argument("--receipt",required=True)
    a=ap.parse_args()
    torch.set_num_threads(2)
    cases_doc=json.load(open(a.cases)); cases=cases_doc["cases"]; gate=cases_doc["gate"]
    processor=DonutProcessor.from_pretrained(a.model_dir,local_files_only=True)
    model=VisionEncoderDecoderModel.from_pretrained(a.model_dir,local_files_only=True)
    model.eval()
    fp_rows,fp_acc=evaluate(model,processor,cases,Path(a.image_root))
    load=apply_packed(model,Path(a.packed))
    model.eval()
    q_rows,q_acc=evaluate(model,processor,cases,Path(a.image_root))
    agreement=sum(relaxed(x["prediction"],y["prediction"]) for x,y in zip(fp_rows,q_rows))/len(cases)
    passed=(fp_acc>=gate["min_fp32_accuracy"] and q_acc>=fp_acc-gate["max_absolute_accuracy_drop"] and agreement>=gate["min_fp32_packed_agreement"])
    out={
      "schema":"PROJECT_BRAIN_H100_CHARTQA_PUBLIC_PRESERVATION_RESULT_V1",
      "status":"PASS__PUBLIC_CHARTQA_CAPABILITY_PRESERVED" if passed else "FAIL__PUBLIC_CHARTQA_CAPABILITY_REGRESSION",
      "case_count":len(cases),"fp32_relaxed_accuracy":fp_acc,"packed_relaxed_accuracy":q_acc,"absolute_accuracy_delta":q_acc-fp_acc,"fp32_packed_relaxed_agreement":agreement,
      "gate":gate,"packed_load":load,
      "cases":[{"id":c["id"],"gold":c["label"],"fp32":x["prediction"],"fp32_score":x["score"],"packed":y["prediction"],"packed_score":y["score"],"agreement":relaxed(x["prediction"],y["prediction"])} for c,x,y in zip(cases,fp_rows,q_rows)],
      "hard_nonclaims":["PUBLIC_20_CASE_PRESERVATION_IS_NOT_CHARTOGRAPHY_GE_89","PUBLIC_20_CASE_PRESERVATION_IS_NOT_FULL_H100_TERMINAL_PROOF"],
      "h100_credit_delta":0,"acceptance_credit_delta":0
    }
    Path(a.receipt).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:out[k] for k in ("status","case_count","fp32_relaxed_accuracy","packed_relaxed_accuracy","absolute_accuracy_delta","fp32_packed_relaxed_agreement")},indent=2,sort_keys=True))
    if not passed: raise SystemExit(3)
if __name__=="__main__": main()
