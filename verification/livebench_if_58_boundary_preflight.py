from __future__ import annotations

import importlib.util
import inspect
import re
import unittest

from livebench.if_runner.ifbench import instructions, instructions_registry

AUTHOR_TEST = "/tmp/ifbench/instructions_test_reuse.py"

spec = importlib.util.spec_from_file_location("ifbench_author_tests_reuse", AUTHOR_TEST)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

test_cls = mod.InstructionsTest
registry = instructions_registry.INSTRUCTION_DICT
assert len(registry) == 58, len(registry)
registry_class_names = {cls.__name__ for cls in registry.values()}
assert len(registry_class_names) == 58, len(registry_class_names)

selected_methods = []
author_boundary_classes = set()

for name in dir(test_cls):
    if not name.startswith("test_"):
        continue
    method = getattr(test_cls, name)
    try:
        src = inspect.getsource(method)
    except (OSError, TypeError):
        continue
    referenced = set(re.findall(r"instructions\.([A-Za-z0-9_]+)\(", src))
    relevant = referenced & registry_class_names
    if not relevant:
        continue
    if "self.assertTrue" in src and "self.assertFalse" in src:
        selected_methods.append(name)
        author_boundary_classes.update(relevant)

expected_author_boundary = {
    "WordCountRangeChecker","StopWordPercentageChecker","PersonNameCountChecker",
    "NGramOverlapChecker","NumbersCountChecker","AlphabetLoopChecker",
    "ConsonantClusterChecker","IncrementingAlliterationChecker","PalindromeChecker",
    "PunctuationCoverChecker","NestedParenthesesChecker","NestedQuotesChecker",
    "PrimeLengthsChecker","OptionsResponseChecker","NewLineWordsChecker",
    "EmojiSentenceChecker","CharacterCountUniqueWordsChecker","StartWithVerbChecker",
    "LimitedWordRepeatChecker","IncludeKeywordChecker","PronounCountChecker",
    "AlternateParitySyllablesChecker","LastWordFirstNextChecker",
    "ParagraphLastFirstWordMatchChecker","IncrementingWordCountChecker",
    "NoConsecutiveFirstLetterChecker","IndentStairsChecker","QuoteExplanationChecker",
    "SpecialBulletPointsChecker","SubBulletPointsChecker","SomeBulletPointsChecker",
    "PrintMultiplesChecker","MultipleChoiceQuestionsChecker","ReverseNewlineChecker",
    "WordReverseOrderChecker","CharacterReverseOrderChecker","SentenceAlphabetChecker",
    "EuropeanCapitalsSortChecker","CityCSVChecker","SpecialCharacterCSVChecker",
    "QuotesCSVChecker","DateFormatListChecker","KeywordsMultipleChecker",
    "WordsPositionChecker","RepeatChangeChecker","RepeatSpanChecker","TitleCaseChecker",
}
assert author_boundary_classes == expected_author_boundary, (
    sorted(expected_author_boundary-author_boundary_classes),
    sorted(author_boundary_classes-expected_author_boundary),
)

suite = unittest.TestSuite(test_cls(name) for name in selected_methods)
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful(), (result.failures, result.errors)

supplemental_classes = set()

def pair(cls, instruction_id, build_kwargs, good, bad):
    inst = cls(instruction_id)
    inst.build_description(**build_kwargs)
    good_out = inst.check_following(good)
    bad_out = inst.check_following(bad)
    assert good_out is True, (cls.__name__, "good rejected", good)
    assert bad_out is False, (cls.__name__, "bad accepted", bad)
    supplemental_classes.add(cls.__name__)

pair(
    instructions.UniqueWordCountChecker,
    "count:unique_word_count",
    {"N": 5},
    "one two three four five",
    "one two three four four",
)
pair(
    instructions.SentTypeRatioChecker,
    "ratio:sentence_type",
    {},
    "One. Two. Three?",
    "One. Two. Three.",
)
pair(
    instructions.SentBalanceChecker,
    "ratio:sentence_balance",
    {},
    "One. Two? Three!",
    "One. Two? Three.",
)
pair(
    instructions.ConjunctionCountChecker,
    "count:conjunctions",
    {"small_n": 3},
    "alpha and beta but gamma or delta",
    "alpha and beta but gamma",
)
pair(
    instructions.ItalicsThesisChecker,
    "format:thesis",
    {},
    "<i>Thesis.</i> Body.",
    "Thesis. Body.",
)
pair(
    instructions.KeywordSpecificPositionChecker,
    "words:keywords_specific_position",
    {"keyword": "test", "n": 1, "m": 1},
    "Test is here.",
    "Here test is.",
)
pair(
    instructions.ThreeVowelChecker,
    "words:vowel",
    {},
    "red sky",
    "aeiou",
)
pair(
    instructions.NthWordJapaneseChecker,
    "count:words_japanese",
    {"N": 2},
    "alpha 日本 beta 日本",
    "alpha beta gamma 日本",
)
repeat = instructions.RepeatSimpleChecker("repeat:repeat_simple")
repeat.build_description()
repeat_good = repeat._description_pattern
assert repeat.check_following(repeat_good) is True
assert repeat.check_following(repeat_good + " extra") is False
supplemental_classes.add("RepeatSimpleChecker")

pair(
    instructions.OutputTemplateChecker,
    "format:output_template",
    {},
    "My Answer: A My Conclusion: C Future Outlook: F",
    "My Answer: A My Conclusion: C",
)
pair(
    instructions.NoWhitespaceChecker,
    "format:no_whitespace",
    {},
    "NoWhitespace",
    "Has whitespace",
)

expected_supplemental = registry_class_names - expected_author_boundary
assert supplemental_classes == expected_supplemental, (
    sorted(expected_supplemental-supplemental_classes),
    sorted(supplemental_classes-expected_supplemental),
)
assert len(author_boundary_classes | supplemental_classes) == 58

print({
    "status": "PASS",
    "author_positive_negative_checker_count": len(author_boundary_classes),
    "supplemental_positive_negative_checker_count": len(supplemental_classes),
    "total_checker_count": len(author_boundary_classes | supplemental_classes),
    "terminal_case_content_read": 0,
})
