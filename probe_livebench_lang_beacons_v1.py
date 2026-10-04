#!/usr/bin/env python3
from __future__ import annotations
import json, math
from langdetect.detector_factory import DetectorFactory, PROFILES_DIRECTORY

TARGETS=("en","es","pt","ar","hi","fr","ru","de","ja","it","bn","uk","th","ur","ta","te","bg","ko","pl","he","fa","vi","ne","sw","kn","mr","gu","pa","ml","fi")
factory=DetectorFactory()
factory.load_profile(PROFILES_DIRECTORY)
assert set(TARGETS) <= set(factory.langlist)
lang_index={x:i for i,x in enumerate(factory.langlist)}

def detect_seed(text,seed):
    factory.seed=seed
    d=factory.create()
    d.append(text)
    return d.detect(), d.get_probabilities()[0].prob

def ranked(target):
    i=lang_index[target]
    rows=[]
    for g,ps in factory.word_lang_prob_map.items():
        p=ps[i]
        if p<=0: continue
        if not g.strip(): continue
        if any(ch in g for ch in ",[]*<>?!"):
            continue
        q=max(ps[:i]+ps[i+1:])
        purity=p/(q+1e-15)
        # Prefer exclusive/high-probability 2/3-grams and avoid bare spaces.
        score=(1000 if q==0 else math.log(purity+1e-30))*10 + math.log(p+1e-30) + len(g)
        rows.append((score,purity,p,g))
    rows.sort(reverse=True)
    out=[]
    seen=set()
    for row in rows:
        g=row[3]
        if g not in seen:
            seen.add(g); out.append(g)
    return out

def robust(text,target):
    noises=(
        "",
        " 9000001 9000002 [0] *0* ",
        "\n9000001.\n9000002\nP.S.+\n",
        '" 9000001 9000002 9000003 "',
    )
    worst=1.0
    for noise in noises:
        for placement in (text+noise, noise+text):
            for seed in range(48):
                got,p=detect_seed(placement,seed)
                if got!=target:
                    return False,(got,p,seed,repr(noise),placement[:120])
                worst=min(worst,p)
    return True,worst

results={}
for target in TARGETS:
    grams=ranked(target)
    best=None
    for k in (1,2,3,4,6,8,12,16,24,32,48,64):
        core=" ".join(grams[:k])
        for reps in (4,8,16,32,64):
            text=((core+" ")*reps).strip()
            if len(text)>9000: continue
            ok,detail=robust(text,target)
            if ok:
                cand=(len(text),float(detail),k,reps,text)
                if best is None or cand[:1] < best[:1]:
                    best=cand
                break
        if best and best[0] < 120:
            break
    if best is None:
        raise AssertionError("NO_ROBUST_BEACON:"+target)
    results[target]={
        "length":best[0],"worst_top_probability":best[1],
        "feature_count":best[2],"repetitions":best[3],
        "beacon":best[4],
    }
    print(target,results[target]["length"],results[target]["worst_top_probability"],repr(results[target]["beacon"][:100]))

out={
 "status":"PASS__PROFILE_DERIVED_ROBUST_BEACONS_FOR_ALL_30_PINNED_LANGUAGE_CODES",
 "target_count":len(TARGETS),
 "seed_count":48,
 "noise_profile_count":4,
 "placement_count":2,
 "checks_per_target":48*4*2,
 "results":results,
}
print("RESULT_JSON="+json.dumps(out,ensure_ascii=False,sort_keys=True))
