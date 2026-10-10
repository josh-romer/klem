"""Rederive every browser policy choice and export from complete raw API records."""
import copy
import gzip
import hashlib
import json
import signal
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda value: hashlib.sha256(value).hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def kept_indices(record, mode):
    paths = record.get('analysis', {}).get('analyses', []) if record.get('analysis') else []
    if mode == 'raw':
        return list(range(len(paths)))
    annotation = record['dictionary']
    result = []
    for index, path in enumerate(paths):
        matched = all(any(owner['lemma'] == lemma and owner['entries'] for owner in annotation['lemmas']) for lemma in path['lemmas'])
        if matched and (mode != 'compatible' or annotation['readings'][index]['status'] != 'incompatible'):
            result.append(index)
    return result


def filtered(record, mode):
    result = copy.deepcopy(record)
    if mode == 'raw' or record.get('analysis') is None:
        return result
    indices = kept_indices(record, mode)
    paths = [record['analysis']['analyses'][index] for index in indices]
    result['analysis']['analyses'] = paths
    result['dictionary']['readings'] = [record['dictionary']['readings'][index] for index in indices]
    lemmas = [lemma for path in paths for lemma in path['lemmas']]
    result['dictionary']['lemmas'] = [owner for owner in record['dictionary']['lemmas'] if owner['lemma'] in lemmas]
    return result


