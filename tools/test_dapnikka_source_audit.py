"""Controls reject source loss, identity borrowing and altered requirements."""

import copy
import unittest

import dapnikka_source_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def reject(self, mutation, reason):
        values = copy.deepcopy(self.evidence)
        mutation(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(*values)

    def test_actual_sources(self):
        self.assertEqual(audit.inspect(*self.evidence)["native_entries"], 90)

    def test_dialogue_group_loss(self):
        self.reject(lambda v: v[0]["complete_groups"].pop(), "complete original groups")

    def test_missing_expression(self):
        self.reject(lambda v: v[0]["complete_imported_entries"].pop("krdict:86630"), "ending/expression identities")

    def test_changed_lemma(self):
        self.reject(lambda v: v[5]["cases"][0]["judgments"][0].update(lemmas=["먹다"]), "source requirement")

    def test_label_borrows_identity(self):
        self.reject(lambda v: v[6]["-답니까"]["sources"][0].update(id=86566), "source identities")

    def test_duplicate_native_identity(self):
        self.reject(lambda v: v[2]["LexicalResource"]["Lexicon"]["LexicalEntry"].append(copy.deepcopy(v[2]["LexicalResource"]["Lexicon"]["LexicalEntry"][0])), "identity collision")

    def test_reclassified_homonym(self):
        self.reject(lambda v: v[1]["entries"]["krdict:64526"].update(pos="동사"), "Native projection")

    def test_lost_label_entry(self):
        self.reject(lambda v: v[7]["LexicalResource"]["Lexicon"]["LexicalEntry"].pop(), "label fixture source identities")

    def test_lost_native_label_field(self):
        self.reject(lambda v: v[7]["LexicalResource"]["Lexicon"]["LexicalEntry"][0].pop("feat"), "complete label fixture Native entries")


if __name__ == "__main__":
    unittest.main()
