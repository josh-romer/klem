"""Independently verify a frozen fresh-passage capture; no linguistic verdicts."""
import gzip
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import unicodedata

from hada_remaining_audit import SOURCE, inspect_source, parent_for, read


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Paragraphs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current = None
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            assert self.current is None
            self.current = []

    def handle_endtag(self, tag):
        if tag == 'p' and self.current is not None:
            self.rows.append(''.join(self.current))
            self.current = None

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)


def records(run, text):
    assert run['exit_code'] == 0
    assert digest(run['jsonl'].encode()) == run['sha256']
    rows = [json.loads(line) for line in run['jsonl'].splitlines()]
    assert ''.join(row['surface'] for row in rows) == text
    offset = 0
    for row in rows:
        assert row['span'] == {'start': offset, 'end': offset + len(row['surface'].encode())}
        offset = row['span']['end']
    return rows


def inspect(base=Path(__file__).resolve().parents[1] / 'docs/fresh-unsu'):
    def path(suffix):
        return base.with_name(base.name + suffix)
    source = read(path('-source.json'))
    manifest = read(path('-evidence.json'))
    root = Path(__file__).resolve().parents[1]
    for name, expected in manifest['files'].items():
        assert digest((root / name).read_bytes()) == expected
    for name, screenshot in manifest['screenshots'].items():
        data = (root / name).read_bytes()
        assert data.startswith(b'\x89PNG\r\n\x1a\n')
        assert digest(data) == screenshot['sha256']
    html_bytes = gzip.decompress(path('-narrative.html.gz').read_bytes())
    assert digest(html_bytes) == manifest['narrative_fragment_sha256']
    html = html_bytes.decode()
    parser = Paragraphs()
    parser.feed(html)
    assert parser.current is None and parser.rows == source['paragraphs']
    text = '\n'.join(parser.rows)
    assert text == source['input']
    assert digest(text.encode()) == source['input_sha256']
    n = len(parser.rows)
    selected = [0, (n - 1) // 3, (2 * (n - 1)) // 3, n - 1]
    assert source['selection_indices'] == selected
    expected_passages = []
    for index in selected:
        value = parser.rows[index]
        identity = digest(json.dumps([457472, index, value], ensure_ascii=False).encode())[:20]
        expected_passages.append({'id': 'fresh-unsu-paragraph-' + identity, 'paragraph_index': index, 'text': value})
    assert source['selected_passages'] == expected_passages
    report = json.loads(gzip.decompress(path('-cli.json.gz').read_bytes()))
    assert report['source'] == source
    assert report['source_sha256'] == digest(path('-source.json').read_bytes())
    assert digest(report['producer']['text'].encode()) == report['producer']['sha256']
    owners = inspect_source(read(SOURCE))
    assert report['dictionary_sha256'] == read(SOURCE)['dictionary_sha256']
    assert report['before_cli_sha256'] == read(SOURCE)['before_cli_sha256']
    release = read(Path(__file__).resolve().parents[1] / 'docs/hada-remaining-packaged-checks.json.gz')
    assert report['cli_sha256'] == release['cli_sha256']
    assert set(report['runs']) == set(report['before']) == {'raw', 'headword', 'compatible'}
    changes, misses = [], []
    for mode, runs in report['runs'].items():
        before = records(report['before'][mode], unicodedata.normalize('NFC', text))
        assert set(runs) == {'NFC-cached', 'NFC-uncached', 'NFD-cached', 'NFD-uncached'}
        semantics = None
        for name, run in runs.items():
            after = records(run, unicodedata.normalize(name.split('-')[0], text))
            current = [(row['kind'], row.get('analysis'), row.get('dictionary')) for row in after]
            if semantics is None:
                semantics = current
            else:
                assert semantics == current
        after = records(runs['NFC-cached'], unicodedata.normalize('NFC', text))
        assert len(before) == len(after)
        count = words = empty = 0
        for ordinal, (old, new) in enumerate(zip(before, after, strict=True)):
            assert (old['kind'], old['surface'], old['span']) == (new['kind'], new['surface'], new['span'])
            if new['kind'] != 'word':
                assert new == old
                continue
            words += 1
            empty += not new['analysis']['analyses']
            if mode == 'compatible' and not new['analysis']['analyses']:
                misses.append(ordinal)
            parents = old['analysis']['analyses']
            assert [a for a in new['analysis']['analyses'] if a in parents] == parents
            flat = new['dictionary']['lemmas']
            original = old['dictionary']['lemmas']
            assert [item for item in flat if item['lemma'] in [x['lemma'] for x in original]] == original
            for index, analysis in enumerate(new['analysis']['analyses']):
                reading = new['dictionary']['readings'][index]
                if analysis in parents:
                    assert reading == old['dictionary']['readings'][parents.index(analysis)]
                    continue
                word = new['analysis']['normalized']
                parent, components = parent_for(owners, word, analysis, parents)
                identity = digest(json.dumps([mode, ordinal, analysis], ensure_ascii=False, sort_keys=True).encode())[:20]
                changes.append({'id': 'fresh-unsu-change-' + identity, 'mode': mode, 'record': ordinal, 'surface': word, 'analysis': analysis, 'parent': parent, 'inserted_components': components, 'reading': reading, 'contextual_verdict': 'unjudged', 'independent_review': 'pending'})
                count += 1
        assert report['statistics'][mode] == {'records': len(after), 'word_records': words, 'empty_word_records': empty, 'candidate_additions': count}
    assert report['candidate_changes'] == changes
    review = read(path('-review.json'))
    assert review['source_sha256'] == report['source_sha256']
    assert review['cli_capture_sha256'] == digest(path('-cli.json.gz').read_bytes())
    assert review['browser_capture_sha256'] == digest(gzip.decompress(path('-browser.json.gz').read_bytes()))
    assert [x['record_index'] for x in review['dictionary_misses']] == misses
    raw = records(report['runs']['raw']['NFC-cached'], unicodedata.normalize('NFC', text))
    head = records(report['runs']['headword']['NFC-cached'], unicodedata.normalize('NFC', text))
    compatible = records(report['runs']['compatible']['NFC-cached'], unicodedata.normalize('NFC', text))
    counts = {}
    encoded = text.encode()
    for miss in review['dictionary_misses']:
        index = miss['record_index']
        row = compatible[index]
        assert miss['surface'] == row['surface'] and miss['span'] == row['span']
        identity = digest(json.dumps([source['input_sha256'], index, row['surface']], ensure_ascii=False).encode())[:20]
        assert miss['id'] == 'fresh-unsu-miss-' + identity
        start, end = row['span']['start'], row['span']['end']
        assert miss['context_before'] == encoded[:start].decode()[-70:]
        assert miss['context_after'] == encoded[end:].decode()[:70]
        assert miss['headword_analyses'] == head[index]['analysis']['analyses']
        assert miss['raw_dictionary_lemmas'] == [l for l in raw[index]['dictionary']['lemmas'] if l['entries']]
        observation = 'headword matches excluded by compatibility' if miss['headword_analyses'] else 'no dictionary-matched complete candidate'
        assert miss['coverage_observation'] == observation
        counts[observation] = counts.get(observation, 0) + 1
        assert miss['judgment'] == 'unjudged' and miss['independent_review'] == 'pending'
    assert review['coverage_observation_counts'] == counts
    browser = json.loads(gzip.decompress(path('-browser.json.gz').read_bytes()))
    assert browser['source_sha256'] == report['source_sha256']
    assert browser['cli_sha256'] == report['cli_sha256']
    assert browser['dictionary_sha256'] == report['dictionary_sha256']
    assert browser['errors'] == []
    assert digest(manifest['browser_producer']['text'].encode()) == manifest['browser_producer']['sha256'] == browser['producer_sha256']
    assert len(browser['captures']) == 8
    for passage in expected_passages:
        for encoding in ['NFC', 'NFD']:
            capture = next(c for c in browser['captures'] if c['passage_id'] == passage['id'] and c['encoding'] == encoding)
            assert capture['paragraph_index'] == passage['paragraph_index']
            assert capture['request']['text'] == unicodedata.normalize(encoding, passage['text'])
            assert ''.join(r['surface'] for r in capture['response']['records']) == capture['request']['text']
            assert len(capture['checks']) == 3
            assert capture['response']['records'] == capture['checks'][0]['cli_records']
            for mode, check in zip(['raw', 'headword', 'compatible'], capture['checks'], strict=True):
                assert check['mode'] == mode and check['cli_records'] == check['exported_records']
                assert ''.join(r['surface'] for r in check['cli_records']) == capture['request']['text']
            word_records = [r for r in capture['response']['records'] if r['kind'] == 'word']
            assert len(capture['diagrams']) == len(word_records)
            for diagram, word in zip(capture['diagrams'], word_records, strict=True):
                assert diagram['surface'] == word['surface']
                if diagram['selected'] is not None:
                    assert 0 <= int(diagram['selected']) < len(word['analysis']['analyses'])
    options = read(path('-options.json'))
    assert len(options['captures']) == 4
    for capture in options['captures']:
        assert capture['forms'] == ['먹', '지', '를']
        assert capture['analysis']['lemmas'] == [{'text':'먹다','kind':'predicate'}]
        assert [m['form'] for m in capture['analysis']['morphemes']] == ['지','를']
    return len(parser.rows), words, len(changes), len(misses)


if __name__ == '__main__':
    print('Verified retained narrative extraction, deterministic passage selection, complete spans, twelve streams, retained candidates/readings/flat entries, exact source parents and individual miss coverage:', inspect())
