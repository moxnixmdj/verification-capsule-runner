from __future__ import annotations
import pathlib, subprocess, sys
from pypdf import PdfReader
import xlrd

root=pathlib.Path("/tmp/rank21")
for p in [root/"measurement data.xls", root/"sample.xls", root/"Sr-90_tables.pdf"]:
    if not p.exists():
        raise SystemExit(f"MISSING:{p}")

def dump_xls(path):
    print(f"=== XLS {path.name} ===")
    wb=xlrd.open_workbook(path)
    for sh in wb.sheets():
        print(f"-- SHEET {sh.name} rows={sh.nrows} cols={sh.ncols}")
        for r in range(sh.nrows):
            vals=[sh.cell_value(r,c) for c in range(sh.ncols)]
            if any(v not in ("",None) for v in vals):
                print(r+1, repr(vals))

dump_xls(root/"measurement data.xls")
dump_xls(root/"sample.xls")

print("=== PDF Sr-90_tables.pdf ===")
reader=PdfReader(root/"Sr-90_tables.pdf")
print("pages",len(reader.pages))
for i,p in enumerate(reader.pages):
    txt=p.extract_text() or ""
    print(f"-- PAGE {i+1}")
    print(txt)
