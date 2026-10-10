"""Check independent long-command targets against preserved original Native data."""
import gzip
import hashlib
import json
from pathlib import Path

import gentle_command_source_audit as prior
from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
SOURCE_SHA = 'df50f05b5812862492e592680a93dad18a6ad79affa0ca8c8f8b8eb9217f279c'
BASELINE_SHA = 'edce41eef831d9823deca5986768013d89a12f808f9f8f96df44031ccdf0808d'
SUITE_SHA = 'd5440ac1a4801573e78eca3a5fdd98544c1e548a9cd5b7733d3c3060bd1c3668'
HEADS = {'오다', '살다', '먹다', '듣다', '돕다', '짓다', '낫다', '예쁘다',
         '학생', '이다', '-답다', '묻다', '보다', '물어보다'}


def preserved(name, digest):
    raw = (ROOT / 'docs' / name).read_bytes()
    assert sha(raw) == digest, 'original source/baseline manifest bytes'
    values = {}
    for name, item in json.loads(raw)['files'].items():
        archive = (ROOT / 'docs' / item['path']).read_bytes()
        assert sha(archive) == item['archive_sha256'], 'original source/baseline archive bytes'
        original = archive if name.endswith('.gz') else gzip.decompress(archive)
        assert sha(original) == item['source_sha256'], 'original source/baseline payload bytes'
        values[name] = original
    return values


def inputs():
    source = preserved('gentle-command-long-source-proof-archive.json', SOURCE_SHA)
    baseline = preserved('gentle-command-long-baseline-proof-archive.json', BASELINE_SHA)
    fixtures = ROOT / 'tests/fixtures'
    read = lambda name: json.loads((fixtures / name).read_bytes())
    return dict(originals=source, baseline_raw=baseline['gentle-command-long-installed-baseline.json.gz'],
                source_raw=(fixtures / 'gentle-command-long-source.json').read_bytes(),
                suite_raw=(fixtures / 'gentle-command-long-validity.json').read_bytes(),
                suite=read('gentle-command-long-validity.json'),
                interactions_raw=(fixtures / 'gentle-command-class-interaction-validity.json').read_bytes(),
                interactions=read('gentle-command-class-interaction-validity.json'),
                novel_packet_raw=(ROOT / 'docs/gentle-command-long-runtime-proof-gentle-command-long-novel-targets.json.gz').read_bytes(),
                novel_suite_raw=(fixtures / 'gentle-command-long-novel-validity.json').read_bytes(),
                novel_entries=read('gentle-command-long-novel-native-entries.json'),
                novel_extra_native=read('gentle-command-long-novel-boundary-native.json'),
                novel_extra_entries=read('gentle-command-long-novel-boundary-native-entries.json'),
                native=read('gentle-command-long-native.json'),
                entries=read('gentle-command-long-native-entries.json'),
                boundary_native=read('gentle-command-long-boundary-native.json'),
                boundary_entries=read('gentle-command-long-boundary-native-entries.json'),
                ending_native=read('gentle-command-long-ending-native.json'),
                prior_paths=read('gentle-command-long-prior-paths.json'),
                baseline=json.loads(gzip.decompress(baseline['gentle-command-long-installed-baseline.json.gz'])),
                label=json.loads((ROOT / 'web/src/grammar-labels.json').read_bytes())['-으려무나'],
                prior=prior.inputs())


