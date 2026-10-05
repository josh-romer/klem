"""Verify actual noun-hada API ordering, native endpoints and browser exports."""
import argparse
import base64
import hashlib
import unicodedata

from hada_nominal_audit import FIXTURE, RULES, SOURCE, inspect_source
from hada_nominal_audit import REPORT as DIAGNOSTICS
from well_doeda_audit import MODES, ROOT, read, sha, word_records

REPORT = ROOT / 'docs/hada-nominal-runtime-checks.json.gz'


def inspect(report):
    source, diagnostics = read(SOURCE), read(DIAGNOSTICS)
    owners = inspect_source(source)
    bases = {o['base'] for o in owners.values()}
    words = list(read(FIXTURE)['before_analyses'])
    api, browser = report['api'], report['browser']
    assert report['source_sha256'] == api['source_sha256'] == sha(SOURCE)
    assert report['diagnostics_sha256'] == sha(DIAGNOSTICS)
    assert api['cli_sha256'] == browser['cli_sha256'] == diagnostics['cli_sha256']
    assert api['fixture_sha256'] == browser['fixture_sha256'] == sha(FIXTURE)
    assert browser['dictionary_sha256'] == diagnostics['dictionary_sha256']
    assert api['before']['cli_sha256'] == source['before_cli_sha256']
    groups, group = [], []
    for word in words:
        trial = group + [word]
        if group and (len(trial) > 63 or max(len(unicodedata.normalize(e, ' '.join(trial)).encode()) for e in ['NFC', 'NFD']) > 7800):
            groups.append(group)
            group = []
        group.append(word)
    if group:
        groups.append(group)
    assert len(groups) == 11 and api['before']['derived_orders'] == 0
    assert len(api['before']['batches']) == 11 and len(api['batches']) == 22
    before = {}
    _, original = word_records(source['before']['raw']['jsonl'])
    _, expected = word_records(diagnostics['runs']['raw']['NFC-cached']['jsonl'])
    for batch, group in zip(api['before']['batches'], groups, strict=True):
        assert batch['encoding'] == 'NFC' and batch['request']['text'] == ' '.join(group)
        assert hashlib.sha256(batch['cli_jsonl'].encode()).hexdigest() == batch['cli_jsonl_sha256']
        records, _ = word_records(batch['cli_jsonl'])
        assert records == batch['response']['records']
        for record, orders in zip(records, batch['response']['breakdowns'], strict=True):
            if not record.get('analysis'):
                continue
            word = record['analysis']['normalized']
            old = original[word]
            assert (record['analysis'], record['dictionary']) == (old['analysis'], old['dictionary'])
            before[word] = (record, orders)
    assert set(before) == set(words)
    count = derived = 0
    for encoding in ['NFC', 'NFD']:
        batches = [b for b in api['batches'] if b['encoding'] == encoding]
        assert len(batches) == len(groups)
        for batch, group in zip(batches, groups, strict=True):
            text = unicodedata.normalize(encoding, ' '.join(group))
            assert batch['request']['text'] == text and len(text.encode()) <= 8000
            assert hashlib.sha256(batch['cli_jsonl'].encode()).hexdigest() == batch['cli_jsonl_sha256']
            records, _ = word_records(batch['cli_jsonl'])
            assert records == batch['response']['records']
            for record, orders in zip(records, batch['response']['breakdowns'], strict=True):
                if not record.get('analysis'):
                    continue
                count += 1
                word = record['analysis']['normalized']
                wanted = expected[word]
                assert (record['analysis'], record['dictionary']) == (wanted['analysis'], wanted['dictionary'])
                previous, old_orders = before[word]
                for analysis, order in zip(record['analysis']['analyses'], orders, strict=True):
                    if analysis in previous['analysis']['analyses']:
                        assert order == old_orders[previous['analysis']['analyses'].index(analysis)]
                        continue
                    assert analysis['lemmas'][0]['text'] in bases
                    assert any(rule in analysis['rules'] for rule in RULES.values())
                    assert order[:2] == [{'lemma': 0}, {'morpheme': 0}]
                    assert [c['morpheme'] for c in order if 'morpheme' in c] == list(range(len(analysis['morphemes'])))
                    assert [c['lemma'] for c in order if 'lemma' in c] == list(range(len(analysis['lemmas'])))
                    derived += 1
    assert count == 1298 and derived == api['derived_orders'] == 708
    assert api['complete_native_entries'] == api['before']['complete_native_entries'] == source['complete_native_entries']
    for captured in [api, api['before']]:
        assert hashlib.sha256(captured['producer']['text'].encode()).hexdigest() == captured['producer']['sha256']
    assert browser['browser_errors'] == [] and len(browser['diagrams']) == 8
    text = '공부하시다 건강해요 정직했어요 사랑하는'
    assert [b['encoding'] for b in browser['responses']] == ['NFC', 'NFD']
    for captured in browser['responses']:
        assert captured['request']['text'] == unicodedata.normalize(captured['encoding'], text)
        response = captured['response']
        suffix = next(e for e in response['grammar']['-하다'] if e['id'] == 'krdict:88475')
        assert suffix == {key: source['complete_native_entries']['krdict:88475'][key] for key in ['headword', 'homonym', 'id', 'pos']}
        for record in response['records']:
            if record.get('analysis'):
                old = expected[record['analysis']['normalized']]
                assert (record['analysis'], record['dictionary']) == (old['analysis'], old['dictionary'])
    assert {(c['encoding'], c['mode']) for c in browser['checks']} == {(e, m) for e in ['NFC', 'NFD'] for m in MODES}
    for check in browser['checks']:
        assert check['cli_records'] == check['exported_records']
        _, wanted = word_records(diagnostics['runs'][check['mode']]['NFC-cached']['jsonl'])
        for record in check['exported_records']:
            if record.get('analysis'):
                old = wanted[record['analysis']['normalized']]
                assert (record['analysis'], record['dictionary']) == (old['analysis'], old['dictionary'])
    for diagram in browser['diagrams']:
        response = next(b['response'] for b in browser['responses'] if b['encoding'] == diagram['encoding'])
        record = next(r for r in response['records'] if (r.get('analysis') or {}).get('normalized') == diagram['word'])
        analysis = record['analysis']['analyses'][diagram['selected']]
        assert diagram['selected'] != diagram['whole_selected']
        assert analysis['lemmas'][0] == {'text': diagram['base'], 'kind': 'nominal'}
        owner = owners[diagram['base'] + '하다']
        assert RULES[owner['sense_id']] in analysis['rules']
        assert diagram['owner'] == record['dictionary']['readings'][diagram['selected']]['lemmas'][0]
        entry = next(e for e in diagram['owner']['entries'] if e['id'] == diagram['entry'])
        assert diagram['label'] == response['glosses'][diagram['entry']]
        assert entry['derivational_identity']['relation'] == ('unknown' if diagram['word'] == '사랑하는' else 'recorded_match')
        assert diagram['parts'][:2] == [diagram['base'], '하']
        assert diagram['formation_label'] == ('State / adjective formation' if owner['sense_id'] == '2' else 'Action / verb formation')
        assert ('sense 2' in diagram['formation_title']) if owner['sense_id'] == '2' else ('Other -하다 senses' in diagram['formation_title'])
        whole = record['analysis']['analyses'][diagram['whole_selected']]
        assert whole['lemmas'][0] == {'text': owner['whole_head'], 'kind': 'predicate'}
    assert set(report['screenshots']) == {'desktop', 'mobile'}
    for screenshot in report['screenshots'].values():
        raw = base64.b64decode(screenshot['base64'], validate=True)
        assert raw.startswith(b'\x89PNG\r\n\x1a\n') and hashlib.sha256(raw).hexdigest() == screenshot['sha256']
    return count, derived, 138, 8, 6


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', required=True)
    parser.parse_args()
    print('Verified API words/orders/native/diagrams/exports:', inspect(read(REPORT)))
