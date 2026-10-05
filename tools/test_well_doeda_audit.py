"""Missing source, candidate, and corpus evidence must fail the compound gate."""
import copy
import unittest

import well_doeda_audit as audit
import well_doeda_broad as broad
import well_doeda_corpora as corpora
import well_doeda_runtime as runtime


class SourceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = audit.read(audit.SOURCE)

    def test_complete_source(self):
        self.assertEqual(audit.inspect_source(self.source), (44, 46, 39, 8))

    def test_changed_compound_classification(self):
        changed = copy.deepcopy(self.source)
        changed["primary_source"]["short_excerpt"] = "suffix"
        with self.assertRaises(AssertionError):
            audit.inspect_source(changed)

    def test_missing_native_homonym(self):
        changed = copy.deepcopy(self.source)
        del changed["complete_native_entries"]["krdict:48214"]
        changed["native_sha256"] = audit.digest(changed["complete_native_entries"])
        with self.assertRaises(AssertionError):
            audit.inspect_source(changed)

    def test_missing_original_word(self):
        changed = copy.deepcopy(self.source)
        changed["before"]["raw"]["words"].pop("잘된다고")
        with self.assertRaises(AssertionError):
            audit.inspect_source(changed)

    def test_rewritten_gold(self):
        changed = copy.deepcopy(self.source)
        row = next(r for c in changed["corpora"] for r in c["rows"])
        row["original_row"][2] = "잘되+ㄴ다고"
        with self.assertRaises(AssertionError):
            audit.inspect_source(changed)

    def test_omitted_stable_control(self):
        changed = copy.deepcopy(self.source)
        changed["cases"].pop()
        with self.assertRaises(AssertionError):
            audit.inspect_source(changed)


class CapturedEvidenceGuards(unittest.TestCase):
    def test_complete_captures(self):
        self.assertEqual(audit.inspect_comparison(audit.read(audit.SOURCE),
            audit.read(audit.ROOT / "docs/well-doeda-diagnostics.json.gz")), (117, 39))
        self.assertEqual(broad.inspect(audit.read(broad.REPORT)), (18, 5))
        self.assertEqual(corpora.inspect(audit.read(corpora.REPORT)), (66570, 32096, 2))
        self.assertEqual(runtime.inspect(audit.read(runtime.REPORT)), (92, 78, 39, 6))

    def test_missing_unicode_cache_run(self):
        report = audit.read(audit.ROOT / "docs/well-doeda-diagnostics.json.gz")
        del report["runs"]["compatible"]["NFD-uncached"]
        with self.assertRaises(AssertionError):
            audit.inspect_comparison(audit.read(audit.SOURCE), report)

    def test_missing_broad_stream(self):
        report = audit.read(broad.REPORT)
        report["comparisons"].pop()
        with self.assertRaises(AssertionError):
            broad.inspect(report)

    def test_lost_original_corpus_word(self):
        report = audit.read(corpora.REPORT)
        del report["after_words"]["잘되고"]
        with self.assertRaises(AssertionError):
            corpora.inspect(report)

    def test_incorrect_compound_ownership(self):
        report = audit.read(runtime.REPORT)
        batch = report["api"]["batches"][0]["response"]
        for record, orders in zip(batch["records"], batch["breakdowns"], strict=True):
            if not record.get("analysis"):
                continue
            for analysis, order in zip(record["analysis"]["analyses"], orders, strict=True):
                if audit.RULE in analysis["rules"]:
                    order[1] = {"morpheme": 0}
                    with self.assertRaises(AssertionError):
                        runtime.inspect(report)
                    return
        self.fail("Expected a compound in the captured API")


if __name__ == "__main__":
    unittest.main()
