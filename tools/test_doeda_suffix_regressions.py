"""Mutation guards for immutable proposals and individually scoped corrections."""

import copy
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import doeda_suffix_regressions as audit


class Corrections(unittest.TestCase):
    def test_effective_cases_preserve_every_unamended_original(self):
        source = audit.read(audit.FIXTURE)
        effective = audit.effective_cases()
        originals = [c for c in source["cases"] if c["lemmas"][0] != "속"]
        self.assertTrue(all(c in effective for c in originals))
        self.assertEqual(
            Counter(c["verdict"] for c in effective),
            {"required": 1580, "forbidden": 20},
        )
        self.assertEqual(len({c["id"] for c in effective}), 1600)

    def test_rewritten_original_wrong_role_lost_sense_and_broad_conflict_are_rejected(
        self,
    ):
        data = audit.read(audit.CORRECTIONS)
        for kind in ("hash", "original", "role", "sense", "conflict"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                mutated = copy.deepcopy(data)
                if kind == "hash":
                    mutated["source_fixture_sha256"] = "0" * 64
                elif kind == "original":
                    mutated["corrections"][0]["original"]["verdict"] = "forbidden"
                elif kind == "role":
                    mutated["corrections"][0]["replacement_positive"]["lemma_kinds"][
                        0
                    ] = "nominal"
                elif kind == "sense":
                    mutated["source_entries"][1]["senses"].pop()
                else:
                    mutated["native_entry_reviews"][0]["required_rule"] = "particle"
                path = Path(tmp) / "corrections.json"
                path.write_text(json.dumps(mutated))
                with (
                    patch.object(audit, "CORRECTIONS", path),
                    self.assertRaises(AssertionError),
                ):
                    audit.effective_cases()

    def test_policy_separates_missing_heads_from_reviewed_identity_conflicts(self):
        raw = audit.records()
        policy = audit.records(True)
        self.assertEqual(len(raw), 1600)
        self.assertEqual(len(policy), 1540)
        indexed = {r["id"]: r for r in policy}
        for row in raw:
            old = row["judgments"][0]
            new = indexed.get(row["id"] + "-policy")
            if new is None:
                self.assertEqual(old["verdict"], "required")
                self.assertIn(
                    old["lemmas"][0], ("앳", "외람", "편벽", "허황", "헛", "이룩")
                )
            elif old["verdict"] != new["judgments"][0]["verdict"]:
                self.assertEqual(old["lemmas"][0], "속")
                self.assertEqual(old["lemma_kinds"][0], "root")
                self.assertEqual(new["judgments"][0]["verdict"], "forbidden")


if __name__ == "__main__":
    unittest.main()
