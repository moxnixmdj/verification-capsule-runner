import unittest

from controller_fast import semantic_success_errors


class BuilderSemanticSuccessTests(unittest.TestCase):
    def test_exit_zero_without_sentinel_fails(self):
        errors=semantic_success_errors({"success_sentinel":"DONE"},{"exit_code":0,"stdout":"","stderr":""})
        self.assertIn("SUCCESS_SENTINEL_NOT_OBSERVED",errors)

    def test_freecad_exception_with_exit_zero_fails(self):
        errors=semantic_success_errors(
            {"success_sentinel":"DONE"},
            {"exit_code":0,"stdout":"DONE\n","stderr":"Exception while processing file: /app/answer.py [boom]\n"},
        )
        self.assertTrue(any(e.startswith("FATAL_STDERR_PATTERN:") for e in errors))

    def test_clean_semantic_success_passes(self):
        self.assertEqual(
            semantic_success_errors(
                {"success_sentinel":"BUILD_OK"},
                {"exit_code":0,"stdout":"... BUILD_OK ...","stderr":""},
            ),
            [],
        )


if __name__=="__main__":
    unittest.main()
