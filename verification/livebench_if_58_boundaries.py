#!/usr/bin/env python3
import json, os, random, sys

import nltk
def _blocked_download(*args, **kwargs):
    raise RuntimeError("NETWORK_DOWNLOAD_FORBIDDEN_DURING_BOUNDARY_PREFLIGHT")
nltk.download=_blocked_download

from livebench.if_runner.ifbench import instructions_registry

def reverse_newline_good():
    return "\n".join(["Zimbabwe"]+[f"Y{i:02d}" for i in range(51,0,-1)])

def mcq_good():
    qs=[]
    stems=["A","A longer","A much longer stem","A substantially longer question stem"]
    for i,stem in enumerate(stems,1):
        qs.append(
            f"Question {i} {stem}\n"
            "A. one\nB. two\nC. three\nD. four\nE. five"
        )
    return "\n".join(qs)

def alphabet_sentences():
    words=[
      "Apple","Boat","Cat","Dog","Eagle","Fox","Goat","Horse","Island","Jewel","Kite","Lemon","Moon",
      "Nest","Orange","Pear","Queen","River","Sun","Tree","Umbrella","Violet","Water","Xylophone","Yam","Zebra"
    ]
    return " ".join(w+"." for w in words)

def city_csv():
    rows=["ID,Country,City,Year,Count"]
    rows += [f"{i},Country{i},City{i},1800,{i}" for i in range(1,8)]
    return "\n".join(rows)

def special_csv():
    rows=["ProductID,Category,Brand,Price,Stock",'1,Tools,"Brand!",10,2']
    rows += [f"{i},Tools,Brand,10,2" for i in range(2,15)]
    return "\n".join(rows)

def quoted_tsv():
    rows=['"StudentID"\t"Subject"\t"Grade"\t"Semester"\t"Score"']
    rows += [
      '"1"\t"Math"\t"A"\t"Fall"\t"90"',
      '"2"\t"Science"\t"B"\t"Fall"\t"80"',
      '"3"\t"Art"\t"A"\t"Spring"\t"95"',
    ]
    return "\n".join(rows)

CAPITALS="Reykjavik, Helsinki, Oslo, Tallinn, Stockholm, Riga, Moscow, Copenhagen, Vilnius, Minsk, Dublin, Berlin, Amsterdam, Warsaw, London, Brussels, Prague, Luxembourg, Paris, Vienna, Bratislava, Budapest, Vaduz, Chisinau, Bern, Ljubljana, Zagreb"

