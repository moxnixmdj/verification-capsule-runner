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

# Formula inventory from source-preserving LibreOffice conversion. This reads
# formula metadata only; it does not calculate the requested task result.
import zipfile, xml.etree.ElementTree as ET
out["xlsx_formula_inventory"]={}
ns={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
for xlsx in sorted(root.glob("*.xlsx")):
    found=[]
    with zipfile.ZipFile(xlsx) as z:
        for member in sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")):
            xml=ET.fromstring(z.read(member))
            for cell in xml.findall(".//m:c",ns):
                f=cell.find("m:f",ns)
                if f is not None:
                    v=cell.find("m:v",ns)
                    found.append({"sheet_xml":member,"cell":cell.attrib.get("r"),"formula":f.text or "","cached":None if v is None else v.text})
    out["xlsx_formula_inventory"][xlsx.name]=found
print("FORMULA_INVENTORY")
print(json.dumps(out["xlsx_formula_inventory"],ensure_ascii=False,indent=2))
