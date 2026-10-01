import json, pathlib, sys
import xlrd
from pypdf import PdfReader

root=pathlib.Path(sys.argv[1])
out={"workbooks":{},"pdf":{}}
for name in ["measurement data.xls","sample.xls"]:
    p=root/name
    wb=xlrd.open_workbook(str(p), formatting_info=False)
    sheets=[]
    for sh in wb.sheets():
        cells=[]
        for r in range(sh.nrows):
            for c in range(sh.ncols):
                v=sh.cell_value(r,c)
                if v not in ("", None):
                    cells.append({"row":r+1,"col":c+1,"value":v})
        sheets.append({"name":sh.name,"nrows":sh.nrows,"ncols":sh.ncols,"nonempty":cells})
    out["workbooks"][name]=sheets
pdf=root/"Sr-90_tables.pdf"
reader=PdfReader(str(pdf))
out["pdf"]["pages"]=[{"page":i+1,"text":page.extract_text() or ""} for i,page in enumerate(reader.pages)]
print(json.dumps(out,ensure_ascii=False,indent=2))
