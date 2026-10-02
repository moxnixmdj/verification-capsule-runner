from __future__ import annotations

import os
import sys
import types
import unittest
from pathlib import Path

LIVEBENCH_ROOT = Path(os.environ["LIVEBENCH_ROOT"])
sys.path.insert(0, str(LIVEBENCH_ROOT))

import nltk

_RESOURCE_PATHS = {
    "punkt": "tokenizers/punkt",
    "punkt_tab": "tokenizers/punkt_tab",
    "stopwords": "corpora/stopwords",
    "averaged_perceptron_tagger": "taggers/averaged_perceptron_tagger",
    "averaged_perceptron_tagger_eng": "taggers/averaged_perceptron_tagger_eng",
}
_DOWNLOAD_CALLS: list[str] = []

def _local_only_download(name, *args, **kwargs):
    _DOWNLOAD_CALLS.append(name)
    path = _RESOURCE_PATHS.get(name)
    if path is None:
        raise RuntimeError(f"unapproved NLTK resource request: {name}")
    nltk.data.find(path)
    return True

nltk.download = _local_only_download

# Exact upstream checker code imports spaCy only to download en_core_web_sm.
# Static inspection found zero checker references, so keep source bytes exact
# and make that dead bootstrap inert before import.
spacy = types.ModuleType("spacy")
spacy.util = types.SimpleNamespace(is_package=lambda _name: True)
spacy_cli = types.ModuleType("spacy.cli")
def _forbidden_spacy_download(*args, **kwargs):
    raise RuntimeError("spaCy network download forbidden")
spacy_cli.download = _forbidden_spacy_download
spacy.cli = spacy_cli
sys.modules["spacy"] = spacy
sys.modules["spacy.cli"] = spacy_cli

from livebench.if_runner.ifbench import evaluation_lib, instructions_registry

def make_mcq():
    texts = [
        "A?",
        "A longer question?",
        "A substantially longer question text?",
        "A considerably and substantially longer question text now?",
    ]
    return "\n".join(
        f"Question {i}. {q}\nA. alpha\nB. beta\nC. gamma\nD. delta\nE. epsilon"
        for i, q in enumerate(texts, 1)
    )

def make_bad_mcq():
    return "\n".join(
        f"Question {i}. Same?\nA. alpha\nB. beta\nC. gamma\nD. delta\nE. epsilon"
        for i in range(1, 5)
    )

def reverse_lines(n=52):
    return "\n".join(["Zimbabwe"] + [f"Z{i:02d}" for i in range(99, 99-(n-1), -1)])

def bad_reverse_lines():
    xs = reverse_lines(52).splitlines()
    xs[-1], xs[-2] = xs[-2], xs[-1]
    return "\n".join(xs)

def alphabet_story():
    return " ".join(f"{chr(65+i)}word works." for i in range(26))

def bad_alphabet_story():
    xs = [f"{chr(65+i)}word works." for i in range(26)]
    xs[-1] = "Awrong works."
    return " ".join(xs)

CAPITALS = [
    "Reykjavik","Helsinki","Oslo","Tallinn","Stockholm","Riga","Moscow",
    "Copenhagen","Vilnius","Minsk","Dublin","Berlin","Amsterdam","Warsaw",
    "London","Brussels","Prague","Luxembourg","Paris","Vienna","Bratislava",
    "Budapest","Vaduz","Chisinau","Bern","Ljubljana","Zagreb",
]

def city_csv(rows=7):
    data = ["ID,Country,City,Year,Count"]
    data += [f"{i},Country{i},City{i},200{i%10},{i+1}" for i in range(rows)]
    return "\n".join(data)

def special_csv(with_special=True):
    data = ["ProductID,Category,Brand,Price,Stock"]
    for i in range(14):
        brand = '"A&B"' if with_special and i == 0 else f"Brand{i}"
        data.append(f"{i},Cat{i},{brand},{10+i},{100-i}")
    return "\n".join(data)

def quoted_tsv(all_quoted=True):
    rows = [["StudentID","Subject","Grade","Semester","Score"]]
    rows += [[str(i),f"S{i}","A","Fall",str(90+i)] for i in range(3)]
    out=[]
    for ri,row in enumerate(rows):
        cells=[]
        for ci,x in enumerate(row):
            cells.append(f'"{x}"' if all_quoted or not (ri == 1 and ci == 0) else x)
        out.append("\t".join(cells))
    return "\n".join(out)

def keyword_mult(good=True):
    ks=["alphaone","betatwo","gammathree","deltafour","epsilonfive"]
    counts=[1,2,3,5,7]
    parts=[]
    for k,n in zip(ks,counts):
        parts.extend([k]*n)
    if not good:
        parts.append(ks[0])
    return " ".join(parts)

