set -e
python3 - <<'PY'
from pathlib import Path
import string, math, collections

cp=Path('/app/data/sample_ciphertext.txt').read_text()
pp=Path('/app/data/sample_plaintext.txt').read_text()
print('LEN',len(cp),len(pp),'SAME_NONALPHA',all((not p.isalpha() and p==c) or p.isalpha() for p,c in zip(pp,cp)))
print('PLAINTEXT_HEAD',repr(pp[:500]))
print('CIPHERTEXT_HEAD',repr(cp[:500]))

P=[]; C=[]; pos=[]
for i,(p,c) in enumerate(zip(pp,cp)):
    if p.isalpha() and c.isalpha():
        P.append(ord(p.lower())-97); C.append(ord(c.lower())-97); pos.append(i)
K=[(c-p)%26 for p,c in zip(P,C)]
KB=[(c+p)%26 for p,c in zip(P,C)]
KV=[(p-c)%26 for p,c in zip(P,C)]
print('ALPHA_LEN',len(P))
print('SHIFT_HEAD',''.join(chr(97+x) for x in K[:500]))

def exact_period(seq,k):
    return sum(seq[i]==seq[i%k] for i in range(k,len(seq))), max(1,len(seq)-k)

period=[]
for k in range(1,min(257,len(K)//2+1)):
    a,b=exact_period(K,k); period.append((a/b,k,a,b))
print('TOP_PERIODS',sorted(period,reverse=True)[:20])

def lag_scores(A,B,maxlag=512):
    out=[]
    n=min(len(A),len(B))
    for lag in range(1,min(maxlag,n-1)+1):
        m=n-lag
        if m<=0: break
        hit=sum(A[i]==B[i-lag] for i in range(lag,n))
        out.append((hit/m,lag,hit,m))
    return sorted(out,reverse=True)[:30]

print('K_vs_P_LAGS',lag_scores(K,P))
print('K_vs_C_LAGS',lag_scores(K,C))
print('NEGK_vs_P_LAGS',lag_scores(KV,P))
print('BEAUFORTK_vs_P_LAGS',lag_scores(KB,P))

# Test whether key schedule advances by raw character positions rather than alphabetic positions.
rawP=[None]*len(pp); rawC=[None]*len(pp); rawK=[None]*len(pp)
for i,(p,c) in enumerate(zip(pp,cp)):
    if p.isalpha() and c.isalpha():
        pv=ord(p.lower())-97; cv=ord(c.lower())-97
        rawP[i]=pv; rawC[i]=cv; rawK[i]=(cv-pv)%26
raw=[]
for lag in range(1,min(513,len(pp))):
    pairs=[(rawK[i],rawP[i-lag]) for i in range(lag,len(pp)) if rawK[i] is not None and rawP[i-lag] is not None]
    if pairs:
        hit=sum(a==b for a,b in pairs)
        raw.append((hit/len(pairs),lag,hit,len(pairs)))
print('RAWPOS_K_vs_P_LAGS',sorted(raw,reverse=True)[:30])

# Lane/interleave test: within each residue class mod stride, does K become plaintext-autokey after primer m?
best=[]
for stride in range(2,17):
    for m in range(1,33):
        hit=tot=0
        for r in range(stride):
            idx=list(range(r,len(K),stride))
            for j in range(m,len(idx)):
                tot+=1
                if K[idx[j]]==P[idx[j-m]]: hit+=1
        if tot:
            best.append((hit/tot,stride,m,hit,tot))
print('INTERLEAVED_P_AUTOKEY',sorted(best,reverse=True)[:40])

# Repeat-key per lane: K on each lane periodic with small period.
bestp=[]
for stride in range(2,17):
    for per in range(1,33):
        hit=tot=0
        for r in range(stride):
            idx=list(range(r,len(K),stride))
            for j in range(per,len(idx)):
                tot+=1
                if K[idx[j]]==K[idx[j%per]]: hit+=1
        if tot: bestp.append((hit/tot,stride,per,hit,tot))
print('INTERLEAVED_PERIODIC',sorted(bestp,reverse=True)[:40])

# Character-level case relation sanity.
case_ok=sum((p.isupper()==c.isupper()) for p,c in zip(pp,cp) if p.isalpha() and c.isalpha())
print('CASE_PRESERVED',case_ok,len(P))
PY
