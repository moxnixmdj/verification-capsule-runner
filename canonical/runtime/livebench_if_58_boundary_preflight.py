"""Synthetic good/bad boundary preflight for all 58 pinned LiveBench IF checkers.

No terminal benchmark cases are read. Each registered checker receives:
- explicit synthetic construction args when needed,
- one synthetic value that must be accepted,
- one nearby synthetic value that must be rejected.
"""
from __future__ import annotations
import json
from livebench.if_runner.ifbench import instructions_registry, evaluation_lib


ARGS = {
    "count:word_count_range": {"min_words":3,"max_words":3},
    "count:unique_word_count": {"N":3},
    "ratio:stop_words": {"percentage":0},
    "count:conjunctions": {"small_n":2},
    "count:person_names": {"N":2},
    "ratio:overlap": {"reference_text":"abcdef","percentage":100},
    "count:numbers": {"N":2},
    "format:options": {"options":"yes/no/maybe"},
    "count:words_japanese": {"N":2},
    "words:repeats": {"small_n":1},
    "sentence:keyword": {"word":"target","N":2},
    "count:pronouns": {"N":2},
    "sentence:increment": {"small_n":1},
    "format:list": {"sep":"###"},
    "count:keywords_multiple": {
        "keyword1":"alpha","keyword2":"beta","keyword3":"gamma",
        "keyword4":"delta","keyword5":"epsilon",
    },
    "words:keywords_specific_position": {"keyword":"target","n":1,"m":2},
    "words:words_position": {"keyword":"target"},
    "repeat:repeat_change": {"prompt_to_repeat":"alpha beta gamma"},
    "repeat:repeat_span": {"prompt_to_repeat":"alpha beta gamma delta","n_start":1,"n_end":3},
}


def mcq_good():
    out=[]
    qs=[
        "Art?",
        "Art history question?",
        "Modern art history question with context?",
        "Detailed modern art history question with broader historical context?",
    ]
    for i,q in enumerate(qs,1):
        out.append(f"Question {i}. {q}")
        for letter in "ABCDE":
            out.append(f"{letter}. option{letter.lower()}")
    return "\n".join(out)


def africa_reverse_good():
    return "\n".join(["Zimbabwe"]+[f"Y{n:03d}" for n in range(999,948,-1)])


def alphabet_story():
    words=[
        "Apple","Boat","Cat","Dog","Eagle","Fox","Goat","Horse","Ibis","Jaguar","Koala","Lion",
        "Mouse","Newt","Otter","Panda","Quail","Rabbit","Snake","Tiger","Urchin","Viper","Wolf","Xray","Yak","Zebra"
    ]
    return " ".join(f"{w} moves." for w in words)


def city_csv(rows=7):
    data=["ID,Country,City,Year,Count"]
    for i in range(1,rows+1):
        data.append(f"{i},Country{i},City{i},200{i%10},{i*10}")
    return "\n".join(data)


def special_csv(good=True):
    data=["ProductID,Category,Brand,Price,Stock"]
    for i in range(1,15):
        brand='"Brand!"' if good and i==1 else f"Brand{i}"
        data.append(f"{i},Cat{i},{brand},{i}.00,{i+2}")
    return "\n".join(data)


def quoted_tsv(good=True):
    header='\t'.join(f'"{x}"' for x in ["StudentID","Subject","Grade","Semester","Score"])
    rows=[header]
    for i in range(1,4):
        vals=[str(i),f"Subject{i}","A","Fall",str(90+i)]
        if good:
            rows.append('\t'.join(f'"{x}"' for x in vals))
        else:
            rows.append('\t'.join(vals))
    return "\n".join(rows)