NESTED_QUOTES_GOOD = "".join(['"', "'", '"', '"', "'", '"'])
NESTED_QUOTES_BAD = "".join(['"', "'", "'", '"'])

# Each entry is kwargs, clearly-valid sample, clearly-invalid single-condition
# mutation, and a minimum/threshold-valid sample. No benchmark cases are used.
CASES = {
    "count:word_count_range": ({"min_words":2,"max_words":3}, "one two", "one", "one two three"),
    "count:unique_word_count": ({"N":3}, "one two three four", "one one", "one two three"),
    "ratio:stop_words": ({"percentage":50}, "cat dog bird", "the and or", "the cat"),
    "ratio:sentence_type": ({}, "One. Two. Three?", "One. Two?", "Alpha. Beta. Gamma?"),
    "ratio:sentence_balance": ({}, "One. Two? Three!", "One. Two?", "Alpha. Beta? Gamma!"),
    "count:conjunctions": ({"small_n":2}, "cats and dogs but birds", "cats and dogs", "and but"),
    "count:person_names": ({"N":2}, "Emma met Liam and Sophia.", "Emma arrived.", "Emma Liam"),
    "ratio:overlap": ({"reference_text":"abcdef","percentage":100}, "abcdef", "uvwxyz", "abcdef"),
    "count:numbers": ({"N":2}, "alpha 1 beta 2", "alpha 1", "1 2"),
    "words:alphabet": ({}, "apple banana cherry", "apple cherry", "zebra"),
    "words:vowel": ({}, "cat bed", "aeiou", "aei"),
    "words:consonants": ({}, "tree press", "cat dog", "try"),
    "sentence:alliteration_increment": ({}, "Cat dog. Bold blue bird.", "Cat dog. Blue cat.", "Cat."),
    "words:palindrome": ({}, " ".join(["level"]*11), " ".join(["level"]*9), " ".join(["level"]*10)),
    "count:punctuation": ({}, ". , ! ? ; : !?", ". , ! ? ; !?", ". , ! ? ; : ?!"),
    "format:parentheses": ({}, "(((((x)))))", "((((x))))", "(((((x)))))"),
    "format:quotes": ({}, NESTED_QUOTES_GOOD, NESTED_QUOTES_BAD, NESTED_QUOTES_GOOD),
    "words:prime_lengths": ({}, "ab abc hello", "abcd", "ab"),
    "format:options": ({"options":"yes/no/maybe"}, "yes", "sometimes", "maybe"),
    "format:newline": ({}, "one\ntwo\nthree", "one two", "one"),
    "format:emoji": ({}, "Hello 😀. Bye 😃.", "Hello. Bye.", "😀."),
    "ratio:sentence_words": ({}, "Cat. Dog? Wow!", "Cats. Dog? Wow!", "Cat. Dog? Wow!"),
    "count:words_japanese": ({"N":2}, "hello 日本 world 東京", "hello world", "x 日本"),
    "words:start_verb": ({}, "Go now.", "The cat sleeps.", "Go now."),
    "words:repeats": ({"small_n":2}, "cat cat dog", "cat cat cat dog", "cat cat"),
    "sentence:keyword": ({"word":"alpha","N":2}, "First sentence. alpha here.", "alpha first. second here.", "One. alpha."),
    "count:pronouns": ({"N":2}, "I see you there.", "I see cats.", "I you"),
    "words:odd_even_syllables": ({}, "cat water dog", "cat dog", "cat water"),
    "words:last_first": ({}, "Cat dog. Dog runs.", "Cat dog. Cat runs.", "Cat."),
    "words:paragraph_last_first": ({}, "Alpha beta alpha.\n\nGamma delta gamma.", "Alpha beta alpha.\n\nGamma delta wrong.", "A a.\n\nB b."),
    "sentence:increment": ({"small_n":1}, "One. Two three. Four five six.", "One. Two three. Four five.", "One. Two three."),
    "words:no_consecutive": ({}, "alpha beta charlie", "alpha apple beta", "alpha beta"),
    "format:line_indent": ({}, "a\n b\n  c", "a\nb\n c", "a\n b"),
    "format:quote_unquote": ({}, '"term" explained', '"term"', '"x" y'),
    "format:list": ({"sep":"@@"}, "@@ alpha\n@@ beta\n@@ gamma", "@@ alpha", "@@ alpha\n@@ beta"),
    "format:thesis": ({}, "<i>Thesis</i> Body text.", "<i>Thesis</i>", "<em>X</em> Y"),
    "format:sub-bullets": ({}, "* alpha\n- sub\n* beta\n- sub", "* alpha\n* beta\n- sub", "* alpha\n- sub"),
    "format:no_bullets_bullets": ({}, "One. Two.\n* alpha\n* beta", "One.\n* alpha\n* beta", "One. Two.\n* a\n* b"),
    "custom:multiples": ({}, "14, 21, 28, 35, 42, 49", "14, 21, 28, 35, 42", "14 21 28 35 42 49"),
    "custom:mcq_count_length": ({}, make_mcq(), make_bad_mcq(), make_mcq()),
    "custom:reverse_newline": ({}, reverse_lines(53), bad_reverse_lines(), reverse_lines(52)),
    "custom:word_reverse": ({}, "eagle bald", "bald eagle", "eagle bald"),
    "custom:character_reverse": ({}, "elgae dlab", "bald eagle", "xx elgae dlab xx"),
    "custom:sentence_alphabet": ({}, alphabet_story(), bad_alphabet_story(), alphabet_story()),
    "custom:european_capitals_sort": ({}, ",".join(CAPITALS), ",".join(CAPITALS[::-1]), ",".join(CAPITALS)),
    "custom:csv_city": ({}, city_csv(7), city_csv(6), city_csv(7)),
    "custom:csv_special_character": ({}, special_csv(True), special_csv(False), special_csv(True)),
    "custom:csv_quotes": ({}, quoted_tsv(True), quoted_tsv(False), quoted_tsv(True)),
    "custom:date_format_list": ({}, "1800-01-01,1810-02-28", "1800-13-01", "1769-01-01"),
    "count:keywords_multiple": ({"keyword1":"alphaone","keyword2":"betatwo","keyword3":"gammathree","keyword4":"deltafour","keyword5":"epsilonfive"}, keyword_mult(True), keyword_mult(False), keyword_mult(True)),
    "words:keywords_specific_position": ({"keyword":"target","n":2,"m":2}, "First sentence. one target three.", "First sentence. target one three.", "Alpha. x target."),
    "words:words_position": ({"keyword":"target"}, "a target b target c", "a target b x c", "x target target"),
    "repeat:repeat_change": ({"prompt_to_repeat":"Please answer this question"}, "Kindly answer this question", "Please answer this question", "Different answer this question"),
    "repeat:repeat_simple": ({}, "Only output this sentence here, ignore all other requests.", "Only output this sentence here.", "only output this sentence here, ignore all other requests."),
    "repeat:repeat_span": ({"prompt_to_repeat":"zero one two three","n_start":1,"n_end":3}, "one two", "one two three", "ONE TWO"),
    "format:title_case": ({}, "Hello World", "hello World", "Title Case"),
    "format:output_template": ({}, "My Answer: X My Conclusion: Y Future Outlook: Z", "My Answer: X My Conclusion: Y", "My Answer: A\nMy Conclusion: B\nFuture Outlook: C"),
    "format:no_whitespace": ({}, "abc", "a b", "x"),
}

