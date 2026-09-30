set -e
python3 - <<'PY'
from pathlib import Path
cp=Path('/app/data/sample_ciphertext.txt').read_text()
pp=Path('/app/data/sample_plaintext.txt').read_text()
P=[]; C=[]
for p,c in zip(pp,cp):
    if p.isalpha() and c.isalpha():
        P.append(ord(p.lower())-97); C.append(ord(c.lower())-97)
K=[(c-p)%26 for p,c in zip(P,C)]
n=len(K)

# For each residue class modulo stride, find best plaintext lag.
for stride in range(2,17):
    lanes=[]
    total_hit=total_n=0
    for r in range(stride):
        best=None
        for lag in range(1,65):
            pairs=[i for i in range(max(lag,r),n) if i%stride==r]
            if not pairs: continue
            hit=sum(K[i]==P[i-lag] for i in pairs)
            sc=hit/len(pairs)
            cand=(sc,lag,hit,len(pairs))
            if best is None or cand>best: best=cand
        lanes.append((r,)+best)
        total_hit+=best[2]; total_n+=best[3]
    print('STRIDE',stride,'WEIGHTED',total_hit/total_n,'LANES',lanes)

# Global best assignment using position modulo M -> lag, then inspect errors after a prefix.
cands=[]
for M in range(2,33):
    lagmap={}
    for r in range(M):
        best=max(
            (
                (sum(K[i]==P[i-l] for i in range(l,n) if i%M==r),
                 sum(1 for i in range(l,n) if i%M==r),
                 l)
                for l in range(1,65)
            ),
            key=lambda x:(x[0]/x[1] if x[1] else -1,x[0])
        )
        lagmap[r]=best[2]
    for start in range(0,100):
        idx=range(max(start,65),n)
        hit=sum(K[i]==P[i-lagmap[i%M]] for i in idx)
        tot=n-max(start,65)
        if tot:
            cands.append((hit/tot,M,start,lagmap,hit,tot))
best=sorted(cands,key=lambda x:x[0],reverse=True)[:20]
for x in best:
    print('MAP',x)

# More direct: for each position after 64, report which lags 1..32 match.
for i in range(64,min(180,n)):
    matches=[l for l in range(1,33) if K[i]==P[i-l]]
    print('I',i,'mod',i%12,'K',chr(97+K[i]),'P',chr(97+P[i]),'MATCHLAGS',matches)

# Test lane-autokey: if letters are distributed round-robin into L lanes, each lane has
# an independent primer length q; K at lane position j>=q equals previous plaintext in same lane.
for L in range(2,17):
    for q in range(1,9):
        hit=tot=0
        for i in range(L*q,n):
            if K[i]==P[i-L*q]:
                hit+=1
            tot+=1
        if hit/tot>0.08:
            print('LANE_AUTOKEY L,Q,LAG',L,q,L*q,hit/tot,hit,tot)

# Test cyclic varying lag pattern directly for periods 2..16 and lags 1..20 using coordinate ascent/exact per residue.
for period in range(2,17):
    lagmap=[]
    hits=0; tots=0
    for r in range(period):
        options=[]
        for lag in range(1,21):
            inds=[i for i in range(max(64,lag),n) if i%period==r]
            h=sum(K[i]==P[i-lag] for i in inds)
            options.append((h/len(inds),lag,h,len(inds)))
        b=max(options)
        lagmap.append((r,)+b)
        hits+=b[2]; tots+=b[3]
    if hits/tots>0.2:
        print('CYCLIC',period,hits/tots,lagmap)
PY
