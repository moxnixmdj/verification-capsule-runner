from pathlib import Path
import json, subprocess, sys, os, math

base=Path("/tmp/rank21")
base.mkdir(exist_ok=True)
files={
"measurement data.xls":"https://raw.githubusercontent.com/harbor-framework/terminal-bench/452bf305c6daa62fc59061d22133a7cbc7c1572e/tasks/foodstuff-beta-activity/environment/data/measurement%20data.xls",
"sample.xls":"https://raw.githubusercontent.com/harbor-framework/terminal-bench/452bf305c6daa62fc59061d22133a7cbc7c1572e/tasks/foodstuff-beta-activity/environment/data/sample.xls",
"Sr-90_tables.pdf":"https://raw.githubusercontent.com/harbor-framework/terminal-bench/452bf305c6daa62fc59061d22133a7cbc7c1572e/tasks/foodstuff-beta-activity/environment/data/Sr-90_tables.pdf",
}
for name,url in files.items():
    subprocess.run(["curl","-LfsS",url,"-o",str(base/name)],check=True)

import xlrd
from pypdf import PdfReader

out={"schema":"RANK21_STAGE_B_ALLOWLISTED_INPUT_EXTRACTION_V1","files":{}}
for name in ("measurement data.xls","sample.xls"):
    wb=xlrd.open_workbook(base/name)
    sheets=[]
    for sh in wb.sheets():
        rows=[]
        for r in range(sh.nrows):
            vals=[]
            for c in range(sh.ncols):
                v=sh.cell_value(r,c)
                vals.append(v)
            rows.append(vals)
        sheets.append({"name":sh.name,"rows":rows})
    out["files"][name]={"sheets":sheets}

reader=PdfReader(str(base/"Sr-90_tables.pdf"))
out["files"]["Sr-90_tables.pdf"]={
    "page_count":len(reader.pages),
    "text":[(p.extract_text() or "") for p in reader.pages]
}
print(json.dumps(out,indent=2,ensure_ascii=False))
