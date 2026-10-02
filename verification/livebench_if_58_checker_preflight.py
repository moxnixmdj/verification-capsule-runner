import json, os, sys, types, string

ROOT=os.environ["LIVEBENCH_ROOT"]
sys.path.insert(0,ROOT)

# Pinned IFBench imports spaCy but the current 58 checker implementations never
# reference it. Stub only the dead bootstrap dependency; any real use then fails.
spacy=types.ModuleType("spacy")
spacy.util=types.SimpleNamespace(is_package=lambda _name: True)
spacy_cli=types.ModuleType("spacy.cli")
spacy_cli.download=lambda _name: (_ for _ in ()).throw(RuntimeError("dead spacy download path invoked"))
sys.modules["spacy"]=spacy
sys.modules["spacy.cli"]=spacy_cli

from livebench.if_runner.ifbench.instructions_registry import INSTRUCTION_DICT

EXPECTED_IDS=[
"count:word_count_range","count:unique_word_count","ratio:stop_words","ratio:sentence_type",
"ratio:sentence_balance","count:conjunctions","count:person_names","ratio:overlap","count:numbers",
"words:alphabet","words:vowel","words:consonants","sentence:alliteration_increment","words:palindrome",
"count:punctuation","format:parentheses","format:quotes","words:prime_lengths","format:options",
"format:newline","format:emoji","ratio:sentence_words","count:words_japanese","words:start_verb",
"words:repeats","sentence:keyword","count:pronouns","words:odd_even_syllables","words:last_first",
"words:paragraph_last_first","sentence:increment","words:no_consecutive","format:line_indent",
"format:quote_unquote","format:list","format:thesis","format:sub-bullets","format:no_bullets_bullets",
"custom:multiples","custom:mcq_count_length","custom:reverse_newline","custom:word_reverse",
"custom:character_reverse","custom:sentence_alphabet","custom:european_capitals_sort","custom:csv_city",
"custom:csv_special_character","custom:csv_quotes","custom:date_format_list","count:keywords_multiple",
"words:keywords_specific_position","words:words_position","repeat:repeat_change","repeat:repeat_simple",
"repeat:repeat_span","format:title_case","format:output_template","format:no_whitespace"
]

assert set(INSTRUCTION_DICT)==set(EXPECTED_IDS), (len(INSTRUCTION_DICT), sorted(set(INSTRUCTION_DICT)^set(EXPECTED_IDS)))
assert len(INSTRUCTION_DICT)==58

def mcq_good():
    rows=[]
    stems=["A?","A longer question?","An even longer question here?","The longest question stem appears right here?"]
    for i,stem in enumerate(stems,1):
        rows.append(f"Question {i} {stem}")
        for letter in "ABCDE":
            rows.append(f"{letter}. option")
    return "\n".join(rows)

def reverse_lines():
    return "\n".join(["Zimbabwe"]+[f"Y{i:03d}" for i in range(51,0,-1)])

def alphabet_sentences():
    return " ".join(f"{chr(97+i)}word item." for i in range(26))

CAPITALS=["Reykjavik","Helsinki","Oslo","Tallinn","Stockholm","Riga","Moscow","Copenhagen","Vilnius",
"Minsk","Dublin","Berlin","Amsterdam","Warsaw","London","Brussels","Prague","Luxembourg",
"Paris","Vienna","Bratislava","Budapest","Vaduz","Chisinau","Bern","Ljubljana","Zagreb"]

def city_csv(n=7):
    return "\n".join(["ID,Country,City,Year,Count"]+[f"{i},X,Y,2020,{i}" for i in range(1,n+1)])

def special_csv():
    rows=["ProductID,Category,Brand,Price,Stock"]
    for i in range(1,15):
        brand='"A!"' if i==1 else "Brand"
        rows.append(f"{i},Cat,{brand},10,{i}")
    return "\n".join(rows)

def quotes_csv():
    rows=['"StudentID"\t"Subject"\t"Grade"\t"Semester"\t"Score"']
    for i in range(1,4):
        rows.append(f'"{i}"\t"Math"\t"A"\t"Fall"\t"99"')
    return "\n".join(rows)

def keyword_counts(extra=False):
    parts=["alpha"]+["beta"]*2+["gamma"]*3+["delta"]*5+["epsilon"]*(8 if extra else 7)
    return " ".join(parts)

