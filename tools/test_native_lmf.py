"""Catch field loss, duplicate identities and mixed-language fixture adapters."""

import copy
import json
import unittest
from pathlib import Path

from native_lmf import verify_native_lmf

ROOT = Path(__file__).resolve().parents[1]


class NativeLmfTests(unittest.TestCase):
    def setUp(self):
        fixtures = ROOT / "tests/fixtures"
        self.native = json.loads(
            (fixtures / "lexical-nada-dependencies.json").read_text()
        )["complete_native_entries"]
        self.lmf = json.loads(
            (fixtures / "krdict-lexical-nada-dependencies.json").read_text()
        )

    def test_native_fields_match_without_original_export(self):
        verify_native_lmf(self.lmf, self.native)

    def test_each_sense_field_and_entry_identity_is_checked(self):
        for change in [
            "SenseExample",
            "Equivalent",
            "feat",
            "val",
            "duplicate",
            "homonym",
            "WordForm",
        ]:
            with self.subTest(change=change):
                lmf = copy.deepcopy(self.lmf)
                entries = lmf["LexicalResource"]["Lexicon"]["LexicalEntry"]
                raw = next(e for e in entries if e["val"] == "79260")
                if change == "duplicate":
                    entries.append(copy.deepcopy(raw))
                elif change == "homonym":
                    next(f for f in raw["feat"] if f["att"] == "homonym_number")[
                        "val"
                    ] = "1"
                elif change == "WordForm":
                    raw["WordForm"] = {"feat": {"att": "writtenForm", "val": "가짜"}}
                elif change == "val":
                    raw["val"] = "123456789"
                else:
                    raw["Sense"][0].pop(change)
                with self.assertRaises(AssertionError):
                    verify_native_lmf(lmf, self.native)

    def test_unexpected_non_english_translation_is_rejected(self):
        raw = next(
            e
            for e in self.lmf["LexicalResource"]["Lexicon"]["LexicalEntry"]
            if e["val"] == "79260"
        )
        extra = copy.deepcopy(raw["Sense"][0]["Equivalent"][0])
        next(f for f in extra["feat"] if f["att"] == "language")["val"] = "일본어"
        raw["Sense"][0]["Equivalent"].append(extra)
        with self.assertRaises(AssertionError):
            verify_native_lmf(self.lmf, self.native)


if __name__ == "__main__":
    unittest.main()
