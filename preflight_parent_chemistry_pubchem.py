#!/usr/bin/env python3
import json, urllib.request, pathlib, math

ROOT=pathlib.Path(__file__).resolve().parent
REPORT=ROOT/"parent-chemistry-pubchem-preflight.json"
sources=[
  ("ethanol","https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/ethanol/property/MolecularFormula,MolecularWeight/JSON","C2H6O"),
  ("oxygen","https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/oxygen/property/MolecularFormula,MolecularWeight/JSON","O2"),
  ("carbon_dioxide","https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/carbon%20dioxide/property/MolecularFormula,MolecularWeight/JSON","CO2"),
  ("water","https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/water/property/MolecularFormula,MolecularWeight/JSON","H2O"),
]
records=[]
failures=[]
for name,url,expected_formula in sources:
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-PubChem-Preflight/1"})
        with urllib.request.urlopen(req,timeout=20) as resp:
            status=resp.status
            payload=json.loads(resp.read(1000000).decode("utf-8"))
        row=payload["PropertyTable"]["Properties"][0]
        formula=str(row["MolecularFormula"])
        mw=float(row["MolecularWeight"])
        if status!=200: failures.append(name+":HTTP_"+str(status))
        if formula!=expected_formula: failures.append(name+":FORMULA_"+formula)
        if not math.isfinite(mw) or mw<=0: failures.append(name+":MW_INVALID")
        records.append({"name":name,"url":url,"http_status":status,"formula":formula,"molecular_weight":mw})
    except Exception as exc:
        failures.append(name+":"+type(exc).__name__+":"+str(exc))
report={
  "schema":"PROJECT_BRAIN_PARENT_CHEMISTRY_PUBCHEM_PREFLIGHT_V1",
  "task_id":"PARENT-CHEMISTRY-ETHANOL-COMBUSTION-MASS-BALANCE-20260930-001",
  "status":"PASS" if not failures else "FAIL",
  "source_only_preflight":True,
  "task_executed":False,
  "reaction_answer_computed":False,
  "records":records,
  "failures":failures,
}
REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
if failures: raise SystemExit(1)