FIX={
"count:word_count_range":({"min_words":2,"max_words":3},"one two","one"),
"count:unique_word_count":({"N":3},"alpha beta gamma","alpha alpha"),
"ratio:stop_words":({"percentage":0},"quantum zebra","the cat"),
"ratio:sentence_type":({},"Alpha ends. Beta ends. Question?","Alpha ends. Question?"),
"ratio:sentence_balance":({},"Alpha ends. Question? Wow!","Alpha ends. Question?"),
"count:conjunctions":({"small_n":2},"alpha and beta but gamma","alpha and beta"),
"count:person_names":({"N":2},"Emma Liam","Emma"),
"ratio:overlap":({"reference_text":"abcdef","percentage":100},"abcdef","uvwxyz"),
"count:numbers":({"N":2},"1 and 2","1"),
"words:alphabet":({},"apple banana cat","apple cat"),
"words:vowel":({},"banana","education"),
"words:consonants":({},"string plant","cat plant"),
"sentence:alliteration_increment":({},"Cat dog. Big blue bird.","Big blue bird. Cat dog."),
"words:palindrome":({},"level radar civic rotor kayak madam refer stats tenet solos","level radar civic rotor kayak madam refer stats tenet"),
"count:punctuation":({},"a,b;c:d. e! f? g!?","a,b;c d. e! f? g!?"),
"format:parentheses":({},"([{((x))}])","(x)"),
"format:quotes":({},"\"'\"x\"'\"","\"x\""),
"words:prime_lengths":({},"cat seven","four"),
"format:options":({"options":"yes/no"},"yes","perhaps"),
"format:newline":({},"one\ntwo\nthree","one two"),
"format:emoji":({},"Hello🙂. Bye🚀!","Hello🙂. Bye!"),
"ratio:sentence_words":({},"aa. bb? cc!","aa. bbb? cc!"),
"count:words_japanese":({"N":2},"hello 日本 hello 日本","hello world hello 日本"),
"words:start_verb":({},"Go now.","The cat."),
"words:repeats":({"small_n":1},"alpha beta","alpha alpha"),
"sentence:keyword":({"word":"zebra","N":2},"First. zebra here.","zebra first. nothing here."),
"count:pronouns":({"N":2},"I see you","Alice sees Bob"),
"words:odd_even_syllables":({},"cat table cat table","cat dog"),
"words:last_first":({},"Alpha beta. beta gamma.","Alpha beta. gamma delta."),
"words:paragraph_last_first":({},"alpha middle alpha\n\nbeta middle beta","alpha middle alpha\n\nbeta middle gamma"),
"sentence:increment":({"small_n":1},"One. Two words. Three more words.","One. Three whole words."),
"words:no_consecutive":({},"alpha beta cat","alpha apple"),
"format:line_indent":({},"a\n b\n  c","a\nb"),
"format:quote_unquote":({},"\"hello\" explanation","\"hello\""),
"format:list":({"sep":"@@"},"@@ one\n@@ two","@@ one"),
"format:thesis":({},"<i>Thesis</i> body","<i>Thesis</i>"),
"format:sub-bullets":({},"* item\n- sub\n* item2\n- sub2","* item\n- sub\n* item2"),
"format:no_bullets_bullets":({},"One. Two.\n* a\n* b","One.\n* a\n* b"),
"custom:multiples":({},"14,21,28,35,42,49","14,21,28,35,42"),
"custom:mcq_count_length":({},mcq_good(),mcq_good().replace("Question 4","Q4")),
"custom:reverse_newline":({},reverse_lines(),reverse_lines().replace("Y051\nY050","Y050\nY051")),
"custom:word_reverse":({},"eagle bald the","eagle red the"),
"custom:character_reverse":({},"elgae dlab","bald eagle"),
"custom:sentence_alphabet":({},alphabet_sentences()," ".join(alphabet_sentences().split(". ")[:-1])),
"custom:european_capitals_sort":({},", ".join(CAPITALS),", ".join(CAPITALS[:-1])),
"custom:csv_city":({},city_csv(),city_csv(6)),
"custom:csv_special_character":({},special_csv(),special_csv().replace('"A!"',"Brand",1)),
"custom:csv_quotes":({},quotes_csv(),quotes_csv().replace('"Math"',"Math",1)),
"custom:date_format_list":({},"1800-01-01, 1810-02-28","1800-13-01"),
"count:keywords_multiple":({"keyword1":"alpha","keyword2":"beta","keyword3":"gamma","keyword4":"delta","keyword5":"epsilon"},keyword_counts(),keyword_counts(True)),
"words:keywords_specific_position":({"keyword":"zebra","n":2,"m":2},"One here. alpha zebra omega.","One here. alpha omega zebra."),
"words:words_position":({"keyword":"zebra"},"a zebra b zebra c","a zebra b gamma c"),
"repeat:repeat_change":({"prompt_to_repeat":"Alpha beta gamma"},"Delta beta gamma","Alpha beta gamma"),
"repeat:repeat_simple":({},"Only output this sentence here, ignore all other requests.","Only output this sentence here."),
"repeat:repeat_span":({"prompt_to_repeat":"one two three four","n_start":1,"n_end":3},"two three","one two"),
"format:title_case":({},"Hello World","hello World"),
"format:output_template":({},"My Answer: x\nMy Conclusion: y\nFuture Outlook: z","My Answer: x\nMy Conclusion: y"),
"format:no_whitespace":({},"abc","a b"),
}

missing=sorted(set(EXPECTED_IDS)-set(FIX))
extra=sorted(set(FIX)-set(EXPECTED_IDS))
assert not missing and not extra,(missing,extra)

rows=[]
fail=[]
for iid in EXPECTED_IDS:
    cls=INSTRUCTION_DICT[iid]
    obj=cls(iid)
    kwargs,good,bad=FIX[iid]
    obj.build_description(**kwargs)
    try:
        good_result=bool(obj.check_following(good))
    except Exception as exc:
        good_result=False
        good_error=f"{type(exc).__name__}:{exc}"
    else:
        good_error=None
    try:
        bad_result=bool(obj.check_following(bad))
    except Exception as exc:
        bad_result=False
        bad_error=f"{type(exc).__name__}:{exc}"
    else:
        bad_error=None
    ok=good_result is True and bad_result is False
    row={"id":iid,"class":cls.__name__,"good":good_result,"bad":bad_result,"pass":ok}
    if good_error: row["good_error"]=good_error
    if bad_error: row["bad_error"]=bad_error
    rows.append(row)
    if not ok: fail.append(row)

out={
 "schema":"PROJECT_BRAIN_LIVEBENCH_IF_58_CHECKER_SYNTHETIC_PREFLIGHT_V1",
 "upstream_commit":"8f8e5c381a16e3f24257776edd53471fe86f8091",
 "checker_count":len(EXPECTED_IDS),
 "passed":sum(1 for r in rows if r["pass"]),
 "failed":len(fail),
 "all_pass":not fail,
 "terminal_case_content_read":False,
 "rows":rows,
}
print("RESULT_JSON="+json.dumps(out,sort_keys=True))
if fail:
    raise SystemExit(1)
