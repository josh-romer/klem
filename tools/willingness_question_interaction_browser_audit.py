"""Preserve original and authored interaction dropdowns, Native owners and typed order."""
import gzip
import json
import hashlib
import signal
import unicodedata
from pathlib import Path
from willingness_question_browser_audit import matches, filtered, kept_indices
ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def read(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()) if str(path).endswith('.gz') else Path(path).read_bytes())
def inputs():
    docs = ROOT / 'docs'
    proof = lambda name: read(docs / ('willingness-question-interaction-browser-proof-' + name + '.gz'))
    return {'binding': read(docs / 'willingness-question-installed-proof-willingness-installed-source-binding-retry1.json.gz'),
            'binding_raw': gzip.decompress((docs / 'willingness-question-installed-proof-willingness-installed-source-binding-retry1.json.gz').read_bytes()),
            'runtime': proof('willingness-interaction-installed-browser-runtime.json'),
            'browser': proof('willingness-interaction-installed-browser.json'),
            'driver': gzip.decompress((docs / 'willingness-question-interaction-browser-proof-willingness-interaction-installed-browser.mjs.gz').read_bytes()),
            'supervisor': gzip.decompress((docs / 'willingness-question-interaction-browser-proof-run_willingness_interaction_installed_browser.py.gz').read_bytes()),
            'suites': [read(ROOT / 'tests/fixtures' / name) for name in ['willingness-question-validity.json', 'willingness-question-boundary-validity.json', 'willingness-question-interaction-validity.json']],
            'label': read(ROOT / 'web/src/grammar-labels.json')['-으련'],
            'native': read(ROOT / 'tests/fixtures/willingness-question-native-entries.json'),
            'full_rust': read(docs / 'willingness-question-interaction-proof-willingness-interaction-full-rust.json.gz')}


def inspect_production_binding(v):
    full, binding = v['full_rust'], v['binding']
    assert full['state'] == 'passed' and full['exit_code'] == 0 and all(full[k] for k in ['inputs_unchanged', 'head_unchanged', 'index_unchanged']), 'complete frozen interaction Rust validation'
    assert full['totals'] == {'passed': 1176, 'failed': 0, 'ignored': 1} and full['batches'] == 252, 'complete interaction Rust totals'
    different = set()
    for profile in binding['profiles'].values():
        for record in profile['files'].values():
            path = '/tmp/klem-willingness-interactions/' + record['snapshot_path']
            assert path in full['frozen_inputs'], 'every original package file in the complete current source snapshot'
            if full['frozen_inputs'][path] != record['sha256']:
                different.add(record['snapshot_path'])
    assert different == {'tests/fixtures/validity.json', 'tests/validity.rs', 'tests/willingness_question.rs'}, 'only three inherited compiled-test files differ from installed production'
    assert full['frozen_inputs']['/tmp/klem-willingness-interactions/tests/fixtures/willingness-question-interaction-validity.json'] == '529f6614d742d6606f1b3e5f66c9df3a769cd698a6b92ee90eb276b09f438de3', 'exact new interaction fixture outside the inherited package profile'

def inspect_browser(v):
    b, runtime, browser = v['binding'], v['runtime'], v['browser']
    assert browser['state'] == 'installed-willingness-interaction-browser-passed' and not browser['errors'] and browser['producer_sha256'] == sha(v['driver']), 'actual error-free installed browser'
    assert runtime['state'] == 'passed' and runtime['exit_code'] == 0 and runtime['inputs_unchanged'] and runtime['server_stopped'] and runtime['server_exit_code'] in [0, -signal.SIGINT], 'owned installed server stopped'
    command = runtime['command']
    assert runtime['binding_sha256'] == sha(v['binding_raw']) and command[:3] == [b['launcher']['package'] + '/bin/klem-web', '--port', '0'] and command[3] == '--dictionary' and command[4] in runtime['frozen_inputs'], 'actual installed browser launcher'
    assert command[0] in runtime['frozen_inputs'] and b['profiles']['klem']['package'] + '/bin/klem' in runtime['frozen_inputs'] and b['profiles']['klem']['package'] + '/bin/klem-web' in runtime['frozen_inputs'], 'actual installed browser binaries'
    assert sha(v['driver']) in runtime['frozen_inputs'].values() and sha(v['supervisor']) in runtime['frozen_inputs'].values(), 'actual frozen browser producers'
    assert sha(runtime['producer']['text'].encode()) == runtime['producer']['sha256'] == sha(v['supervisor']), 'actual installed browser supervisor'
    assets = b['profiles']['web-assets']['package'] + '/share/klem-web/'
    assert assets + 'index.html' in runtime['frozen_inputs'] and any(p.startswith(assets + 'assets/') and p.endswith('.js') for p in runtime['frozen_inputs']), 'actual installed frontend assets'
    # Apply the original independent typed-path/display/export checks directly;
    # never invent prototype build identities for an installed browser.
    inspect_browser_choices(v)


def inspect_browser_choices(v):
    browser = v['browser']
    cases = [(case, j) for suite in v['suites'] for case in suite['cases'] for j in case['judgments'] if j['verdict'] == 'required']
    assert len(cases) == 19, 'all independent source and boundary paths'
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
                heads = [head[:-1] if kind in ['predicate', 'auxiliary', 'copula'] and head.endswith('다') else head for head, kind in zip(judgment['lemmas'], judgment['lemma_kinds'], strict=True)]
                forms = [heads[0], *judgment['morphemes']] if len(heads) == 1 else [heads[0], judgment['morphemes'][0], heads[1], *judgment['morphemes'][1:]]
                expected_diagrams.append((case_id, encoding, mode, path, forms))
    assert browser['policyDecisions'] == expected_decisions and len(expected_decisions) == 114, 'all original reading dropdown policies'
    assert len(browser['diagrams']) == len(expected_diagrams) == 114, 'all original browser diagrams'
    for diagram, expected in zip(browser['diagrams'], expected_diagrams, strict=True):
        assert (diagram['case_id'], diagram['encoding'], diagram['mode'], diagram['analysis'], diagram['forms']) == expected, 'all independently typed display components and order'
        assert not diagram['references'] and all(str(source['id']) in diagram['source_hint'] for source in label['sources']), 'original ending source ownership displayed'
    assert not browser['spacingDiagrams'], 'separate missing-space scope'
    assert len(v['native']) == len(browser['nativeEntries']) == 29 and {r['id']: r['entry'] for r in browser['nativeEntries']} == v['native'], 'every complete original Native endpoint field'


def inspect(v):
    inspect_production_binding(v)
    inspect_browser(v)
    return {'state': 'independent-installed-willingness-interaction-browser-passed', 'required_paths':19, 'decisions':114, 'diagrams':114, 'exports':6, 'native_owners':29, 'full_coverage_complete':False, 'scope':'Actual7dfparent installed runtime with production source bytes verified against the complete1176-test interaction Rust snapshot. Three changed existing test files and one new fixture remain outside the inherited Nix test profile. New test-profile Nix/main/timing/contextual and independent review remain separate.'}
if __name__ == '__main__':
    print(json.dumps(inspect(inputs()), ensure_ascii=False, indent=2))
