import json, time
from fastcoref import FCoref

text="Alice approved the release package. She archived it after approval."
t0=time.time()
model=FCoref(device="cpu")
loaded=time.time()
pred=model.predict(texts=[text])
done=time.time()
clusters=pred[0].get_clusters()
assert clusters, clusters
joined=" ".join(" ".join(c) for c in clusters)
assert "Alice" in joined and ("She" in joined or "she" in joined), clusters
print(json.dumps({"status":"PASS","clusters":clusters,"load_seconds":loaded-t0,"infer_seconds":done-loaded}))
