import json, time
from fastcoref import FCoref

tokens=["Alice","approved","the","release","package",".","She","archived","it","after","approval","."]
t0=time.time()
model=FCoref(device="cpu",nlp=None,enable_progress_bar=False)
loaded=time.time()
pred=model.predict(texts=tokens,is_split_into_words=True)
done=time.time()
clusters=pred.get_clusters()
assert clusters, clusters
joined=" ".join(" ".join(c) for c in clusters)
assert "Alice" in joined and ("She" in joined or "she" in joined), clusters
print(json.dumps({
  "status":"PASS",
  "clusters":clusters,
  "load_seconds":loaded-t0,
  "infer_seconds":done-loaded,
  "causal_surface":"PRETOKENIZED_INFERENCE_ONLY__NO_SPACY_PIPELINE"
}))