def inspect(browser, runtime, suites, native, labels, driver, supervisor):
    assert browser['state'] == 'isolated-browser-passed' and not browser['errors'], 'terminal browser capture'
    assert runtime['state'] == 'passed' and runtime['exit_code'] == 0 and runtime['inputs_unchanged'] and runtime['server_stopped'], 'owned browser runtime stopped'
    # The capture supervisor explicitly sends SIGINT after the browser finishes.
    # Popen reports signal termination as a negative signal number on Unix.
    assert runtime['server_exit_code'] in (0, -signal.SIGINT), 'expected owned server exit'
    assert sha(driver.encode()) == browser['producer_sha256'], 'actual browser driver bytes'
    assert sha(driver.encode()) in runtime['frozen_inputs'].values() and sha(supervisor.encode()) in runtime['frozen_inputs'].values(), 'actual frozen browser producers'
    assert 'job.send_signal(signal.SIGINT)' in supervisor and 'job.wait(timeout=20)' in supervisor, 'bounded explicit owned server shutdown'
    assert runtime['command'][1:3] == ['--port', '0'] and runtime['command'][0] in runtime['frozen_inputs'], 'actual owned server command'
    assert '--assets' in runtime['command'] and '--dictionary' in runtime['command'], 'actual assets and dictionary command'
    assert len(suites) == 1 and [len(suite['cases']) for suite in suites] == [46], 'complete Source gold novel suites'
    cases = [case for suite in suites for case in suite['cases'] if any(j['verdict'] == 'required' for j in case['judgments'])]
    assert len(cases) == 37 and len({case['id'] for case in cases}) == 37, 'complete required path identities'
    assert [(r['encoding'], r['mode']) for r in browser['exports']] == [(encoding, mode) for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible']], 'six exact export choices'
    assert [response['encoding'] for response in browser['responses']] == ['NFC', 'NFD'], 'both original Unicode responses'
    decisions, diagrams, exclusions = [], [], []
    for response in browser['responses']:
        encoding, api = response['encoding'], response['api']
        assert api['rules'].get('ending.apprehensive_lsera'), 'actual ending rule identity'
        text = ' '.join(unicodedata.normalize(encoding, case['surface']) for case in cases)
        raw = text.encode()
        cursor = 0
        assert len(api['records']) == 73 and len(api['breakdowns']) == 73, 'complete original API frames'
        for record in api['records']:
            assert record['span']['start'] == cursor, 'original API span continuity'
            cursor = record['span']['end']
            assert raw[record['span']['start']:cursor].decode() == record['surface'], 'original API byte ownership'
            if record.get('analysis'):
                assert len(record['analysis']['analyses']) == len(record['dictionary']['readings']), 'one assessment per path'
        assert cursor == len(raw), 'complete original API bytes'
        words = [(index, record) for index, record in enumerate(api['records']) if record['kind'] == 'word']
        assert len(words) == len(cases), 'all original target words'
        for mode in ['raw', 'headword', 'compatible']:
            exported = next(e for e in browser['exports'] if (e['encoding'], e['mode']) == (encoding, mode))
            assert exported['records'] == [filtered(record, mode) for record in api['records']], 'independently derived complete export'
            for case, (record_index, record) in zip(cases, words, strict=True):
                assert record['surface'] == unicodedata.normalize(encoding, case['surface']), 'original target surface'
                judgment = next(j for j in case['judgments'] if j['verdict'] == 'required')
                paths = record['analysis']['analyses']
                indices = [i for i, path in enumerate(paths)
                           if [lemma['text'] for lemma in path['lemmas']] == judgment['lemmas']
                           and [morph['form'] for morph in path['morphemes']] == judgment['morphemes']
                           and all(rule in path['rules'] for rule in judgment['required_rules'])]
                assert indices, 'independent authored path present'
                index = indices[0]
                path = paths[index]
                assert [lemma['kind'] for lemma in path['lemmas']] == judgment['lemma_kinds'], 'independent authored lemma roles'
                assert [morph['kind'] for morph in path['morphemes']] == judgment['morpheme_kinds'], 'independent authored morpheme roles'
                kept = kept_indices(record, mode)
                offered = [str(i) for i in kept] if kept else ['']
                value = {'case_id': case['id'], 'encoding': encoding, 'mode': mode, 'record_index': record_index,
                         'raw_analysis_index': index, 'analysis': path, 'allowed': index in kept, 'offered_indices': offered}
                if not kept:
                    value['empty_message'] = 'No matching reading'
                decisions.append(value)
                if index not in kept:
                    exclusions.append((case['id'], encoding, mode))
                    continue
                order = api['breakdowns'][record_index][index]
                assert order, 'ordered selected diagram'
                forms = []
                for position, component in enumerate(order):
                    if 'lemma' in component:
                        lemma = path['lemmas'][component['lemma']]
                        form = lemma['text']
                        if lemma['kind'] in ['predicate', 'auxiliary', 'copula'] and form.endswith('다'):
                            form = form[:-1]
                        forms.append(form)
                    else:
                        morph = path['morphemes'][component['morpheme']]
                        form = morph['form']
                        previous = order[position - 1] if position else None
                        after_ha = previous and (
                            ('lemma' in previous and path['lemmas'][previous['lemma']]['text'].endswith('하다'))
                            or ('morpheme' in previous and path['morphemes'][previous['morpheme']]['kind'] == 'suffix'
                                and path['morphemes'][previous['morpheme']]['form'] == '하다'))
                        # The viewer expands 하+어/었 to 하+여/였 without changing
                        # the canonical path or its dictionary lookup keys.
                        if after_ha and form.startswith('었'):
                            form = '였' + form[1:]
                        elif after_ha and form.startswith('어'):
                            form = '여' + form[1:]
                        elif morph['kind'] == 'suffix' and form in ('답다', '되다', '하다'):
                            form = form[:-1]
                        forms.append(form)
                diagrams.append((case['id'], encoding, mode, path, forms))
    assert browser['policyDecisions'] == decisions and len(decisions) == 222, 'all independent policy decisions'
    assert [(row['case_id'], row['encoding'], row['mode'], row['analysis'], row['forms']) for row in browser['diagrams']] == diagrams and len(diagrams) == 222, 'every exact authored diagram and form'
    expected_exclusions = []
    assert exclusions == expected_exclusions, 'exact original unmatched dictionary exclusions'
    for diagram in browser['diagrams']:
        final = diagram['analysis']['morphemes'][-1]
        key = final['form'] if final['kind'] == 'particle' else '-' + final['form']
        label = labels[key]
        assert label['kind'] == final['kind'] and all(str(s['id']) in diagram['source_hint'] for s in label['sources']), 'actual kind and original label owners'
        assert not diagram['references'], 'original entry source hint scope'
    assert len(browser['nativeEntries']) == len(native) == 74 and {row['id']: row['entry'] for row in browser['nativeEntries']} == native, 'all complete original Native responses'
    assert not browser['spacingDiagrams'], 'recorded browser spacing scope'
    return {'original_api_frames': 146, 'policy_decisions': len(decisions), 'rendered_diagrams': len(diagrams),
            'correct_dictionary_exclusions': len(exclusions), 'exact_exports': 6, 'native_entries': len(native), 'owned_server_stopped': True}


def inputs():
    docs = ROOT / 'docs'
    browser = read(docs / 'fear-lsera-closure-browser.json.gz')
    runtime = read(docs / 'fear-lsera-closure-browser-runtime.json.gz')
    suites = [read(ROOT / 'tests/fixtures/fear-lsera-validity.json')]
    native = read(ROOT / 'tests/fixtures/fear-lsera-additional-native-entries.json')
    labels = read(ROOT / 'web/src/grammar-labels.json')
    driver = gzip.decompress((docs / 'fear-lsera-closure-browser.mjs.gz').read_bytes()).decode()
    supervisor = gzip.decompress((docs / 'fear-lsera-closure-browser-supervisor.py.gz').read_bytes()).decode()
    return browser, runtime, suites, native, labels, driver, supervisor

if __name__ == '__main__':
    print(inspect(*inputs()))