def pair(instruction_id, desc):
    pairs={
        "count:word_count_range":("one two three","one two"),
        "count:unique_word_count":("one two three","one one"),
        "ratio:stop_words":("alpha beta","the and"),
        "ratio:sentence_type":("One. Two. Three?","One. Two?"),
        "ratio:sentence_balance":("One. Two? Three!","One. Two?"),
        "count:conjunctions":("and but","and and"),
        "count:person_names":("Emma Liam","Emma"),
        "ratio:overlap":("abcdef","xyzxyz"),
        "count:numbers":("1 2","1"),
        "words:alphabet":("apple boat cat dog","apple cat"),
        "words:vowel":("banana","aeiou"),
        "words:consonants":("tree grass","tree area"),
        "sentence:alliteration_increment":("cat dog. big blue cat.","cat dog. big cat."),
        "words:palindrome":(
            "level radar civic kayak refer level radar civic kayak refer",
            "level radar civic kayak refer level radar civic kayak"
        ),
        "count:punctuation":("a. b, c! d? e; f: g?!","a. b, c! d? e f: g?!"),
        "format:parentheses":("(([[{x}]]))","((x))"),
        "format:quotes":("\"'\"\"'\"","\"hello\""),
        "words:prime_lengths":("hi cat hello","four"),
        "format:options":("yes","perhaps"),
        "format:newline":("one\ntwo\nthree","one two\nthree"),
        "format:emoji":("Hello🙂. Bye🙂.","Hello. Bye🙂."),
        "ratio:sentence_words":("Cat. Dog. Pig.","Cat. Dogs. Pig."),
        "count:words_japanese":("hello 日本 world 日本","hello english world 日本"),
        "words:start_verb":("Running quickly.","The dog runs."),
        "words:repeats":("one two three","one one"),
        "sentence:keyword":("First sentence. This target appears.","Target appears first. Second sentence."),
        "count:pronouns":("I see you.","Alice sees Bob."),
        "words:odd_even_syllables":("cat table dog paper","cat dog"),
        "words:last_first":("Alpha beta. Beta gamma.","Alpha beta. Gamma delta."),
        "words:paragraph_last_first":("Alpha middle alpha.\n\nBeta middle beta.","Alpha middle alpha.\n\nBeta middle gamma."),
        "sentence:increment":("One. One two. One two three.","One. One two three."),
        "words:no_consecutive":("alpha beta cat","alpha apple"),
        "format:line_indent":("a\n b\n  c"," a\nb"),
        "format:quote_unquote":('He said "hello" and left.','He said "hello"'),
        "format:list":("### one\n### two","### one"),
        "format:thesis":("<i>Thesis</i> supporting text","<i>Thesis</i>"),
        "format:sub-bullets":("* item\n- sub\n* item2\n- sub2","* item\n* item2"),
        "format:no_bullets_bullets":("One. Two.\n* a\n* b","One.\n* a\n* b"),
        "custom:multiples":("14, 21, 28, 35, 42, 49","14, 21, 28, 35, 42"),
        "custom:mcq_count_length":(mcq_good(),"Question 1. Art?\nA. a\nB. b\nC. c\nD. d\nE. e"),
        "custom:reverse_newline":(africa_reverse_good(),"Zimbabwe\nY999\nY997\nY998"),
        "custom:word_reverse":("eagle bald","bald eagle"),
        "custom:character_reverse":("elgae dlab","bald eagle"),
        "custom:sentence_alphabet":(alphabet_story(),alphabet_story().replace("Boat moves.","Apple moves.",1)),
        "custom:european_capitals_sort":(
            "Reykjavik, Helsinki, Oslo, Tallinn, Stockholm, Riga, Moscow, Copenhagen, Vilnius, Minsk, Dublin, Berlin, Amsterdam, Warsaw, London, Brussels, Prague, Luxembourg, Paris, Vienna, Bratislava, Budapest, Vaduz, Chisinau, Bern, Ljubljana, Zagreb",
            "Reykjavik, Helsinki, Oslo"
        ),
        "custom:csv_city":(city_csv(7),city_csv(6)),
        "custom:csv_special_character":(special_csv(True),special_csv(False)),
        "custom:csv_quotes":(quoted_tsv(True),quoted_tsv(False)),
        "custom:date_format_list":("1800-01-01, 1801-02-02","1800/01/01"),
        "count:keywords_multiple":(
            "alpha beta beta gamma gamma gamma delta delta delta delta delta epsilon epsilon epsilon epsilon epsilon epsilon epsilon",
            "alpha beta beta gamma gamma gamma delta delta delta delta delta epsilon epsilon epsilon epsilon epsilon epsilon"
        ),
        "words:keywords_specific_position":("one target three.","target one three."),
        "words:words_position":("one target middle target end","one target middle other end"),
        "repeat:repeat_change":("omega beta gamma","alpha beta gamma"),
        "repeat:repeat_simple":(desc,desc+" extra"),
        "repeat:repeat_span":("beta gamma","alpha beta"),
        "format:title_case":("Alpha Beta Gamma","alpha Beta"),
        "format:output_template":("My Answer: x My Conclusion: y Future Outlook: z","My Answer: x My Conclusion: y"),
        "format:no_whitespace":("abc","a b"),
    }
    return pairs[instruction_id]


def run():
    registry=instructions_registry.INSTRUCTION_DICT
    if len(registry)!=58:
        return {"status":"FAIL_CLOSED","reason":"CHECKER_COUNT_CHANGED","count":len(registry)}
    rows=[]
    for idx,(instruction_id,cls) in enumerate(registry.items()):
        inst=cls(instruction_id)
        desc=inst.build_description(**ARGS.get(instruction_id,{}))
        good,bad=pair(instruction_id,desc)
        good_direct=inst.check_following(good)
        bad_direct=inst.check_following(bad)
        args=inst.get_instruction_args() or {}
        good_inp=evaluation_lib.InputExample(
            key=idx,instruction_id_list=[instruction_id],
            prompt="Synthetic boundary preflight only.",kwargs=[dict(args)]
        )
        bad_inp=evaluation_lib.InputExample(
            key=idx,instruction_id_list=[instruction_id],
            prompt="Synthetic boundary preflight only.",kwargs=[dict(args)]
        )
        good_strict=evaluation_lib.test_instruction_following_strict(good_inp,good).follow_instruction_list[0]
        bad_strict=evaluation_lib.test_instruction_following_strict(bad_inp,bad).follow_instruction_list[0]
        row={
            "instruction_id":instruction_id,
            "good_direct":bool(good_direct),
            "bad_direct":bool(bad_direct),
            "good_strict":bool(good_strict),
            "bad_strict":bool(bad_strict),
            "pass":bool(good_direct and not bad_direct and good_strict and not bad_strict),
        }
        rows.append(row)
    failed=[x for x in rows if not x["pass"]]
    return {
        "schema":"PROJECT_BRAIN_LIVEBENCH_IF_58_CHECKER_SYNTHETIC_BOUNDARY_PREFLIGHT_V1",
        "status":"PASS" if not failed else "FAIL_CLOSED",
        "checker_count":len(rows),
        "passed":len(rows)-len(failed),
        "failed":failed,
        "terminal_case_content_read":0,
        "rows":rows,
    }


if __name__=="__main__":
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    raise SystemExit(0 if out["status"]=="PASS" else 1)
