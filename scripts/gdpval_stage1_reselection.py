#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse, unquote
from urllib.request import Request, urlopen

ROWS_API="https://datasets-server.huggingface.co/rows?dataset=openai%2Fgdpval&config=default&split=train"
SAFE_REF_PREFIX="https://huggingface.co/datasets/openai/gdpval/resolve/main/reference_files/"
OUT=Path("verification-output/safe_bundle")

ORIGINAL_EXCLUSIONS={
 "83d10b06-26d1-4636-a32c-23f92c57f30b",
 "b57efde3-26d6-4742-bbff-2b63c43b4baa",
 "8a7b6fca-60cc-4ae3-b649-971753cbf8b9",
 "1752cb53-5983-46b6-92ee-58ac85a11283",
}
ORIGINAL_STAGE1={
 "XLSX":"a079d38f-c529-436a-beca-3e291f9e62a3",
 "PPTX":"be830ca0-b352-4658-a5bd-57139d6780ba",
 "TEXT_CONFIG":"2c249e0f-4a8c-4f8e-b4f4-6508ba29b34f",
}
SPENT_XLSX=[
 "17111c03-aac7-45c2-857d-c06d8223d6ad",
 "bb863dd9-31c2-4f64-911a-ce11f457143b",
]

def fetch_rows():
 rows=[]
 for offset,length in ((0,100),(100,100),(200,20)):
  u=f"{ROWS_API}&offset={offset}&length={length}"
  with urlopen(Request(u,headers={"User-Agent":"brain-gdpval-safe-bundle/1.0"}),timeout=45) as r:
   payload=json.loads(r.read().decode())
  page=payload.get("rows"); assert isinstance(page,list)
  rows.extend(page)
 assert len(rows)==220
 return rows

def exts(files):
 return sorted({PurePosixPath(str(x)).suffix.lower() for x in (files or []) if PurePosixPath(str(x)).suffix})

def meta(row):
 tid=str(row.get("task_id") or "")
 refs=list(row.get("reference_files") or [])
 dels=list(row.get("deliverable_files") or [])
 return {
  "task_id":tid,
  "task_id_sha256":hashlib.sha256(tid.encode()).hexdigest(),
  "sector":row.get("sector"),
  "occupation":row.get("occupation"),
  "reference_file_count":len(refs),
  "deliverable_file_count":len(dels),
  "extensions":exts(dels),
 }

def eligible(row,exclusions,cls):
 tid=str(row.get("task_id") or "")
 if not tid or tid in exclusions:return False
 refs=list(row.get("reference_files") or [])
 dels=list(row.get("deliverable_files") or [])
 if len(refs)>3 or not (1<=len(dels)<=2):return False
 e=set(exts(dels))
 if cls=="XLSX":return ".xlsx" in e
 if cls=="PPTX":return ".pptx" in e
 if cls=="TEXT_CONFIG":return ".txt" in e and (".yaml" in e or ".yml" in e)
 raise ValueError(cls)

def pick(rows,exclusions,cls):
 c=[meta(x["row"]) for x in rows if eligible(x.get("row") or {},exclusions,cls)]
 c.sort(key=lambda x:(x["task_id_sha256"],x["task_id"]))
 return c

def safe_filename(path,index):
 name=PurePosixPath(path).name
 if not name:return f"reference_{index}"
 # URL may have escaped spaces while path list may not.
 return unquote(name).replace("/","_").replace("\\","_")

