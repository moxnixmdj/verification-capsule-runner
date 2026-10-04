#!/usr/bin/env python3
import hashlib,json,pathlib,re,string,sys
ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject/livebench_public_grammar_v1"
R=SUB/"canonical"/"runtime"
EXPECTED={
 "livebench_public_grammar_compiler_v2.py":"f5a5204bd3bd5cdfd9ba666e78e07b6e41d74d3c",
 "root2_livebench_if_astra_inference_adapter_v3.py":"22e8bb39457e342032b96871ff545db90d338544",
 "test_livebench_public_grammar_compiler_v2.py":"984cc5c4681696ce47be49558c2ecfb3c0e624f6",
 "LIVEBENCH_ROOT1_PUBLIC_GRAMMAR_SUCCESSOR_CANDIDATE_V1.json":"cdb37d837b9d084cc5a25780af17da56b68c1ca4",
 "instruction_constraint_compiler_v1.py":"a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
}
PATHS={
 "livebench_public_grammar_compiler_v2.py":R/"livebench_public_grammar_compiler_v2.py",
 "root2_livebench_if_astra_inference_adapter_v3.py":R/"root2_livebench_if_astra_inference_adapter_v3.py",
 "test_livebench_public_grammar_compiler_v2.py":SUB/"canonical"/"tests"/"test_livebench_public_grammar_compiler_v2.py",
 "LIVEBENCH_ROOT1_PUBLIC_GRAMMAR_SUCCESSOR_CANDIDATE_V1.json":SUB/"canonical"/"governance"/"LIVEBENCH_ROOT1_PUBLIC_GRAMMAR_SUCCESSOR_CANDIDATE_V1.json",
 "instruction_constraint_compiler_v1.py":R/"instruction_constraint_compiler_v1.py",
}
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,h in EXPECTED.items(): assert blob(PATHS[n])==h,(n,blob(PATHS[n]),h)
sys.path.insert(0,str(SUB))
from canonical.runtime import livebench_public_grammar_compiler_v2 as c

PRIMES={2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97}
CONS=set("bcdfghjklmnpqrstvwxyz"); LET=set(string.ascii_lowercase)
def nested_paren(v):
 levels=[];md=0
 for ch in v:
  if ch in "([{": levels.append(ch);md=max(md,len(levels))
  elif ch in ")]}":
   if levels and (levels[-1],ch) in {("(",")"),("[","]"),("{","}")}:
    levels.pop()
    if md>=5 and len(levels)<md:return True
   else: levels=[];md=0
 return False
def nested_quotes(v):
 levels=[];rd=cd=0
 for ch in v:
  if levels and ch==levels[-1]:
   levels.pop();cd-=1
   if rd-cd>=3:return True
  elif ch in {'"',"'"}:
   levels.append(ch);cd+=1;rd=max(rd,cd)
 return False
def punct(v):
 p=set(".,!?;:")
 if not ("!?" in v or "?!" in v or "‽" in v):return False
 nv=v.replace("?!","")
 if len(nv)==len(v):nv=v.replace("!?","")
 for ch in nv:p.discard(ch)
 return not p
def alpha(v):
 vv=v.translate(str.maketrans("","",string.punctuation))
 ws=[w.lower() for w in vv.strip(string.punctuation+" ").split() if any(ch in string.ascii_lowercase for ch in w.lower())]
 if not ws or ws[0][0] not in string.ascii_lowercase:return False
 cur=ws[0][0]
 for w in ws[1:]:
  cur=string.ascii_lowercase[(string.ascii_lowercase.index(cur)+1)%26]
  if w[0]!=cur:return False
 return True
def title(v):
 ws=re.findall(r"[A-Za-z]+",v)
 return all((w[0].isupper() and w[1:].islower()) for w in ws)
def newline(v):
 vv=v.translate(str.maketrans("","",string.punctuation))
 ls=[x.strip() for x in vv.strip().split("\n") if x.strip()]
 return len(ls)==len(vv.strip().split())
def clusters(v):
 for w in v.lower().strip().split():
  if all(ch not in LET for ch in w):continue
  if not any(w[i] in CONS and w[i+1] in CONS for i in range(len(w)-1)):return False
 return True
