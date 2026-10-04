"""Guard original corpus gold, exact token boundaries, and suffix attribution."""

import json
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import test_doeda_suffix_diagnostics as attribution_tests
from doeda_suffix_corpora import (
    PREVIOUS,
    REPORT,
    candidate_changes,
    digest,
    gold_changes,
    inspect,
    words_from_cli,
)
from lexical_nada_audit import read


class CorpusGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        attribution_tests.Attribution.setUpClass()
        source = attribution_tests.Attribution
        cls.parent, cls.added = source.parent, source.added
        cls.components, cls.formations = source.components, source.formations

    def setUp(self):
        self.gold = {
            "id": "id:sentence/1",
            "surface": "속된",
            "expected": ["속", "되다", "은"],
            "matched": False,
            "recovered": 1,
            "recovered_sets": [[0], [1]],
        }
        self.context = {
            self.gold["id"]: {
                "complete_sentence": "original sentence",
                "original_row": ["1", "속된"],
            }
        }
        self.before = {"normalized": "속된", "analyses": [self.parent]}
        self.after = {
            "normalized": "속된",
            "analyses": [self.parent, self.added],
        }

    def candidates(self, before=None, after=None):
        return candidate_changes(
            "속된",
            before or self.before,
            after or self.after,
            [],
            self.components,
            self.formations,
        )

    def test_original_gold_cannot_be_rewritten(self):
        for field, value in (
            ("id", "replacement"),
            ("surface", "replacement"),
            ("expected", ["replacement"]),
        ):
            with self.subTest(field=field), self.assertRaises(AssertionError):
                gold_changes(
                    [self.gold], [dict(self.gold, **{field: value})], self.context
                )

    def test_new_maximal_set_must_preserve_every_old_recovery(self):
        good = dict(self.gold, recovered=2, recovered_sets=[[0, 1]])
        change = gold_changes([self.gold], [good], self.context)[0]
        self.assertEqual(change["original_row"], ["1", "속된"])
        bad = dict(self.gold, recovered=2, recovered_sets=[[0, 2]])
        with self.assertRaises(AssertionError):
            gold_changes([self.gold], [bad], self.context)
        complete = dict(
            self.gold, matched=True, recovered=3, recovered_sets=[[0, 1, 2]]
        )
        with self.assertRaises(AssertionError):
            gold_changes([complete], [dict(complete, matched=False)], self.context)

    def test_corrected_root_has_stable_individual_identity(self):
        first = self.candidates()
        self.assertEqual(first, self.candidates())
        self.assertEqual(first[0]["after"], self.added)
        self.assertEqual(first[0]["contextual_verdict"], "unjudged")
        self.assertEqual(first[0]["independent_review"], "pending")

    def test_wrong_root_role_or_lost_parent_is_rejected(self):
        mutated = deepcopy(self.after)
        mutated["analyses"][1]["lemmas"][0]["kind"] = "nominal"
        with self.assertRaises(AssertionError):
            self.candidates(after=mutated)
        with self.assertRaises(AssertionError):
            self.candidates(after=dict(self.after, analyses=[self.added]))

    def test_punctuation_bearing_original_token_uses_exact_word_interface(self):
        analyses = {word: {"normalized": word} for word in ("가", "나,다")}
        stream = [
            {
                "kind": "word",
                "surface": "가",
                "span": {"start": 0, "end": 3},
                "analysis": analyses["가"],
            },
            {"kind": "space", "surface": "\n"},
            {
                "kind": "word",
                "surface": "나",
                "span": {"start": 4, "end": 7},
                "analysis": {"normalized": "나"},
            },
            {"kind": "punctuation", "surface": ","},
            {
                "kind": "word",
                "surface": "다",
                "span": {"start": 8, "end": 11},
                "analysis": {"normalized": "다"},
            },
            {"kind": "space", "surface": "\n"},
        ]

        def run(command, **kwargs):
            if command[1] == "text":
                self.assertEqual(kwargs["input"], "가\n나,다\n")
                return SimpleNamespace(stdout="\n".join(map(json.dumps, stream)))
            self.assertEqual(command, ["cli", "word", "나,다"])
            return SimpleNamespace(stdout=json.dumps(analyses["나,다"]))

        with patch("doeda_suffix_corpora.subprocess.run", side_effect=run) as mocked:
            self.assertEqual(words_from_cli(Path("cli"), ["가", "나,다"]), analyses)
        self.assertEqual(mocked.call_count, 2)


class CorpusArchiveGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous, cls.report = read(PREVIOUS), read(REPORT)

    def test_original_context_cannot_be_rewritten(self):
        report = dict(self.report)
        report["changed_words"] = dict(report["changed_words"])
        surface = next(iter(report["changed_words"]))
        pair = deepcopy(report["changed_words"][surface])
        pair["occurrences"][0]["original_row"][2] = "rewritten lemma"
        report["changed_words"][surface] = pair
        with self.assertRaises(AssertionError):
            inspect(self.previous, report)

    def test_summary_path_drift_cannot_be_hidden_by_rehashing(self):
        report = dict(self.report)
        report["corpora"] = list(report["corpora"])
        corpus = dict(report["corpora"][0])
        lines = corpus["after_jsonl"].splitlines()
        summary = json.loads(lines[0])
        summary["input"] = "/different/path"
        lines[0] = json.dumps(summary)
        corpus["after_jsonl"] = "\n".join(lines) + "\n"
        corpus["after_report_sha256"] = digest(corpus["after_jsonl"])
        report["corpora"][0] = corpus
        with self.assertRaises(AssertionError):
            inspect(self.previous, report)

    def test_complete_original_text_must_match_pinned_source_hash(self):
        report = dict(self.report)
        report["original_corpus_texts"] = dict(report["original_corpus_texts"])
        source = report["corpora"][0]["source"]
        report["original_corpus_texts"][source] += "\n# rewritten\n"
        with self.assertRaises(AssertionError):
            inspect(self.previous, report)


if __name__ == "__main__":
    unittest.main()