def download_ref(url,dst):
 if not isinstance(url,str) or not url.startswith(SAFE_REF_PREFIX):
  raise RuntimeError("REFERENCE_URL_OUTSIDE_ALLOWED_OPENAI_GDPVAL_PREFIX")
 p=urlparse(url)
 if p.scheme!="https" or p.netloc!="huggingface.co" or "/datasets/openai/gdpval/resolve/main/reference_files/" not in p.path:
  raise RuntimeError("REFERENCE_URL_HOST_OR_PATH_INVALID")
 with urlopen(Request(url,headers={"User-Agent":"brain-gdpval-safe-bundle/1.0"}),timeout=90) as r:
  data=r.read()
 if not data:raise RuntimeError("EMPTY_REFERENCE_DOWNLOAD")
 dst.write_bytes(data)
 return {"file":dst.name,"size_bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}

def main():
 rows=fetch_rows()

 # Replay original selector without reading prompt/rubric/gold fields.
 orig={}
 for cls in ("XLSX","PPTX","TEXT_CONFIG"):
  c=pick(rows,ORIGINAL_EXCLUSIONS,cls); orig[cls]=c[0]["task_id"] if c else None
 assert orig==ORIGINAL_STAGE1,(orig,ORIGINAL_STAGE1)

 base_exclusions=ORIGINAL_EXCLUSIONS|set(ORIGINAL_STAGE1.values())
 first=pick(rows,base_exclusions,"XLSX")
 assert first and first[0]["task_id"]==SPENT_XLSX[0]
 second=pick(rows,base_exclusions|{SPENT_XLSX[0]},"XLSX")
 assert second and second[0]["task_id"]==SPENT_XLSX[1]

 final_exclusions=base_exclusions|set(SPENT_XLSX)
 third=pick(rows,final_exclusions,"XLSX")
 assert third,"THIRD_XLSX_CLASS_EXHAUSTED"
 selected=third[0]
 tid=selected["task_id"]

 # Only now locate selected row and read allowed post-selection fields.
 selected_row=None
 for item in rows:
  row=item.get("row") or {}
  if str(row.get("task_id") or "")==tid:
   selected_row=row;break
 assert selected_row is not None

 prompt=str(selected_row.get("prompt") or "")
 if not prompt.strip():raise RuntimeError("SELECTED_PROMPT_MISSING")
 ref_paths=list(selected_row.get("reference_files") or [])
 ref_urls=list(selected_row.get("reference_file_urls") or [])
 if len(ref_paths)!=len(ref_urls):raise RuntimeError("REFERENCE_PATH_URL_CARDINALITY_MISMATCH")

 OUT.mkdir(parents=True,exist_ok=True)
 refs_dir=OUT/"references"; refs_dir.mkdir(exist_ok=True)
 downloaded=[]
 for i,(rp,ru) in enumerate(zip(ref_paths,ref_urls),1):
  dst=refs_dir/safe_filename(rp,i)
  if dst.exists():dst=refs_dir/f"{i}_{dst.name}"
  rec=download_ref(ru,dst); rec["declared_path"]=str(rp); downloaded.append(rec)

 task_safe={
  "schema":"PROJECT_BRAIN_GDPVAL_STAGE1_SAFE_TASK_BUNDLE_V1",
  "task_id":tid,
  "task_id_sha256":selected["task_id_sha256"],
  "sector":selected_row.get("sector"),
  "occupation":selected_row.get("occupation"),
  "prompt":prompt,
  "reference_files":[str(x) for x in ref_paths],
  "deliverable_files":[str(x) for x in (selected_row.get("deliverable_files") or [])],
  "selection_precommit_brain_commit":"7be0a54aceb8bb3ee111fdbe3eee72747b48a95c",
  "forbidden_fields_exported":[],
 }
 (OUT/"task.json").write_text(json.dumps(task_safe,indent=2,ensure_ascii=False)+"\n")

 result={
  "schema":"PROJECT_BRAIN_GDPVAL_STAGE1_XLSX_THIRD_REPAIR_VERIFICATION_V1",
  "status":"PASS__THIRD_XLSX_SELECTED__SAFE_PROMPT_AND_REFERENCES_PACKAGED",
  "original_selector_exact_replay":True,
  "first_xlsx_exact_replay":True,
  "second_xlsx_exact_replay":True,
  "candidate_count":len(third),
  "selected":selected,
  "reference_downloads":downloaded,
  "safe_bundle_task_json_sha256":hashlib.sha256((OUT/"task.json").read_bytes()).hexdigest(),
  "prompt_printed_to_log":False,
  "rubric_exported":False,
  "gold_deliverable_exported":False,
  "prior_model_output_exported":False,
  "terminal_authority":False,
  "capability_credit_delta":0,
 }
 Path("verification-output/result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 # Log only non-content summary.
 print(json.dumps({
  "status":result["status"],
  "candidate_count":len(third),
  "selected_task_id":tid,
  "reference_count":len(downloaded),
  "reference_hashes":[x["sha256"] for x in downloaded],
  "safe_bundle_task_json_sha256":result["safe_bundle_task_json_sha256"],
 },sort_keys=True))

if __name__=="__main__":
 main()
