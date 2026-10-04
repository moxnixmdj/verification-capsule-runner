from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PAYLOAD=ROOT/"H100_OEWN_SENSE_DISAMBIGUATION_PREEXPOSURE_PAYLOAD_V1.b64"

def safe_call(obj,name,default=None):
    value=getattr(obj,name,default)
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return value

def main():
    import wn
    if getattr(wn,"__version__",None)!="1.1.1":
        raise SystemExit("WN_VERSION_MISMATCH")
    raw=base64.b64decode(PAYLOAD.read_text().strip()).decode("utf-8")
    pre=json.loads(raw)
    if len(pre["tasks"])!=10:
        raise SystemExit("TASK_DENOMINATOR_INVALID")
    wn.download("oewn:2025")
    lex=wn.Wordnet("oewn:2025")
    rows=[]
    for task in pre["tasks"]:
        senses=[]
        for s in lex.synsets(task["lemma"]):
            lemmas=safe_call(s,"lemmas",[]) or []
            senses.append({
                "id":str(getattr(s,"id","")),
                "pos":str(getattr(s,"pos","")),
                "definition":safe_call(s,"definition","") or "",
                "lemmas":sorted(str(x) for x in lemmas),
            })
        rows.append({
            "task_id":task["id"],
            "lemma":task["lemma"],
            "context":task["context"],
            "intent":task["intent"],
            "sense_count":len(senses),
            "senses":sorted(senses,key=lambda x:x["id"]),
        })
    out={
      "schema":"PROJECT_BRAIN_H100_OEWN_SENSE_INVENTORY_EXPORT_V1",
      "source":{"lexicon":"oewn:2025","client_version":"1.1.1"},
      "task_count":len(rows),
      "rows":rows,
      "persistent_learned_bytes":0,
      "external_learned_capability_calls":0,
      "hard_nonclaim":"SENSE_INVENTORY_EXPORT_IS_NOT_DISAMBIGUATION"
    }
    print("H100_OEWN_SENSE_INVENTORY="+json.dumps(out,sort_keys=True))

if __name__=="__main__":
    main()
