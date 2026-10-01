from pathlib import Path
import xlrd
from pypdf import PdfReader

root=Path("/tmp/terminal-bench/tasks/foodstuff-beta-activity/environment/data")
for name in ["measurement data.xls","sample.xls"]:
    path=root/name
    print(f"=== WORKBOOK {name} ===")
    book=xlrd.open_workbook(path, formatting_info=True)
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

print("=== SAMPLE RESULT CELL FORMATS (BIFF) ===")
book=xlrd.open_workbook(root/"sample.xls", formatting_info=True)
sh=book.sheet_by_name("Beta")
for r in [15,16,20,21,22,23,25]:
    cell=sh.cell(r,1)
    xf=book.xf_list[cell.xf_index]
    fmt=book.format_map.get(xf.format_key)
    print(f"B{r+1}", "value=",repr(cell.value), "ctype=",cell.ctype, "xf=",cell.xf_index, "format_key=",xf.format_key, "format=",repr(fmt.format_str if fmt else None))
