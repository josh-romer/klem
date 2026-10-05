"""Verify actual API/CLI parity and source-specific browser diagrams and exports."""
import argparse
import base64
import hashlib
import unicodedata

import hada_remaining_audit as audit

REPORT = audit.ROOT / 'docs/hada-remaining-runtime-checks.json.gz'


def inspect(report):
    source = audit.read(audit.SOURCE)
    diagnostics = audit.read(audit.REPORT)
    owners = audit.inspect_source(source)
    api, browser = report['api'], report['browser']
    assert report['source_sha256'] == api['source_sha256'] == audit.sha(audit.SOURCE)
    assert report['diagnostics_sha256'] == audit.sha(audit.REPORT)
    assert api['cli_sha256'] == browser['cli_sha256'] == diagnostics['cli_sha256']
    assert api['fixture_sha256'] == browser['fixture_sha256'] == audit.sha(audit.FIXTURE)
    assert browser['dictionary_sha256'] == diagnostics['dictionary_sha256']
    previous = audit.read(audit.ROOT / 'docs/hada-nominal-runtime-checks.json.gz')['api']
    assert api['before'] == previous
    packaged = audit.read(audit.ROOT / 'docs/hada-nominal-packaged-checks.json.gz')
    assert packaged['cli_sha256'] == source['before_cli_sha256']
    assert hashlib.sha256(api['producer']['text'].encode()).hexdigest() == api['producer']['sha256']
    assert browser['producer_sha256'] == audit.sha(audit.ROOT / 'web/tests/hada-remaining.mjs')
    _, original = audit.word_records(source['before']['raw']['jsonl'])
    _, expected = audit.word_records(diagnostics['runs']['raw']['NFC-cached']['jsonl'])
    old_orders = {}
    for batch in packaged['api_batches']:
        for record, orders in zip(batch['response']['records'], batch['response']['breakdowns'], strict=True):
            if record.get('analysis'):
                word = record['analysis']['normalized']
                assert record['analysis'] == original[word]['analysis']
                assert record['dictionary'] == original[word]['dictionary']
                if word in old_orders:
                    assert old_orders[word] == orders
                old_orders[word] = orders
    count = derived = 0
    for encoding in ['NFC', 'NFD']:
        batches = [b for b in api['batches'] if b['encoding'] == encoding]
        assert len(batches) == 11
        seen = []
        for batch in batches:
            assert len(batch['request']['text'].encode()) <= 8000
            assert batch['request']['text'] == unicodedata.normalize(encoding, batch['request']['text'])
            assert hashlib.sha256(batch['cli_jsonl'].encode()).hexdigest() == batch['cli_jsonl_sha256']
            records, _ = audit.word_records(batch['cli_jsonl'])
            assert records == batch['response']['records']
            assert ''.join(r['surface'] for r in records) == batch['request']['text']
            for record, orders in zip(records, batch['response']['breakdowns'], strict=True):
                if not record.get('analysis'):
                    continue
                word = record['analysis']['normalized']
                seen.append(word)
                count += 1
                assert (record['analysis'], record['dictionary']) == (expected[word]['analysis'], expected[word]['dictionary'])
                before = original[word]['analysis']['analyses']
                for analysis, order in zip(record['analysis']['analyses'], orders, strict=True):
                    if analysis in before:
                        assert order == old_orders[word][before.index(analysis)]
                        continue
                    parent, components = audit.parent_for(owners, word, analysis, before)
                    assert parent in before
                    assert [c['lemma'] for c in order if 'lemma' in c] == list(range(len(analysis['lemmas'])))
                    assert [c['morpheme'] for c in order if 'morpheme' in c] == list(range(len(analysis['morphemes'])))
                    for component in components:
                        at = order.index({'lemma':component['lemma_index']})
                        assert order[at + 1] == {'morpheme':component['morpheme_index']}
                    derived += 1
        assert seen == list(audit.read(audit.FIXTURE)['before_analyses'])
    assert (count, derived) == (1298, 752)
    assert api['complete_native_entries'] == source['complete_native_entries']
    assert browser['browser_errors'] == []
    assert len(browser['diagrams']) == 34
    assert {c['encoding'] for c in browser['responses']} == {'NFC', 'NFD'}
    for captured in browser['responses']:
        encoding = captured['encoding']
        response = captured['response']
        assert ''.join(r['surface'] for r in response['records']) == captured['request']['text']
        for diagram in [d for d in browser['diagrams'] if d['encoding'] == encoding]:
            record = next(r for r in response['records'] if (r.get('analysis') or {}).get('normalized') == diagram['word'])
            analyses = record['analysis']['analyses']
            owner, li, mi = diagram['source_owner'], diagram['lemma_index'], diagram['morpheme_index']
            assert owner in source['owners']
            assert analyses[diagram['whole_selected']]['lemmas'][li]['text'] == owner['whole_head']
            analysis = analyses[diagram['selected']]
            assert analysis['lemmas'][li] == {'text':owner['base'], 'kind':audit.ROLES[owner['base_role']]}
            assert analysis['morphemes'][mi] == {'form':'하다', 'kind':'suffix'}
            order = response['breakdowns'][response['records'].index(record)][diagram['selected']]
            assert order == diagram['order']
            at = order.index({'lemma':li})
            assert order[at + 1] == {'morpheme':mi}
            assert diagram['parts'][at:at + 2] == [owner['base'], '하']
            licensed = audit.rules_for(owner) & set(analysis['rules'])
            adjective = any('.adjective.' in r for r in licensed)
            verb = any('.verb.' in r for r in licensed)
            label = ('Auxiliary verb / adjective formation' if adjective and verb else 'Auxiliary adjective formation' if adjective else 'Auxiliary verb formation') if owner['sense_id'] == '6' else ('Verb / adjective formation' if adjective and verb else 'State / adjective formation' if adjective else 'Action / verb formation')
            assert diagram['formation_label'] == label
            assert 'sense ' + owner['sense_id'] in diagram['formation_title']
            assert ('Root status does not assert a standalone dictionary entry.' in diagram['formation_title']) == (owner['base_role'] == 'root')
        assert {d['source_owner']['base'] for d in browser['diagrams'] if d['encoding'] == encoding} == {o['base'] for o in source['owners']}
    assert {(c['encoding'], c['mode']) for c in browser['checks']} == {(e, m) for e in ['NFC', 'NFD'] for m in ['raw', 'headword', 'compatible']}
    for check in browser['checks']:
        assert check['cli_records'] == check['exported_records']
        _, expected_mode = audit.word_records(diagnostics['runs'][check['mode']]['NFC-cached']['jsonl'])
        context = audit.read(audit.ROOT / 'docs/hada-remaining-context-checks.json.gz')
        _, contextual = audit.word_records(context['runs'][check['mode']]['NFC-cached']['jsonl'])
        expected_mode.update(contextual)
        for record in check['exported_records']:
            if record.get('analysis'):
                target = expected_mode[record['analysis']['normalized']]
                assert (record['analysis'], record['dictionary']) == (target['analysis'], target['dictionary'])
    assert set(report['screenshots']) == {'desktop', 'mobile'}
    for screenshot in report['screenshots'].values():
        raw = base64.b64decode(screenshot['base64'], validate=True)
        assert raw.startswith(b'\x89PNG\r\n\x1a\n')
        assert hashlib.sha256(raw).hexdigest() == screenshot['sha256']
    return count, derived, 138, 34, 6


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', required=True)
    parser.parse_args()
    print('Verified API words/source additions/native endpoints/browser diagrams/exports:', inspect(audit.read(REPORT)))
