set -e
python3 - <<'PY'
from pathlib import Path
import itertools, collections, re
ct=Path('/app/data/sample_ciphertext.txt').read_text()
pt=Path('/app/data/sample_plaintext.txt').read_text()

records=[]
word=-1; inword=False; cpos=-1; sent=0; alpha=0
for raw,(p,c) in enumerate(zip(pt,ct)):
    if p.isalpha():
        if not inword:
            word+=1; cpos=0; inword=True
        else:
            cpos+=1
        pv=ord(p.lower())-97; cv=ord(c.lower())-97
        records.append({'raw':raw,'a':alpha,'word':word,'cpos':cpos,'sent':sent,'p':pv,'k':(cv-pv)%26})
        alpha+=1
    else:
        inword=False
        if p in '.!?': sent+=1

def score_lanes(label, fn, L, primers):
    lanes=[[] for _ in range(L)]
    hit=tot=0; primer_positions=[]
    for rec in records:
        lane=fn(rec)%L
        hist=lanes[lane]
        q=primers[lane]
        if len(hist)<q:
            primer_positions.append(rec['a'])
        else:
            expect=hist[-q]
            tot+=1
            if rec['k']==expect: hit+=1
        hist.append(rec['p'])
    return hit/tot if tot else 0,hit,tot,primer_positions

families={
 'alpha_mod': lambda r:r['a'],
 'raw_mod': lambda r:r['raw'],
 'word_mod': lambda r:r['word'],
 'charpos_mod': lambda r:r['cpos'],
 'word_plus_char': lambda r:r['word']+r['cpos'],
 'word_minus_char': lambda r:r['word']-r['cpos'],
 'sent_plus_word': lambda r:r['sent']+r['word'],
}
results=[]
for label,fn in families.items():
  for L in range(2,11):
    # equal primer lengths
    for q in range(1,11):
      sc,h,t,pre=score_lanes(label,fn,L,[q]*L)
      if sc>.08: results.append((sc,label,L,(q,)*L,h,t,pre[:30]))
    # all positive compositions of total primer=10 for small L; optimize exhaustive for L<=5
    if L<=5:
      def comps(n,k,prefix=()):
        if k==1:
          if n>=1: yield prefix+(n,)
        else:
          for x in range(1,n-k+2):
            yield from comps(n-x,k-1,prefix+(x,))
      for qs in comps(10,L):
        sc,h,t,pre=score_lanes(label,fn,L,qs)
        if sc>.2: results.append((sc,label,L,qs,h,t,pre[:30]))
for row in sorted(results,reverse=True)[:100]:
    print('RESULT',row)

# Word-level lane where entire words are round-robin assigned, but autokey queues may use
# letters from previous words in same lane. Print top exact mappings for L=2..10.
for L in range(2,11):
  fn=families['word_mod']
  # infer best q for each lane independently 1..12
  qs=[]; hh=tt=0
  for lane in range(L):
    best=None
    for q in range(1,13):
      lanes=[[] for _ in range(L)]; h=t=0
      for rec in records:
        la=fn(rec)%L; hist=lanes[la]
        if la==lane and len(hist)>=q:
          t+=1; h+=rec['k']==hist[-q]
        hist.append(rec['p'])
      cand=(h/t if t else 0,q,h,t)
      if best is None or cand>best: best=cand
    qs.append(best)
    hh+=best[2];tt+=best[3]
  print('WORD_LANE_INDEPENDENT',L,hh/tt,qs)

# Detect whether after first 10 key letters the sequence equals plaintext under word-level block permutations:
# compare key-derived string by word boundaries and show first 25 words' K slices aligned to plaintext word slices.
kchars=''.join(chr(97+r['k']) for r in records)
pchars=''.join(chr(97+r['p']) for r in records)
print('FIRST10KEY',kchars[:10])
off=10
for w in range(min(30,word+1)):
    inds=[r['a'] for r in records if r['word']==w]
    if not inds: continue
    a,b=inds[0],inds[-1]+1
    # same-length segment from autokey payload index a if primer stripped
    print('WORD',w,'P',pchars[a:b],'Kpayload_at_same_alpha',kchars[10+a:10+b])
PY
