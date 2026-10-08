"""Ensure retained runtime evidence cannot hide missing cases or corrupt witnesses."""

import copy
import os
import unittest
from pathlib import Path

import predicate_auxiliary_spacing_runtime as audit

ROOT = Path(__file__).resolve().parents[1]


class SpacingRuntimeEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(os.environ.get(
            "KLEM_AUX_SPACING_RUNTIME",
            ROOT / "docs/predicate-auxiliary-spacing-main-portable-runtime.json.gz",
        ))
        cls.original = audit.read_json(path)

    def corrupt(self, mutate):
        report = copy.deepcopy(self.original)
        mutate(report)
        with self.assertRaises((AssertionError, ValueError, KeyError, StopIteration)):
            audit.verify(report, ROOT)

    @staticmethod
    def hypothesis(report):
        return next(
            h for r in report["runs"][0]["after"]
            for h in r.get("spacing", {}).get("alternatives", [])
            if h.get("rule") == audit.RULE
        )

    def test_partial_evidence_keeps_original_unmet_requirement(self):
        result = audit.verify(self.original, ROOT)
        self.assertEqual(result["observations"], 540)
        self.assertEqual(result["unmet_requirements"], ["auxiliary-nominalization-topic"])
        self.assertFalse(result["coverage_complete"])

    def test_missing_requirement_cannot_be_deleted(self):
        self.corrupt(lambda r: r["requirements"].pop())

    def test_missing_requirement_cannot_be_relabeled_forbidden(self):
        self.corrupt(lambda r: r["requirements"][-1].update(required_spaces=[]))

    def test_missing_requirement_cannot_be_hidden(self):
        self.corrupt(lambda r: r.update(unmet_requirements=[]))

    def test_partial_evidence_cannot_claim_completion(self):
        self.corrupt(lambda r: r.update(coverage_complete=True))

    def test_filter_cache_combination_cannot_be_omitted(self):
        self.corrupt(lambda r: r["runs"].pop())

    def test_unicode_mode_cannot_be_duplicated(self):
        self.corrupt(lambda r: r["runs"][-1].update(encoding="NFC"))

    def test_spacing_cannot_modify_whole_word_candidates(self):
        def mutate(r):
            record = next(x for x in r["runs"][0]["after"] if x.get("analysis"))
            record["analysis"]["analyses"] = []
        self.corrupt(mutate)

    def test_original_utf8_span_cannot_move(self):
        self.corrupt(lambda r: self.hypothesis(r)["records"][0]["span"].update(start=0))

    def test_independent_piece_cannot_invent_a_lemma(self):
        self.corrupt(lambda r: self.hypothesis(r)["records"][0]["analysis"]["analyses"][0]["lemmas"][0].update(text="invented"))

    def test_joined_context_cannot_use_another_source_span(self):
        self.corrupt(lambda r: self.hypothesis(r)["joined_contexts"][0]["span"].update(start=0))

    def test_distinct_joined_contexts_cannot_be_merged_as_duplicate_spans(self):
        def mutate(r):
            contexts = self.hypothesis(r)["joined_contexts"]
            contexts.append(copy.deepcopy(contexts[0]))
        self.corrupt(mutate)

    def test_piece_breakdown_cannot_omit_a_component(self):
        self.corrupt(lambda r: self.hypothesis(r)["records"][0]["breakdowns"][0].pop())

    def test_independent_piece_cannot_omit_native_members(self):
        self.corrupt(lambda r: self.hypothesis(r)["records"][0]["dictionary"].update(lemmas=[]))

    def test_independent_piece_cannot_borrow_a_dictionary_fingerprint(self):
        self.corrupt(lambda r: self.hypothesis(r)["records"][0]["dictionary"].update(fingerprint="wrong"))

    def test_individual_failed_observation_cannot_be_promoted(self):
        def mutate(r):
            next(o for o in r["observations"] if o["missing"])["missing"] = []
        self.corrupt(mutate)

    def test_api_cannot_disagree_with_cli(self):
        self.assertTrue(self.original["api"], "API runtime evidence required")
        self.corrupt(lambda r: r["api"]["NFC"]["records"].pop())

    def test_native_homonym_details_cannot_be_truncated(self):
        self.corrupt(lambda r: r["native"].pop(next(iter(r["native"]))))


if __name__ == "__main__":
    unittest.main()