def inspect(v):
    prior.inspect(v['prior'])
    original = v['originals']
    manifest_raw = (ROOT / 'docs/gentle-command-long-source-proof-archive.json').read_bytes()
    assert sha(manifest_raw) == SOURCE_SHA, 'original source manifest cannot be refreshed'
    files = json.loads(manifest_raw)['files']
    assert set(original) == set(files) and all(sha(original[name]) == item['source_sha256']
                                             for name, item in files.items()), 'all original source payload bytes'
    baseline_manifest = (ROOT / 'docs/gentle-command-long-baseline-proof-archive.json').read_bytes()
    assert sha(baseline_manifest) == BASELINE_SHA, 'original baseline manifest cannot be refreshed'
    assert sha(v['baseline_raw']) == json.loads(baseline_manifest)['files']['gentle-command-long-installed-baseline.json.gz']['source_sha256'], 'exact original baseline payload bytes'
    assert v['source_raw'] == original['gentle-command-long-original-source.json'], 'complete original source fixture'
    source = json.loads(v['source_raw'])
    assert not source['observed_runtime'] and not source['linguistic_judgments_promoted'], 'original targets precede candidate observation'
    assert sha(v['suite_raw']) == SUITE_SHA, 'exact independently authored25 judgments'
    assert v['suite'] == json.loads(v['suite_raw']), 'every original private judgment field'
    assert sha(v['interactions_raw']) == '655f08927753cc454373a47dff559e77b08b1afc80cc46c84bdf2abbd8bd5026', 'exact additional derived-class judgments'
    assert v['interactions'] == json.loads(v['interactions_raw']), 'actual nominal-plus-suffix target fields'
    suite = v['suite']
    assert len(suite['cases']) == 25, 'bounded25-case scope'
    assert {kind: sum(j['verdict'] == kind for case in suite['cases'] for j in case['judgments'])
            for kind in ['required', 'forbidden']} == {'required': 16, 'forbidden': 9}, 'independent verdict counts'
    assert len(source['items']) == 8 and source['ending_owner_ids'] == ['krdict:79266', 'krdict:79265'], 'both original ending owners and all8 groups'
    for item, case in zip(source['items'], suite['cases'][:8], strict=True):
        target = item['independent_typed_proposal']
        assert item['id'] == case['id'] and item['surface'] == case['surface'], 'all original isolated structural targets'
        assert all(case['judgments'][0][key] == value for key, value in target.items()), 'independent typed target fields'
        assert case['judgments'][0]['required_rules'] == ['ending.gentle_command_long'], 'separate ending provenance'
    closure = json.loads(gzip.decompress(original['gentle-command-long-original-native-closure.json.gz']))
    assert v['native'] == json.loads(original['gentle-command-long-native.json']), 'every original source Native field/order'
    assert v['entries'] == closure['complete_imported_entries'] == json.loads(original['gentle-command-long-native-entries.json']), 'every original imported source field/homonym'
    native = v['native']['LexicalResource']['Lexicon']['LexicalEntry']
    assert len(native) == 16 and {e['id']: e for e in map(entry, native)} == v['entries'], 'all16 original source owners'
    expected = {ident: owner for entries in v['prior']['entries'] for ident, owner in entries.items()
                if owner['headword'] in HEADS and ident not in v['entries']}
    assert v['boundary_entries'] == expected and len(expected) == 27, 'every inherited boundary field/homonym'
    expected_native = [owner for group in v['prior']['native']
                       for owner in group['LexicalResource']['Lexicon']['LexicalEntry']
                       if 'krdict:' + owner['val'] in expected]
    assert v['boundary_native']['LexicalResource']['Lexicon']['LexicalEntry'] == expected_native, 'all27 original boundary Native fields/order'
    assert {e['id']: e for e in map(entry, expected_native)} == expected, 'all boundary import projections'
    assert sha(v['novel_packet_raw']) == '3267cd77c36f3adea700eeb76426c177b83cb00379748079e266f5c2a611620f', 'exact original novel occurrence packet'
    novel = json.loads(gzip.decompress(v['novel_packet_raw']))
    manifest_raw = (ROOT / 'docs/gentle-command-long-runtime-proof-archive.json').read_bytes()
    assert sha(manifest_raw) == 'a38f4bd748e734ca314d908bc24676e551e6cb815a923fc3075c879726a4da31', 'exact novel runtime archive manifest'
    item = json.loads(manifest_raw)['files']['gentle-command-long-novel-validity.json']
    assert sha(v['novel_suite_raw']) == item['source_sha256'], 'exact eight bounded novel proposals'
    assert not novel['proposals_precede_runtime'] and len(novel['items']) == 8, 'honest post-observation novel scope'
    assert v['novel_entries'] == novel['complete_imported_entries'] and len(v['novel_entries']) == 15, 'all fifteen complete novel Native owners'
    extra = {ident: owner for ident, owner in v['novel_entries'].items() if ident not in v['entries'] and ident not in expected}
    assert v['novel_extra_entries'] == extra and len(extra) == 5, 'five exact additional lexical owners'
    extra_native = [owner for ident, owner in novel['original_native_entries'].items() if ident in extra]
    assert v['novel_extra_native']['LexicalResource']['Lexicon']['LexicalEntry'] == extra_native, 'all five additional original Native records'
    endings = [owner for owner in native if 'krdict:' + owner['val'] in source['ending_owner_ids']]
    assert v['ending_native']['LexicalResource']['Lexicon']['LexicalEntry'] == endings and len(endings) == 2, 'catalog fixture has both exact ending owners'
    assert v['label']['kind'] == 'ending' and v['label']['label'] == 'Gentle command / permission' and v['label']['sources'] == [
        {'id': 79266, 'headword': '-려무나', 'pos': '어미'},
        {'id': 79265, 'headword': '-으려무나', 'pos': '어미'}], 'label owns only the two original long endings'
    baseline = v['baseline']
    assert baseline == json.loads(gzip.decompress(v['baseline_raw'])), 'unchanged actual prior baseline observations'
    assert baseline['inputs_unchanged'] and baseline['streams'] == 24 and baseline['frames'] == 1512, 'complete24-policy prior baseline'
    assert not baseline['linguistic_judgments_promoted'], 'prior observation does not promote linguistic judgments'
    observations = next(run['observations'] for run in baseline['runs']
                        if run['encoding'] == 'NFC' and run['mode'] == 'raw' and run['cache_bytes'] == 0)
    assert v['prior_paths'] == observations and len(observations) == 8, 'all8 full original baseline records retained'
    return dict(state='independent-long-gentle-source-and-baseline-passed', cases=25, required=16,
                forbidden=9, source_groups=8, native_owners=43, prior_streams=24, prior_frames=1512,
                extra_interaction_cases=3, extra_required=1, extra_forbidden=2,
                extra_novel_cases=8, complete_novel_native_owners=15,
                contextual_and_independent_review='pending', full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
