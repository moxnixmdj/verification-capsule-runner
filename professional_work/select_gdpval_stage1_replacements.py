import hashlib, json
from pathlib import Path
from datasets import load_dataset

EXCLUDE={
 "83d10b06-26d1-4636-a32c-23f92c57f30b",
 "b57efde3-26d6-4742-bbff-2b63c43b4baa",
 "8a7b6fca-60cc-4ae3-b649-971753cbf8b9",
 "1752cb53-5983-46b6-92ee-58ac85a11283",
 "a079d38f-c529-436a-beca-3e291f9e62a3",
 "be830ca0-b352-4658-a5bd-57139d6780ba",
 "2c249e0f-4a8c-4f8e-b4f4-6508ba29b34f",
}
ds=load_dataset("openai/gdpval",split="train")
required={"task_id","sector","occupation","reference_files","deliverable_files"}
missing=required-set(ds.column_names)
if missing: raise RuntimeError(f"missing metadata columns: {sorted(missing)}")

def ext(path):
    p=str(path).lower()
    return "."+p.rsplit(".",1)[-1] if "." in p else ""

def classify(delivs):
    exts=sorted({ext(x) for x in delivs})
    if exts==[".xlsx"]: return "XLSX"
    if exts==[".pptx"]: return "PPTX"
    return None

cands={"XLSX":[],"PPTX":[]}
for row in ds:
    tid=str(row["task_id"])
    if tid in EXCLUDE: continue
    refs=list(row["reference_files"] or [])
    dels=list(row["deliverable_files"] or [])
    cls=classify(dels)
    if cls is None or len(refs)>3 or not (1<=len(dels)<=2): continue
    cands[cls].append({
      "artifact_class":cls,
      "task_id":tid,
      "task_id_sha256":hashlib.sha256(tid.encode()).hexdigest(),
      "sector":row["sector"],
      "occupation":row["occupation"],
      "reference_file_count":len(refs),
      "deliverable_file_count":len(dels),
      "extensions":sorted({ext(x) for x in dels}),
    })

selected=[]
for cls in ("XLSX","PPTX"):
    if not cands[cls]: raise RuntimeError(f"no eligible {cls}")
    selected.append(min(cands[cls],key=lambda x:x["task_id_sha256"]))

out={
 "schema":"PROJECT_BRAIN_GDPVAL_STAGE1_REPLACEMENT_SELECTION_V1",
 "status":"METADATA_ONLY_REPLACEMENTS_FROZEN__PROMPTS_UNREAD",
 "selection_rule":"For each XLSX/PPTX class, among public GDPval tasks not excluded, <=3 references and 1-2 deliverables, choose lexicographically smallest SHA256(task_id).",
 "excluded_task_ids":sorted(EXCLUDE),
 "selected_replacements":selected,
 "capability_credit_delta":0,
}
Path("gdpval_stage1_replacements.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out,indent=2))
