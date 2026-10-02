import hashlib, importlib.metadata, json, re
from pathlib import Path
import stanza
SPEC=json.loads(Path("verification/m0a_stanza_coref_dev.json").read_text())
CORPUS=json.loads(Path("verification/m0a_olmo_contrastive_dev.json").read_text())
CASES={x["id"]:x for x in CORPUS["cases"]}
ROOT=Path("/tmp/stanza_resources")
def norm(s): return " ".join(re.findall(r"[a-z0-9]+",s.lower()))
def mention_text(doc,m):
    sent=doc.sentences[m.sentence]
    if not isinstance(m.start_word,int) or not isinstance(m.end_word,int): return "_ZERO_"
    return " ".join(w.text for w in sent.words[m.start_word:m.end_word])
def chain_texts(doc):
    return [[mention_text(doc,m) for m in ch.mentions] for ch in doc.coref]
def contains(text,pat): return norm(pat) in norm(text)
def link_exists(chains,left,right):
    return any(any(contains(x,left) for x in ch) and any(contains(x,right) for x in ch) for ch in chains)
EXPECT={
 "DEV_PRONOUN_SINGULAR_001":[["backup process","It"]],
 "DEV_PLURAL_PRONOUN_001":[["parser and verifier","They"]],
 "DEV_FORMER_LATTER_001":[["producer","former"],["verdict.json","latter"]],
 "DEV_CONDITIONAL_ANAPHORA_001":[["maintenance mode","that mode"]],
 "DEV_DEMONSTRATIVE_EVENT_001":[["recompute the manifest hash","This validation"]],
}
stanza.download("en",processors="tokenize,coref",model_dir=str(ROOT),verbose=False)
nlp=stanza.Pipeline("en",processors="tokenize,coref",dir=str(ROOT),use_gpu=False,verbose=False)
rows=[]
for cid in SPEC["admitted_cases"]:
    doc=nlp(CASES[cid]["source"])
    chains=chain_texts(doc)
    links=[{"left":a,"right":b,"observed":link_exists(chains,a,b)} for a,b in EXPECT[cid]]
    rows.append({"id":cid,"chains":chains,"links":links,"all_expected_links_observed":all(x["observed"] for x in links)})
hashes=[]
for base in [ROOT,Path("/tmp/hf")]:
    if base.exists():
        for p in sorted(x for x in base.rglob("*") if x.is_file()):
            h=hashlib.sha256()
            with p.open("rb") as f:
                for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
            hashes.append({"path":str(p),"bytes":p.stat().st_size,"sha256":h.hexdigest()})
result={
 "schema":"PROJECT_BRAIN_M0A_STANZA_COREF_DEV_RESULT_V1",
 "stanza_version":importlib.metadata.version("stanza"),
 "source_release_commit":SPEC["donor"]["release_commit"],
 "model_weight_license_status":SPEC["donor"]["model_weight_license_status"],
 "rows":rows,"case_pass_count":sum(x["all_expected_links_observed"] for x in rows),"case_count":len(rows),
 "classification":"PARTIAL_REFERENCE_PROPOSAL_SOURCE_ONLY","downloaded_artifact_hashes":hashes,
 "heldout_exposed":0,"fresh_terminal_evidence_consumed":0,"capability_credit":False,"family_credit":False,"incremental_spend_usd":0
}
print("RESULT_JSON="+json.dumps(result,sort_keys=True))