CASES={
"count:word_count_range":({"min_words":3,"max_words":3},"one two three","one two"),
"count:unique_word_count":({"N":3},"one two three","one one"),
"ratio:stop_words":({"percentage":0},"quartz glyph","the and"),
"ratio:sentence_type":({},"One. Two. Three?","One. Two?"),
"ratio:sentence_balance":({},"One. Two? Three!","One. Two?"),
"count:conjunctions":({"small_n":2},"and but","and"),
"count:person_names":({"N":2},"Emma Liam","Emma"),
"ratio:overlap":({"reference_text":"abcdef","percentage":100},"abcdef","uvwxyz"),
"count:numbers":({"N":2},"1 2","1"),
"words:alphabet":({},"apple boat cat","apple cat"),
"words:vowel":({},"cat bed","a e i o"),
"words:consonants":({},"brick strong","cat"),
"sentence:alliteration_increment":({},"cat dog. big brown cat.","big brown. cat dog."),
"words:palindrome":({}," ".join(["level"]*10)," ".join(["level"]*9)),
"count:punctuation":({},"a,b;c:d.e! f? g?!","a,b c:d.e! f? g?!"),
"format:parentheses":({},"((((()))))","(((())))"),
"format:quotes":({},'"'+"'"+'"'+'"'+"'"+'"','"'+"'"+"'"+'"'),
"words:prime_lengths":({},"aa bbb","aaaa"),
"format:options":({"options":"red,blue"},"red","green"),
"format:newline":({},"one\ntwo","one two"),
"format:emoji":({},"Hello 😊.","Hello."),
"ratio:sentence_words":({},"Cat. Dog? Sun!","Cat. Longer? Sun!"),
"count:words_japanese":({"N":2},"one 日本 two 日本","one two"),
"words:start_verb":({},"Write clearly.","Table clearly."),
"words:repeats":({"small_n":1},"one two","one one"),
"sentence:keyword":({"word":"alpha","N":2},"First. one alpha.","alpha first. second."),
"count:pronouns":({"N":2},"I see you.","I see."),
"words:odd_even_syllables":({},"cat table cat table","cat dog"),
"words:last_first":({},"One bridge. Bridge two.","One bridge. Road two."),
"words:paragraph_last_first":({},"Alpha beta alpha\n\nGamma delta gamma","Alpha beta alpha\n\nGamma delta wrong"),
"sentence:increment":({"small_n":1},"One. Two words.","One. Two."),
"words:no_consecutive":({},"apple boat cat","apple ant"),
"format:line_indent":({},"a\n b\n  c","a\n b\n c"),
"format:quote_unquote":({},'He said "hi" and left.','He said "hi"'),
"format:list":({"sep":"@@"},"@@ item one\n@@ item two","@@ item one"),
"format:thesis":({},"<i>Claim</i> Explanation","<i>Claim</i>"),
"format:sub-bullets":({},"* item\n- sub","* item"),
"format:no_bullets_bullets":({},"First sentence. Second sentence.\n* a\n* b","First sentence.\n* a\n* b"),
"custom:multiples":({},"14,21,28,35,42,49","14,21,28,35,42"),
"custom:mcq_count_length":({},mcq_good(),mcq_good().replace("E. five","",1)),
"custom:reverse_newline":({},reverse_newline_good(),"\n".join(reverse_newline_good().splitlines()[:-1]+["Y99"])),
"custom:word_reverse":({},"eagle bald","bald eagle"),
"custom:character_reverse":({},"elgae dlab","bald eagle"),
"custom:sentence_alphabet":({},alphabet_sentences(),alphabet_sentences().replace("Moon.","Noon.",1)),
"custom:european_capitals_sort":({},CAPITALS,CAPITALS.replace("Helsinki, Oslo","Oslo, Helsinki")),
"custom:csv_city":({},city_csv(),"\n".join(city_csv().splitlines()[:-1])),
"custom:csv_special_character":({},special_csv(),special_csv().replace('"Brand!"',"Brand")),
"custom:csv_quotes":({},quoted_tsv(),quoted_tsv().replace('"90"',"90")),
"custom:date_format_list":({},"1800-01-01, 1801-02-28","1900-01-01"),
"count:keywords_multiple":(
 {"keyword1":"alpha","keyword2":"beta","keyword3":"gamma","keyword4":"delta","keyword5":"epsilon"},
 "alpha "+"beta "*2+"gamma "*3+"delta "*5+"epsilon "*7,
 "alpha "+"beta "*2+"gamma "*3+"delta "*5+"epsilon "*6
),
"words:keywords_specific_position":({"keyword":"alpha","n":2,"m":2},"First sentence. one alpha three.","First sentence. alpha one three."),
"words:words_position":({"keyword":"key"},"a key b key c","a key b x c"),
"repeat:repeat_change":({"prompt_to_repeat":"Original alpha beta"},"Changed alpha beta","Original alpha beta"),
"repeat:repeat_span":({"prompt_to_repeat":"zero one two three four","n_start":1,"n_end":4},"one two three","one two"),
"format:title_case":({},"Hello World","hello World"),
"format:output_template":({},"My Answer: A\nMy Conclusion: B\nFuture Outlook: C","My Answer: A\nMy Conclusion: B"),
"format:no_whitespace":({},"abc","a b"),
}

registry=instructions_registry.INSTRUCTION_DICT
if len(registry)!=58:
    raise RuntimeError(f"CHECKER_COUNT_MISMATCH:{len(registry)}")
if set(CASES)|{"repeat:repeat_simple"} != set(registry):
    missing=set(registry)-(set(CASES)|{"repeat:repeat_simple"})
    extra=set(CASES)-set(registry)
    raise RuntimeError(f"BOUNDARY_MAP_MISMATCH missing={sorted(missing)} extra={sorted(extra)}")

rows=[]
for iid, cls in registry.items():
    inst=cls(iid)
    random.seed("PROJECT_BRAIN_LIVEBENCH_BOUNDARY_V1:"+iid)
    if iid=="repeat:repeat_simple":
        desc=inst.build_description()
        good=desc
        bad=desc+" extra"
        kwargs={}
    else:
        kwargs,good,bad=CASES[iid]
        desc=inst.build_description(**kwargs)
    try:
        g=bool(inst.check_following(good))
        b=bool(inst.check_following(bad))
        err=None
    except Exception as e:
        g=False;b=True
        err=type(e).__name__+":"+str(e)[:300]
    rows.append({"id":iid,"class":cls.__name__,"good_pass":g,"bad_pass":b,"boundary_pass":g and not b,"error":err})

fail=[x for x in rows if not x["boundary_pass"]]
out={
  "schema":"PROJECT_BRAIN_LIVEBENCH_IF_58_CHECKER_SYNTHETIC_BOUNDARY_PREFLIGHT_V1",
  "checker_count":len(rows),
  "boundary_pass_count":len(rows)-len(fail),
  "failures":fail,
  "rows":rows,
  "terminal_case_content_read":False,
  "fresh_terminal_evidence_consumed":0,
  "incremental_spend_usd":0,
}
out["status"]="PASS" if not fail else "FAIL_CLOSED"
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
if fail:
    raise SystemExit(1)