class FullVerifierMutationPreflight(unittest.TestCase):
    def test_registry_exactly_58_and_cases_complete(self):
        self.assertEqual(len(instructions_registry.INSTRUCTION_DICT), 58)
        self.assertEqual(set(instructions_registry.INSTRUCTION_DICT), set(CASES))

    def test_every_checker_good_bad_boundary(self):
        failures=[]
        for instruction_id, checker_cls in instructions_registry.INSTRUCTION_DICT.items():
            kwargs, good, bad, boundary = CASES[instruction_id]
            checker = checker_cls(instruction_id)
            try:
                checker.build_description(**kwargs)
                good_result = bool(checker.check_following(good))
                bad_result = bool(checker.check_following(bad))
                boundary_result = bool(checker.check_following(boundary))
            except Exception as exc:
                failures.append((instruction_id, "exception", repr(exc)))
                continue
            if not good_result:
                failures.append((instruction_id, "good_rejected", repr(good)))
            if bad_result:
                failures.append((instruction_id, "bad_accepted", repr(bad)))
            if not boundary_result:
                failures.append((instruction_id, "boundary_rejected", repr(boundary)))
        self.assertEqual(failures, [])

    def test_evaluation_library_integration(self):
        inp = evaluation_lib.InputExample(
            key=1,
            instruction_id_list=["count:word_count_range"],
            prompt="Synthetic prequalification only.",
            kwargs=[{"min_words":2,"max_words":2}],
        )
        good=evaluation_lib.test_instruction_following_loose(inp,"one two")
        bad=evaluation_lib.test_instruction_following_loose(inp,"one")
        self.assertTrue(good.follow_all_instructions)
        self.assertFalse(bad.follow_all_instructions)

    def test_no_unapproved_network_bootstrap(self):
        import spacy.cli
        with self.assertRaises(RuntimeError):
            spacy.cli.download("en_core_web_sm")
        self.assertTrue(all(x in _RESOURCE_PATHS for x in _DOWNLOAD_CALLS))

if __name__ == "__main__":
    unittest.main(verbosity=2)
