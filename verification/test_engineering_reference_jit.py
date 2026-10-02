import pathlib, unittest
from engineering_reference_resolver import (
    validate_gdt_symbols, validate_gdt_modifiers, validate_roughness_grades, resolve
)
DATA=pathlib.Path("/tmp/engineering-reference-data/data")

class VerifyJITEngineeringReference(unittest.TestCase):
    def text(self,name):
        return (DATA/name).read_text(encoding="utf-8")

    def test_gdt_symbols_actual_pinned_data(self):
        v=validate_gdt_symbols(self.text("gdt-symbols.csv"))
        self.assertEqual(v["status"],"VALIDATED")
        self.assertEqual(v["row_count"],14)
        r=resolve(v,"Position")
        self.assertEqual(r["status"],"RESOLVED")
        self.assertEqual(r["row"]["symbol"],"⌖")

    def test_symbol_lookup_by_unicode_glyph(self):
        v=validate_gdt_symbols(self.text("gdt-symbols.csv"))
        r=resolve(v,"⏥")
        self.assertEqual(r["row"]["characteristic"],"Flatness")

    def test_modifiers_actual_pinned_data(self):
        v=validate_gdt_modifiers(self.text("gdt-modifiers.csv"))
        self.assertEqual(v["status"],"VALIDATED")
        self.assertEqual(v["row_count"],15)
        self.assertEqual(resolve(v,"MMC")["row"]["meaning"],"maximum material condition")

    def test_roughness_actual_pinned_data(self):
        v=validate_roughness_grades(self.text("surface-roughness-grades.csv"))
        self.assertEqual(v["status"],"VALIDATED")
        self.assertEqual(v["row_count"],12)
        self.assertEqual(float(resolve(v,"N7")["row"]["ra_um"]),1.6)

    def test_corrupt_codepoint_fails_closed(self):
        text=self.text("gdt-symbols.csv").replace("U+23E4","U+23E5",1)
        self.assertEqual(validate_gdt_symbols(text)["status"],"FAIL_CLOSED")

    def test_unknown_reference_does_not_fuzzy_guess(self):
        v=validate_gdt_symbols(self.text("gdt-symbols.csv"))
        self.assertEqual(resolve(v,"probably position-ish")["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
