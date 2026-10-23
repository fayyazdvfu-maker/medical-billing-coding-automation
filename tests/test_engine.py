import copy
import json
import unittest
from pathlib import Path
from billing_automation import validate

ROOT = Path(__file__).resolve().parents[1]


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.claim = json.loads((ROOT / "examples/claim.json").read_text())
        self.rules = json.loads((ROOT / "examples/rules.json").read_text())
        self.catalog = json.loads((ROOT / "examples/catalog.json").read_text())

    def ids(self, **kwargs):
        return [f.rule_id for f in validate(self.claim, kwargs.get("rules", self.rules), kwargs.get("catalog", self.catalog))]

    def test_valid_fixture_and_no_mutation(self):
        before = copy.deepcopy(self.claim)
        self.assertEqual(self.ids(), [])
        self.assertEqual(self.claim, before)

    def test_payer_specific_rule_and_source(self):
        self.claim["lines"][0]["modifiers"] = []
        finding = validate(self.claim, self.rules, self.catalog)[0]
        self.assertEqual(finding.rule_id, "DEMO_MODIFIER_RULE")
        self.assertEqual(finding.source, self.rules[0]["source"])
        self.claim["payer"] = "OTHER_PAYER"
        self.assertNotIn("DEMO_MODIFIER_RULE", self.ids())

    def test_effective_dates_inclusive_and_expiry(self):
        self.claim["lines"][0]["modifiers"] = []
        for day in ("2026-01-01", "2026-12-31"):
            self.claim["date_of_service"] = day
            self.assertIn("DEMO_MODIFIER_RULE", self.ids())
        self.claim["date_of_service"] = "2027-01-01"
        self.assertNotIn("DEMO_MODIFIER_RULE", self.ids())
        self.assertIn("CODE_DATE_RANGE", self.ids())

    def test_boolean_and_out_of_range_pointers_rejected(self):
        for pointers in ([True], [0], [2], [], "1"):
            self.claim["lines"][0]["diagnosis_pointers"] = pointers
            self.assertIn("DIAGNOSIS_POINTER", self.ids())

    def test_nonreportable_and_unknown_catalog_codes(self):
        self.catalog["HCPCS"]["DEMO_PROC"]["reportable"] = False
        self.assertIn("CODE_NOT_REPORTABLE", self.ids())
        self.claim["lines"][0]["procedure_code"] = "UNKNOWN"
        self.assertIn("CODE_NOT_IN_CATALOG", self.ids())

    def test_duplicate_modifiers_and_missing_context(self):
        self.claim["lines"][0]["modifiers"] *= 2
        self.assertIn("DUPLICATE_MODIFIER", self.ids())
        self.claim["date_of_service"] = "invalid"
        self.claim["payer"] = None
        self.assertIn("SERVICE_DATE", self.ids())
        self.assertIn("PAYER_REQUIRED", self.ids())
        self.assertNotIn("DEMO_MODIFIER_RULE", self.ids())

    def test_missing_catalog_is_not_silent_success(self):
        self.assertIn("CATALOG_NOT_SUPPLIED", self.ids(catalog=None))

    def test_missing_source_and_unsupported_rule_are_not_applied(self):
        self.rules[0]["source"] = ""
        self.assertTrue(any(f.severity == "review" for f in validate(self.claim, self.rules, self.catalog)))
        self.rules[0]["type"] = "deny_every_payer"
        self.assertTrue(any("not applied" in f.message for f in validate(self.claim, self.rules, self.catalog)))

    def test_required_field(self):
        rule = dict(self.rules[0], type="required_field", field="test_reference")
        self.assertIn("DEMO_MODIFIER_RULE", self.ids(rules=[rule]))
        self.claim["lines"][0]["test_reference"] = "synthetic reference"
        self.assertNotIn("DEMO_MODIFIER_RULE", self.ids(rules=[rule]))


if __name__ == "__main__":
    unittest.main()
