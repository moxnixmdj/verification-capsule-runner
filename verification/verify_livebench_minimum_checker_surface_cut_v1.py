#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import pathlib
import urllib.request
from collections import defaultdict
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "verification_inputs" / "livebench_if_minimum_checker_surface_cut_v1.py"
EXPECTED_CANDIDATE_BLOB = "4751e8aced0fb08a594cc819882f7ca8bfdb3c3c"
DATA_URL = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
EXPECTED_DATA_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
EXPECTED_SET = {
    "count:conjunctions","count:numbers","count:pronouns","count:punctuation",
    "count:unique_word_count","count:word_count_range","format:emoji","format:line_indent",
    "format:list","format:parentheses","format:quotes","format:sub-bullets","format:thesis",
    "ratio:overlap","ratio:sentence_balance","ratio:sentence_type","ratio:sentence_words",
    "ratio:stop_words","sentence:increment","sentence:keyword","words:alphabet",
    "words:consonants","words:no_consecutive","words:odd_even_syllables","words:palindrome",
    "words:paragraph_last_first","words:vowel",
}


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_candidate():
    raw = CANDIDATE.read_bytes()
    assert git_blob_sha(raw) == EXPECTED_CANDIDATE_BLOB
    spec = importlib.util.spec_from_file_location("candidate_surface_cut", CANDIDATE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fetch_rows():
    req = urllib.request.Request(DATA_URL, headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    assert git_blob_sha(raw) == EXPECTED_DATA_BLOB, git_blob_sha(raw)
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    assert len(rows) == 300
    assert sum(len(x["instruction_id_list"]) == 1 for x in rows) == 256
    assert sum(len(x["instruction_id_list"]) == 2 for x in rows) == 44
    assert len({i for row in rows for i in row["instruction_id_list"]}) == 58
    return rows


def independent_max_score4_by_k(rows):
    names = sorted({i for row in rows for i in row["instruction_id_list"]})
    ix = {name:i for i,name in enumerate(names)}
    single = [0] * len(names)
    edges = defaultdict(int)
    adj = [set() for _ in names]
    for row in rows:
        ids = row["instruction_id_list"]
        assert len(ids) in (1,2)
        if len(ids) == 1:
            single[ix[ids[0]]] += 1
        else:
            a,b = sorted((ix[ids[0]],ix[ids[1]]))
            edges[(a,b)] += 1
            adj[a].add(b); adj[b].add(a)

    seen=set(); components=[]
    for start in range(len(names)):
        if start in seen: continue
        stack=[start]; seen.add(start); comp=[]
        while stack:
            u=stack.pop(); comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v); stack.append(v)
        components.append(comp)

    tables=[]
    for comp in components:
        pos={v:j for j,v in enumerate(comp)}
        local_edges=[(pos[a],pos[b],w) for (a,b),w in edges.items() if a in pos and b in pos]
        best=[-1]*(len(comp)+1)
        for mask in range(1<<len(comp)):
            k=mask.bit_count()
            score4=sum(4*single[v] for j,v in enumerate(comp) if mask>>j&1)
            for a,b,w in local_edges:
                n=((mask>>a)&1)+((mask>>b)&1)
                score4 += w*(4 if n==2 else 1 if n==1 else 0)
            best[k]=max(best[k],score4)
        tables.append(best)

    dp=[0]
    for table in tables:
        nxt=[-1]*(len(dp)+len(table)-1)
        for a,x in enumerate(dp):
            for b,y in enumerate(table):
                if y >= 0:
                    nxt[a+b]=max(nxt[a+b],x+y)
        dp=nxt
    return dp


def main():
    candidate=load_candidate()
    rows=fetch_rows()
    out=candidate.solve(rows,"65.7")

    assert out["minimum_checker_type_count"] == 27
    assert out["best_score4"] == 796
    assert out["best_score_percent_fraction"] == "199/3"
    assert out["best_with_one_fewer"]["checker_type_count"] == 26
    assert out["best_with_one_fewer"]["score4"] == 773
    assert out["best_with_one_fewer"]["score_percent_fraction"] == "773/12"
    assert set(out["checker_types"]) == EXPECTED_SET

    independent=independent_max_score4_by_k(rows)
    threshold4 = 789  # ceil(4*300*0.657)
    assert independent[26] == 773 < threshold4
    assert independent[27] == 796 >= threshold4

    print(json.dumps({
        "status":"PASS",
        "candidate_blob":EXPECTED_CANDIDATE_BLOB,
        "data_blob":EXPECTED_DATA_BLOB,
        "rows":300,
        "instruction_types":58,
        "threshold_percent":"65.7",
        "threshold_score4":threshold4,
        "max_score4_26":independent[26],
        "max_score4_27":independent[27],
        "minimum_checker_types":27,
        "best_score_percent":"199/3",
        "terminal_prompt_content_used":False,
        "acceptance_credit":False
    },sort_keys=True))


if __name__ == "__main__":
    main()
