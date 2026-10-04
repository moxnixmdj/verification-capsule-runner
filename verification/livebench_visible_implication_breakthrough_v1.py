#!/usr/bin/env python3
import hashlib, json, re, urllib.request

DATA_URL = "https://raw.githubusercontent.com/google-research/google-research/e49bbfe381c9c0e564b937f1c4e163a2273c65cc/instruction_following_eval/data/input_data.jsonl"
ACTIVE = [
    "keywords:existence","keywords:forbidden_words","length_constraints:number_paragraphs",
    "length_constraints:number_words","length_constraints:number_sentences","length_constraints:nth_paragraph_first_word",
    "detectable_content:postscript","detectable_format:number_bullet_lists","detectable_format:title",
    "detectable_format:multiple_sections","detectable_format:json_format","combination:repeat_prompt",
    "combination:two_responses","startend:end_checker","startend:quotation"
]
EXPECTED_COUNTS = {
    "keywords:existence":39,"keywords:forbidden_words":49,"length_constraints:number_paragraphs":27,
    "length_constraints:number_words":52,"length_constraints:number_sentences":52,
    "length_constraints:nth_paragraph_first_word":12,"detectable_content:postscript":26,
    "detectable_format:number_bullet_lists":31,"detectable_format:title":37,
    "detectable_format:multiple_sections":14,"detectable_format:json_format":17,
    "combination:repeat_prompt":41,"combination:two_responses":24,
    "startend:end_checker":26,"startend:quotation":41
}

raw = urllib.request.urlopen(DATA_URL, timeout=30).read()
rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
assert len(rows) == 541

counts = {k:0 for k in ACTIVE}
for row in rows:
    for iid in row["instruction_id_list"]:
        if iid in counts:
            counts[iid] += 1
assert counts == EXPECTED_COUNTS, (counts, EXPECTED_COUNTS)
assert sum(counts.values()) == 488

# Every active keyword/forbidden target is visibly present in the public prompt.
keyword_visible = 0
forbidden_visible = 0
for row in rows:
    for iid, kw in zip(row["instruction_id_list"], row["kwargs"]):
        pl = row["prompt"].lower()
        if iid == "keywords:existence":
            for word in kw["keywords"]:
                assert word.lower() in pl, (iid, word, row["prompt"])
                keyword_visible += 1
        elif iid == "keywords:forbidden_words":
            for word in kw["forbidden_words"]:
                assert word.lower() in pl, (iid, word, row["prompt"])
                forbidden_visible += 1

# Constructive counterexample to "visible numeric text == hidden kwargs".
stronger_visible = []
for row in rows:
    for iid, kw in zip(row["instruction_id_list"], row["kwargs"]):
        if iid == "length_constraints:number_words" and kw == {"relation":"at least","num_words":336}:
            if re.search(r"at least\s+400\s+words", row["prompt"], flags=re.I):
                stronger_visible.append(row)
assert len(stronger_visible) == 1
assert 400 >= 336

# Visible semantic constraints can exist without the corresponding hidden label.
visible_not_hidden = [
    r for r in rows
    if re.search(r"using only\s+10\s+words", r["prompt"], flags=re.I)
    and "length_constraints:number_words" not in r["instruction_id_list"]
]
assert visible_not_hidden, "expected strict visible-surface superset witness"

# Prove exact active-family incompatibility for repeat_prompt + forbidden_words.
contradictions = []
for row in rows:
    ids = row["instruction_id_list"]
    if "combination:repeat_prompt" not in ids or "keywords:forbidden_words" not in ids:
        continue
    ri = ids.index("combination:repeat_prompt")
    fi = ids.index("keywords:forbidden_words")
    repeated = row["kwargs"][ri]["prompt_to_repeat"]
    forbidden = row["kwargs"][fi]["forbidden_words"]
    hits = []
    for word in forbidden:
        if re.search(r"\b" + re.escape(word) + r"\b", repeated, flags=re.I):
            hits.append(word)
    # Repeat checker requires response to start with repeated verbatim text.
    # Forbidden checker rejects any forbidden word anywhere in response.
    assert set(hits) == set(forbidden), (forbidden, hits, repeated)
    contradictions.append({
        "forbidden_words": forbidden,
        "prompt_to_repeat_sha256": hashlib.sha256(repeated.encode()).hexdigest(),
        "proof": "REQUIRED_REPEAT_CONTAINS_EVERY_FORBIDDEN_WORD"
    })
assert len(contradictions) == 2

receipt = {
    "schema":"PROJECT_BRAIN_LIVEBENCH_VISIBLE_IMPLICATION_BREAKTHROUGH_PUBLIC_VERIFICATION_V1",
    "status":"INDEPENDENT_PUBLIC_DATA_PASS__ZERO_TERMINAL_DATA__ZERO_CREDIT",
    "public_dataset":{
        "url":DATA_URL,
        "sha256":hashlib.sha256(raw).hexdigest(),
        "rows":len(rows),
        "active15_instruction_instances":sum(counts.values()),
        "active15_counts":counts
    },
    "proved":{
        "all_hidden_existence_keywords_visible_in_prompt_occurrences":keyword_visible,
        "all_hidden_forbidden_words_visible_in_prompt_occurrences":forbidden_visible,
        "hidden_kwarg_exact_inversion_not_required_for_monotone_witness":True,
        "visible_constraint_surface_strictly_exceeds_hidden_label_surface":True,
        "repeat_plus_forbidden_full_pass_impossible_public_rows":len(contradictions),
        "partial_credit_is_load_bearing":True
    },
    "numeric_counterexample":{
        "visible":"AT_LEAST_400_WORDS",
        "hidden":{"relation":"at least","num_words":336},
        "implication":"VISIBLE_400_PLUS_IMPLIES_HIDDEN_336_PLUS"
    },
    "contradictions":contradictions,
    "terminal_case_content_read":False,
    "terminal_cases_consumed":0,
    "acceptance_credit_delta":0
}
open("livebench_visible_implication_breakthrough_v1_receipt.json","w").write(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
