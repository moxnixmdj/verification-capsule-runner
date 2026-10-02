import json, time
import spacy
from fastcoref import FCoref

text="Alice approved the release package. She archived it after approval."
t0=time.time()
nlp=spacy.blank("en")
model=FCoref(model_name_or_path="biu-nlp/f-coref", device="cpu", nlp=nlp, enable_progress_bar=False)
loaded=time.time()
pred=model.predict(texts=text)
done=time.time()
clusters=pred.get_clusters()
assert clusters, clusters
flat=[[s.lower() for s in c] for c in clusters]
assert any("alice" in c and "she" in c for c in flat), clusters
print(json.dumps({"status":"PASS","clusters":clusters,"load_seconds":loaded-t0,"infer_seconds":done-loaded}))
