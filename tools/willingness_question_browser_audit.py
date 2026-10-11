"""Bind original typed paths, dropdown policies and exports to the prototype browser."""
import gzip
import hashlib
import json
import signal
import unicodedata
from pathlib import Path

from conjectural_additive_novel_audit import matches
from formal_volitional_browser_audit import filtered, kept_indices

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def inputs():
    proof = lambda name: read(ROOT / 'docs' / ('willingness-question-distribution-proof-' + name + '.gz'))
    return {'build': proof('browser-prototype-build.json'),
            'cli': proof('prototype-binaries-retry2.json'),
            'runtime': proof('willingness-prototype-browser-runtime.json'),
            'browser': proof('willingness-prototype-browser.json'),
            'driver': gzip.decompress((ROOT / 'docs/willingness-question-distribution-proof-willingness-browser.mjs.gz').read_bytes()),
            'suites': [read(ROOT / 'tests/fixtures' / name) for name in ['willingness-question-validity.json', 'willingness-question-boundary-validity.json']],
            'label': read(ROOT / 'web/src/grammar-labels.json')['-으련'],
            'native': read(ROOT / 'tests/fixtures/willingness-question-native-entries.json')}


def inspect(v):
    build, cli = v['build'], v['cli']
    assert build['state'] == cli['state'] == 'passed' and build['inputs_unchanged'] and build['prior_binaries_unchanged'] and cli['inputs_unchanged'], 'terminal frozen prototype build'
    assert len(build['commands']) == 2 and all(c['exit_code'] == 0 for c in build['commands']) and build['commands'][0]['command'] == ['cargo', 'build', '--locked', '--offline', '--features', 'web', '--bin', 'klem-web'] and build['commands'][1]['command'] == ['npm', 'run', 'build'], 'actual offline server and SolidJS build'
    runtime = v['runtime']
    assert runtime['state'] == 'passed' and runtime['exit_code'] == 0 and runtime['inputs_unchanged'] and runtime['server_stopped'], 'terminal stopped prototype browser server'
    # The captured supervisor deliberately sends SIGINT; Unix Popen reports -2.
    assert runtime['server_exit_code'] in (0, -signal.SIGINT), 'expected owned server shutdown'
    command = runtime['command']
    assert command[0] == build['server']['path'] and command[1:4] == ['--port', '0', '--assets'] and command[5] == '--dictionary' and command[6] in runtime['frozen_inputs'], 'actual source-bound server command'
    assert runtime['frozen_inputs'][command[0]] == build['server']['sha256'] and runtime['frozen_inputs'][cli['binaries']['klem']['path']] == cli['binaries']['klem']['sha256'], 'actual source-bound binary identities'
    assert {str(Path(command[4]) / path): digest for path, digest in build['assets'].items()}.items() <= runtime['frozen_inputs'].items(), 'all actual built frontend asset bytes'
    assert sha(runtime['producer']['text'].encode()) == runtime['producer']['sha256'], 'actual prototype supervisor'
    assert 'job.send_signal(signal.SIGINT)' in runtime['producer']['text'] and 'job.wait(timeout=20)' in runtime['producer']['text'], 'bounded explicit owned shutdown'
    browser = v['browser']
    assert browser['state'] == 'source-bound-willingness-prototype-browser-passed' and not browser['errors'] and browser['producer_sha256'] == sha(v['driver']), 'actual error-free browser driver'
    cases = [(case, j) for suite in v['suites'] for case in suite['cases'] for j in case['judgments'] if j['verdict'] == 'required']
    assert len(cases) == 15, 'all independent source and boundary paths'
    assert [r['encoding'] for r in browser['responses']] == ['NFC', 'NFD'], 'both original browser Unicode encodings'
    assert [(e['encoding'], e['mode']) for e in browser['exports']] == [(encoding, mode) for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible']], 'all six original browser exports'
    expected_decisions, expected_diagrams = [], []
    label = v['label']
    assert label['kind'] == 'ending' and label['sources'] == [{'id': 76564, 'headword': '-련', 'pos': '어미'}, {'id': 76567, 'headword': '-으련', 'pos': '어미'}], 'ending owners remain separate from expression homonyms'
    for response in browser['responses']:
        encoding, api = response['encoding'], response['api']
        raw = unicodedata.normalize(encoding, ' '.join(case['surface'] for case, _ in cases)).encode()
        cursor = 0
        for record in api['records']:
            assert record['span']['start'] == cursor and raw[cursor:record['span']['end']].decode() == record['surface'], 'all original browser input bytes and spans'
            cursor = record['span']['end']
        assert cursor == len(raw), 'complete original browser sentence'
        assert 'ending.willingness_question' in api['rules'], 'new rule explanation present'
        indices = [i for i, r in enumerate(api['records']) if r['kind'] == 'word']
        assert len(indices) == len(cases), 'all original browser target words'
        for mode in ['raw', 'headword', 'compatible']:
            export = next(e for e in browser['exports'] if (e['encoding'], e['mode']) == (encoding, mode))
            assert export['records'] == [filtered(record, mode) for record in api['records']], 'every independently filtered complete export'
            for (case, judgment), record_index in zip(cases, indices, strict=True):
                record = api['records'][record_index]
                paths = record['analysis']['analyses']
                matching = [i for i, p in enumerate(paths) if matches(p, judgment)]
                assert matching, 'all independently typed browser decompositions'
                index = matching[0]
                path = paths[index]
                offered = [str(i) for i in kept_indices(record, mode)]
                assert str(index) in offered, 'original required path offered by dictionary policy'
                case_id = case['id'] + '/' + judgment.get('id', 'path')
                expected_decisions.append({'case_id': case_id, 'encoding': encoding, 'mode': mode, 'record_index': record_index, 'raw_analysis_index': index, 'analysis': path, 'allowed': True, 'offered_indices': offered})
                expected_diagrams.append((case_id, encoding, mode, path, [judgment['lemmas'][0][:-1], *judgment['morphemes']]))
    assert browser['policyDecisions'] == expected_decisions and len(expected_decisions) == 90, 'all original reading dropdown policies'
    assert len(browser['diagrams']) == len(expected_diagrams) == 90, 'all original browser diagrams'
    for diagram, expected in zip(browser['diagrams'], expected_diagrams, strict=True):
        assert (diagram['case_id'], diagram['encoding'], diagram['mode'], diagram['analysis'], diagram['forms']) == expected, 'all independently typed display components and order'
        assert not diagram['references'] and all(str(source['id']) in diagram['source_hint'] for source in label['sources']), 'original ending source ownership displayed'
    assert not browser['spacingDiagrams'], 'separate missing-space scope'
    assert len(v['native']) == len(browser['nativeEntries']) == 29 and {r['id']: r['entry'] for r in browser['nativeEntries']} == v['native'], 'every complete original Native endpoint field'
    return {'state': 'original-willingness-prototype-browser-audit-passed',
            'required_paths': 15, 'decisions': 90, 'diagrams': 90, 'exports': 6,
            'native_owners': 29, 'installed_new_family_verified': False,
            'contextual_review_complete': False, 'full_coverage_complete': False}


if __name__ == '__main__':
    print(json.dumps(inspect(inputs()), ensure_ascii=False, indent=2))
