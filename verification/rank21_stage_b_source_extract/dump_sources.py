from pathlib import Path
import xlrd
from pypdf import PdfReader

root=Path("/tmp/terminal-bench/tasks/foodstuff-beta-activity/environment/data")
for name in ["measurement data.xls","sample.xls"]:
    path=root/name
    print(f"=== WORKBOOK {name} ===")
    book=xlrd.open_workbook(path)
    print("sheets",book.sheet_names())
    for sh in book.sheets():
        print(f"--- SHEET {sh.name} rows={sh.nrows} cols={sh.ncols} ---")
        for r in range(sh.nrows):
            vals=[sh.cell_value(r,c) for c in range(sh.ncols)]
            if any(v not in ("",None) for v in vals):
                print(r,repr(vals))
pdf=root/"Sr-90_tables.pdf"
print("=== PDF Sr-90_tables.pdf ===")
reader=PdfReader(str(pdf))
print("pages",len(reader.pages))
for i,p in enumerate(reader.pages):
    txt=p.extract_text() or ""
    print(f"--- PAGE {i+1} ---")
    print(txt)