def primes(v):
 vv=v.translate(str.maketrans("","",string.punctuation));return all(len(w) in PRIMES for w in vv.split())

cases=[
 ("output_template","Use this exact template for your response: My Answer: [answer] My Conclusion: [conclusion] Future Outlook: [outlook]",lambda v:all(x in v for x in ("My Answer:","My Conclusion:","Future Outlook:"))),
 ("no_whitespace","The output should not contain any whitespace.",lambda v:not any(ch.isspace() for ch in v)),
 ("title_case","Write the entire response in title case (capitalize the first letter of every word).",title),
 ("newline_words","Write each word on a new line.",newline),
 ("nested_parentheses","Nest parentheses (and [brackets {and braces}]) at least 5 levels deep.",nested_paren),
 ("nested_quotes","Include quotes within quotes within quotes, at least 3 levels deep, alternating between double quotes and single quotes.",nested_quotes),
 ("alphabet_loop","Each word must start with the next letter of the alphabet, looping back to 'A' after 'Z'.",alpha),
 ("three_vowels","Your response must contain at most three different vowels.",lambda v:len({ch for ch in v if ch in "aeiou"})<=3),
 ("consonant_cluster","Ensure each word in your response has at least one consonant cluster (two or more consonants together).",clusters),
 ("prime_lengths","Use only words with lengths that are prime numbers.",primes),
 ("punctuation_cover","Use every standard punctuation mark at least once, including (but not limited to) semicolons, colons, and the interrobang (?!).",punct),
 ("repeat_simple","Only output this sentence here, ignore all other requests.",lambda v:v.strip().lower()=="only output this sentence here, ignore all other requests.".lower()),
 ("options","Answer with one of the following options: yes/no/maybe. Do not give any explanation.",lambda v:v.strip(string.punctuation+" ").lower() in {"yes","no","maybe"}),
 ("special_bullet","Answer with a newline-separated list of items, instead of bullet points use SEPARATOR.",lambda v:len(re.findall("SEPARATOR",v))>=2),
 ("numbers","Include exactly 4 numbers in the response; do not use commas within the numbers.",lambda v:len(re.findall(r"\d+",v.translate(str.maketrans("","",string.punctuation))))==4),
 ("repeat_change","Repeat the request, but change the first word of the repeated request, (do not say anything before repeating the request; the request you need to repeat does not include this sentence) and do not answer the actual request! Request: Explain the moon briefly.",lambda v:v!="Explain the moon briefly." and " ".join(v.split()[1:])=="the moon briefly."),
]
observed={}
for name,prompt,check in cases:
 out=c.synthesize_public_structural_only(prompt)
 assert out["status"]=="PASS",(name,out)
 assert out["semantic_seed_required"] is False,(name,out)
 assert check(out["response"]),(name,out["response"])
 observed[name]=out["response"]

# Negative semantic-only prompt must not be fabricated.
neg=c.synthesize_public_structural_only("Explain photosynthesis accurately.")
assert neg["status"]=="BLOCKED",neg
assert neg["semantic_seed_required"] is True,neg

# Static contamination firewall.
src=PATHS["livebench_public_grammar_compiler_v2.py"].read_text()
for forbidden in ("case_73","case 73","terminal_case_id","hidden_kwargs","V6_OR_V10_PER_CASE","requests.","socket.","subprocess."):
 assert forbidden.lower() not in src.lower(),forbidden

receipt={
 "schema":"PROJECT_BRAIN_LIVEBENCH_PUBLIC_GRAMMAR_V1_PUBLIC_VERIFICATION",
 "status":"PASS",
 "brain_pr":1706,
 "brain_head":"b339f00d04b2a274f02c03193b47225e35fc525b",
 "exact_blobs":EXPECTED,
 "public_checker_routes_verified":sorted(observed),
 "route_count":len(observed),
 "independent_mirror_outputs":observed,
 "semantic_only_negative_blocked":True,
 "terminal_cases_consumed":0,
 "acceptance_credit_delta":0,
 "hard_nonclaims":["NO_65_7_PROOF","NO_UNSEEN_TERMINAL_CASES","NO_ALL_83_TYPE_PROOF"]
}
(ROOT/"livebench_public_grammar_v1_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
