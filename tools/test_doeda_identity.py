"""Reject missing per-reading identity evidence and changes to frozen candidates."""

import unittest
from copy import deepcopy

from doeda_identity_audit import FIXTURE
from doeda_identity_audit import REPORT as PREFLIGHT
from doeda_identity_diagnostics import REPORT, inspect_record
from doeda_identity_implementation import inspect as inspect_table
from lexical_nada_audit import ROOT, read


class IdentityEvidenceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source, report, cls.fixture = read(PREFLIGHT), read(REPORT), read(FIXTURE)
        cls.heads = {h["base"]: h for h in cls.fixture["heads"]}
        cls.entries = source["complete_native_entries"]
        for before, after in zip(
            source["before_streams"]["raw"], report["after_streams"]["raw"], strict=True
        ):
            if after["surface"] == "가공돼요":
                cls.before, cls.after = before, after
                break
        else:
            raise AssertionError("frozen reference word missing")
        cls.reading_index = next(
            i
            for i, r in enumerate(cls.after["dictionary"]["readings"])
            if any(
                e.get("derivational_identity")
                for l in r["lemmas"]
                for e in l["entries"]
            )
        )
        cls.table = (ROOT / "src/doeda_identity.rs").read_text()

    def check(self, after):
        return inspect_record(self.before, after, self.heads, self.entries)

    def identity_entry(self, after):
        return after["dictionary"]["readings"][self.reading_index]["lemmas"][0][
            "entries"
        ][0]

    def test_frozen_record_and_sorted_table_pass(self):
        self.assertTrue(self.check(self.after))
        inspect_table(self.table, self.fixture)

    def test_each_reading_requires_its_evidence(self):
        after = deepcopy(self.after)
        del self.identity_entry(after)["derivational_identity"]
        with self.assertRaises(AssertionError):
            self.check(after)

    def test_borrowed_origins_sources_and_owned_indices_fail(self):
        for field, value in (
            ("relation", "unknown"),
            ("expected_origins", ["反感"]),
            ("whole_entries", ["krdict:89858"]),
            ("whole_origins_complete", False),
            ("morpheme_index", 1),
        ):
            after = deepcopy(self.after)
            self.identity_entry(after)["derivational_identity"][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.check(after)

    def test_native_origins_must_be_present_and_exact(self):
        for missing in (True, False):
            after = deepcopy(self.after)
            slot = next(
                s
                for s in after["dictionary"]["lemmas"]
                if s["lemma"] == {"text": "가공", "kind": "nominal"}
            )
            entry = slot["entries"][0]
            if missing:
                del entry["origins"]
            else:
                entry["origins"] = ["反感"]
            with (
                self.subTest(missing=missing),
                self.assertRaises((AssertionError, KeyError)),
            ):
                self.check(after)

    def test_candidate_and_grammar_changes_fail(self):
        for field in ("candidate", "status", "conflict", "order"):
            after = deepcopy(self.after)
            if field == "candidate":
                after["analysis"]["analyses"].pop()
            elif field == "status":
                self.identity_entry(after)["status"] = "incompatible"
            elif field == "conflict":
                self.identity_entry(after)["conflicts"] = [{"constraint": "invented"}]
            else:
                after["dictionary"]["lemmas"].reverse()
            with (
                self.subTest(field=field),
                self.assertRaises((AssertionError, IndexError)),
            ):
                self.check(after)

    def test_whole_head_cannot_borrow_suffix_identity(self):
        after = deepcopy(self.after)
        owner = self.identity_entry(after)["derivational_identity"]
        whole = next(
            r
            for a, r in zip(
                after["analysis"]["analyses"],
                after["dictionary"]["readings"],
                strict=True,
            )
            if a["lemmas"][0]["text"] == "가공되다"
        )
        whole["lemmas"][0]["entries"][0]["derivational_identity"] = deepcopy(owner)
        with self.assertRaises(AssertionError):
            self.check(after)

    def test_binary_search_table_reordering_and_source_substitution_fail(self):
        for change in ("order", "origin", "source", "class"):
            table = self.table
            if change == "order":
                table = table.replace('base: "가공"', 'base: "가산"', 1)
            elif change == "origin":
                table = table.replace('"加工"', '"反感"', 1)
            elif change == "source":
                table = table.replace('"krdict:27950"', '"krdict:89858"', 1)
            else:
                table = table.replace(
                    "if !matches!(class, PredicateClass::Verb)", "if false"
                )
            with self.subTest(change=change), self.assertRaises(AssertionError):
                inspect_table(table, self.fixture)


if __name__ == "__main__":
    unittest.main()
