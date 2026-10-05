import json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import h100_chartqa_safetensors_pack_v1 as p

def synth(path):
    parts=[
      ("encoder.w","F32",[300],np.linspace(-1,1,300,dtype="<f4").tobytes()),
      ("decoder.w","F32",[257],np.linspace(-.5,.9,257,dtype="<f4").tobytes()),
      ("encoder.ids","I64",[3],np.asarray([1,2,3],dtype="<i8").tobytes()),
    ]
    h={"__metadata__":{"format":"pt"}}; c=0
    for n,d,s,b in parts: h[n]={"dtype":d,"shape":s,"data_offsets":[c,c+len(b)]}; c+=len(b)
    raw=json.dumps(h,separators=(",",":")).encode(); path.write_bytes(struct.pack("<Q",len(raw))+raw+b"".join(x[3] for x in parts))
    rows=[]; c=0
    for n,d,s,b in parts: rows.append({"name":n,"dtype":d,"shape":s,"numel":int(np.prod(s)),"data_start":c,"data_end":c+len(b),"payload_bytes":len(b)}); c+=len(b)
    rows.sort(key=lambda x:x["name"])
    import hashlib
    m=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return path.stat().st_size,m

class T(unittest.TestCase):
  def test_pack_real_file(self):
    with tempfile.TemporaryDirectory() as td:
      td=Path(td); src=td/"x.safe"; size,m=synth(src); out=td/"x.pack"
      with patch.object(p,"EXPECTED_SOURCE_BYTES",size),patch.object(p,"EXPECTED_MANIFEST_SHA",m),patch.object(p,"EXPECTED_F32",557),patch.object(p,"EXPECTED_I64",3),patch.object(p,"EXPECTED_ENCODER",300),patch.object(p,"EXPECTED_DECODER",257):
        r=p.pack(src,out,chunk_groups=1)
      self.assertTrue(out.exists()); self.assertEqual(r["status"],"PASS__REAL_CHARTQA_W4_W3_PACK_CREATED"); self.assertEqual(len(r["packed_sha256"]),64)
  def test_unclassified_float_fails(self):
    with tempfile.TemporaryDirectory() as td:
      td=Path(td)
      a=np.ones(1,dtype="<f4").tobytes(); h={"x":{"dtype":"F32","shape":[1],"data_offsets":[0,4]}}
      raw=json.dumps(h,separators=(",",":")).encode(); src=td/"x"; src.write_bytes(struct.pack("<Q",len(raw))+raw+a)
      import hashlib
      rows=[{"name":"x","dtype":"F32","shape":[1],"numel":1,"data_start":0,"data_end":4,"payload_bytes":4}]
      m=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
      with patch.object(p,"EXPECTED_SOURCE_BYTES",src.stat().st_size),patch.object(p,"EXPECTED_MANIFEST_SHA",m),patch.object(p,"EXPECTED_F32",1),patch.object(p,"EXPECTED_I64",0),patch.object(p,"EXPECTED_ENCODER",0),patch.object(p,"EXPECTED_DECODER",0):
        with self.assertRaises(p.PackError): p.parse_header(src)

if __name__=="__main__": unittest.main(verbosity=2)
