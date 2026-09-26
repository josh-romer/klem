"""Integrity failures that must never silently become reviewed coverage."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import review_inventory as inventory


class ReviewQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.entry = dict(id='krdict:1', headword='-요', homonym='1', pos='어미',
                          url='https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=1',
                          lexical_unit='단어', notes=['attachment'], forms=[],
                          senses=[dict(id='1', definition='sense', notes=['sense attachment'],
                                       patterns=[], examples=[['one'], ['two']], total_example_groups=3)])
        self.particle = copy.deepcopy(self.entry)
        self.particle.update(id='krdict:2', pos='조사', homonym='2',
                             url=self.entry['url'].replace('=1', '=2'))
        self.entries = [self.entry, self.particle]
        self.write(inventory.CATALOG, {'-요': dict(kind='ending', sources=[
            dict(id=1, headword='-요', pos='어미')])})
        self.ledger = dict(sources={'ending': self.entry['url']}, cases=[dict(
            id='case', judgments=[dict(id='required', source='ending', verdict='required')])])
        self.write(inventory.LEDGER, self.ledger)
        self.write(inventory.AUXILIARIES, dict(entries=[]))
        self.review = dict(id='krdict:1', source_sha256=inventory.digest(self.entry),
                           status='scoped', scope='Bare copula', remaining='Context',
                           checklist=['COV-001'], evidence=[dict(path='tests/ending.rs', test='boundary')],
                           judgments=[dict(case='case', judgment='required')])
        self.reviews = dict(schema_version=1, entries=[self.review])
        self.write(inventory.REVIEWS, self.reviews)
        (self.root / 'tests/ending.rs').write_text('#[test]\nfn boundary() {}\n')
        (self.root / 'docs/coverage-checklist.md').write_text('- [x] **COV-001 — Scope.**\n')

    def write(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def build(self):
        return inventory.build_queue(self.root, {}, self.entries)

    def test_homonyms_stay_separate_and_links_do_not_promote_reviews(self):
        self.reviews['entries'] = []
        self.write(inventory.REVIEWS, self.reviews)
        queue = self.build()
        self.assertEqual(queue['counts']['by_review'], {'unreviewed': 2})
        self.assertEqual(queue['counts']['with_catalog_links'], 1)
        self.assertEqual(queue['counts']['with_judgment_citations'], 1)
        particle = next(r for r in queue['entries'] if r['source']['pos'] == '조사')
        self.assertEqual(particle['catalog'], [])
        self.assertEqual(particle['cited_judgments'], [])
        self.assertEqual(queue, inventory.build_queue(self.root, {}, self.entries[::-1]))

    def test_stale_source_requires_new_manual_review(self):
        self.entry['senses'][0]['notes'].append('new restriction')
        with self.assertRaisesRegex(ValueError, 'stale source review'):
            self.build()

    def test_unknown_duplicate_and_incomplete_reviews_fail(self):
        for changes, message in [({'id': 'krdict:99'}, 'unknown reviewed'),
                                 ({'status': 'complete'}, 'invalid review status'),
                                 ({'remaining': ''}, 'missing review remaining'),
                                 ({'judgments': []}, 'needs judgments'),
                                 ({'checklist': ['COV-999']}, 'unknown checklist')]:
            with self.subTest(changes=changes):
                self.write(inventory.REVIEWS, dict(schema_version=1, entries=[self.review | changes]))
                with self.assertRaisesRegex(ValueError, message):
                    self.build()
        self.write(inventory.REVIEWS, dict(schema_version=1, entries=[self.review, self.review]))
        with self.assertRaisesRegex(ValueError, 'duplicate review'):
            self.build()

    def test_judgment_must_exist_and_cite_same_entry(self):
        for key in ('missing', 'required'):
            with self.subTest(key=key):
                self.review['judgments'][0]['judgment'] = key
                self.write(inventory.REVIEWS, self.reviews)
                self.ledger['sources']['ending'] = self.particle['url']
                self.write(inventory.LEDGER, self.ledger)
                with self.assertRaisesRegex(ValueError, 'does not cite reviewed entry'):
                    self.build()

    def test_missing_test_and_external_path_fail(self):
        for ref, message in [(dict(path='tests/ending.rs', test='removed'), 'unknown Rust test'),
                             (dict(path='../outside'), 'repository-relative')]:
            self.review['evidence'] = [ref]
            self.write(inventory.REVIEWS, self.reviews)
            with self.assertRaisesRegex(ValueError, message):
                self.build()

    def test_catalog_wrong_homonym_pos_fails(self):
        self.write(inventory.CATALOG, {'요': dict(kind='particle', sources=[
            dict(id=1, headword='-요', pos='조사')])})
        with self.assertRaisesRegex(ValueError, 'catalog identity mismatch'):
            self.build()

    def test_queue_tampering_and_changed_evidence_are_detected(self):
        queue = self.build()
        inventory.verify_queue(self.root, queue)
        modified = copy.deepcopy(queue)
        modified['entries'][0]['source']['notes'].append('tampered')
        with self.assertRaisesRegex(ValueError, 'stored source hash mismatch'):
            inventory.verify_queue(self.root, modified)
        modified = copy.deepcopy(queue)
        modified['counts']['entries'] += 1
        with self.assertRaisesRegex(ValueError, 'stale queue'):
            inventory.verify_queue(self.root, modified)
        (self.root / 'tests/ending.rs').write_text('#[test]\nfn boundary() { changed(); }\n')
        with self.assertRaisesRegex(ValueError, 'stale queue'):
            inventory.verify_queue(self.root, queue)

    def test_duplicate_source_and_ledger_ids_fail(self):
        self.entries.append(self.entry)
        with self.assertRaisesRegex(ValueError, 'duplicate source'):
            self.build()
        self.entries.pop()
        self.ledger['cases'].append(self.ledger['cases'][0])
        self.write(inventory.LEDGER, self.ledger)
        with self.assertRaisesRegex(ValueError, 'duplicate case'):
            self.build()

    def test_sqlite_projection_preserves_all_senses_and_notes(self):
        data = copy.deepcopy(self.entry)
        data['senses'][0]['examples'].append(['three'])
        data['senses'].append(data['senses'][0] | {'id': '2'})
        db_path = self.root / 'dictionary.db'
        with sqlite3.connect(db_path) as db:
            db.execute('CREATE TABLE metadata (key TEXT, value TEXT)')
            db.execute('INSERT INTO metadata VALUES (?,?)', ('snapshot', 'test'))
            db.execute('CREATE TABLE entries (id TEXT, headword TEXT, pos TEXT, data TEXT)')
            db.execute('INSERT INTO entries VALUES (?,?,?,?)',
                       (data['id'], data['headword'], data['pos'], json.dumps(data)))
            db.execute('INSERT INTO entries VALUES (?,?,?,?)', ('noun', 'noun', '명사', '{}'))
        before = db_path.read_bytes()
        metadata, entries = inventory.dictionary_entries(db_path)
        self.assertEqual(metadata, {'snapshot': 'test'})
        self.assertEqual(len(entries), 1)
        self.assertEqual(len(entries[0]['senses']), 2)
        self.assertEqual(entries[0]['senses'][0], self.entry['senses'][0])
        self.assertEqual(before, db_path.read_bytes())
        with sqlite3.connect(db_path) as db:
            db.execute("UPDATE entries SET headword='wrong' WHERE id='krdict:1'")
        with self.assertRaisesRegex(ValueError, 'dictionary index mismatch'):
            inventory.dictionary_entries(db_path)


if __name__ == '__main__':
    unittest.main()
