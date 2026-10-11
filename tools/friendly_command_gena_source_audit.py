"""Verify independently authored -게나 targets, full Native data and old runtime paths."""
import gzip
import hashlib
import itertools
import json
import unicodedata
from pathlib import Path

from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SHA = '2fdf16ccdc41566bf197cc7f068462ddf2d5d0e805730bcb0d16085e79a2261b'
SUITE_SHA = '52dc5dae1dd3218c049be2a5f7f89e741fd9b166177102bf361892584188ed3b'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def inputs():
    raw = (ROOT / 'docs/friendly-command-gena-source-baseline-proof-archive.json').read_bytes()
    assert sha(raw) == MANIFEST_SHA, 'original source/baseline manifest bytes'
    originals = {}
    for name, item in json.loads(raw)['files'].items():
        packed = (ROOT / 'docs' / item['path']).read_bytes()
        assert sha(packed) == item['archive_sha256'], 'original packed artifact bytes'
        original = gzip.decompress(packed)
        assert sha(original) == item['source_sha256'], 'original source/baseline bytes'
        originals[name] = original
    fixtures = ROOT / 'tests/fixtures'
    read = lambda name: json.loads((fixtures / name).read_bytes())
    return dict(originals=originals, source=read('friendly-command-gena-source.json'),
                suite_raw=(fixtures / 'friendly-command-gena-validity.json').read_bytes(),
                suite=read('friendly-command-gena-validity.json'),
                native=read('friendly-command-gena-native.json'),
                entries=read('friendly-command-gena-native-entries.json'),
                ending_native=read('friendly-command-gena-ending-native.json'),
                prior_paths=read('friendly-command-gena-prior-paths.json'),
                captures=json.loads(gzip.decompress(originals['friendly-command-gena-baseline-records.json.gz'])),
                label=json.loads((ROOT / 'web/src/grammar-labels.json').read_bytes())['-게나'])


def inspect(v):
    original = v['originals']
    manifest = json.loads((ROOT / 'docs/friendly-command-gena-source-baseline-proof-archive.json').read_bytes())
    assert set(original) == set(manifest['files']) and all(sha(original[n]) == item['source_sha256'] for n,item in manifest['files'].items()), 'all immutable original payloads'
    author = json.loads(original['friendly-command-gena-source-authoring.json'])
    assert v['source'] == author, 'complete original source and pre-runtime target fields'
    assert not author['candidate_runtime_observed'] and not author['shared_cases_reviews_changed'], 'targets authored before targeted runtime'
    assert sha(v['suite_raw']) == SUITE_SHA and v['suite_raw'] == original['friendly-command-gena-validity.json'], 'all24 exact independent judgments'
    assert v['suite'] == json.loads(v['suite_raw']), 'current judgment fields'
    cases = v['suite']['cases']
    assert len(cases) == 24 and {kind:sum(c['judgments'][0]['verdict']==kind for c in cases) for kind in ['required','forbidden']} == {'required':17,'forbidden':7}, 'complete finite scope'
    owner = author['owners']['krdict:66968']
    assert owner['headword'] == '-게나' and len(owner['senses']) == 1 and len(owner['senses'][0]['examples']) == 4, 'single original owner and all groups'
    assert len(author['items']) == 4 and author['owner_ids'] == ['krdict:66968'], 'four original lexical targets'
    for item, case, group in zip(author['items'],cases[:4],owner['senses'][0]['examples'],strict=True):
        assert item['complete_original_group'] == group and item['typed_target'] == case['judgments'][0] and item['id'] == case['id'] and item['surface'] == case['surface'], 'original full groups/typed targets'
        span=item['local_span'];assert '\n'.join(group).encode()[span['start']:span['end']].decode() == item['surface'], 'original UTF-8 occurrence span'
    closure = json.loads(gzip.decompress(original['friendly-command-gena-original-native-closure.json.gz']))
    assert len(closure['source_exports']) == 11 and len(closure['complete_native_entries']) == 31, 'original full export closure'
    assert v['entries'] == closure['complete_native_entries'], 'every complete Native field and homonym'
    assert v['native']['LexicalResource']['Lexicon']['LexicalEntry'] == list(closure['original_lmf'].values()), 'complete original LMF/order'
    assert {e['id']:e for e in map(entry,v['native']['LexicalResource']['Lexicon']['LexicalEntry'])} == v['entries'], 'independent Native import projection'
    assert v['ending_native']['LexicalResource']['Lexicon']['LexicalEntry'] == [closure['original_lmf']['krdict:66968']], 'catalog uses only the own ending entry'
    assert v['label']['kind'] == 'ending' and v['label']['label'] == 'Friendly command' and v['label']['sources'] == [{'id':66968,'headword':'-게나','pos':'어미'}], 'attributed ending label'
    captures = v['captures']
    assert captures == json.loads(gzip.decompress(original['friendly-command-gena-baseline-records.json.gz'])), 'full original runtime output/assessment bytes'
    baseline = json.loads(original['friendly-command-gena-baseline.json'])
    assert baseline['state'] == 'passed' and baseline['inputs_unchanged'] and baseline['runs'] == 36 and baseline['complete_native_owners'] == 31, 'actual installed baseline scope'
    assert baseline['typed_path_matches'] == 0 and baseline['future_rule_path_matches'] == 0, 'canonical path check independent of future rule ID'
    assert {k:v['response']['entry'] for k,v in captures['native_entries'].items()} == v['entries'], 'all31 actual CLI Native responses'
    policies = set(itertools.product(['complete-original-groups','preauthored-24-proposals','unjudged-lexical-prefinal-boundaries'],['NFC','NFD'],['all','headwords','compatible'],[0,4096]))
    assert len(captures['captures']) == 36 and {(c['family'],c['normalization'],c['mode'],c['cache_bytes']) for c in captures['captures']} == policies, 'every actual baseline policy'
    for capture in captures['captures']:
        assert [json.loads(line) for line in capture['stdout'].splitlines()] == capture['frames'], 'complete original frames/order'
        raw = capture['input'].encode(); cursor=0
        for frame in capture['frames']:
            span=frame['span'];assert span['start']==cursor and raw[span['start']:span['end']].decode()==frame['surface'], 'original UTF-8/NFD spans';cursor=span['end']
        assert cursor==len(raw), 'whole original text covered'
        for observation in capture['observations']:
            case=next(c for c in cases if c['id']==observation['case_id']);j=case['judgments'][0]
            frame=next(f for f in capture['frames'] if f['span']==observation['span'])
            assert unicodedata.normalize('NFC',frame['surface'])==case['surface'], 'typed observation surface'
            def matches(a):
                return [l['text'] for l in a['lemmas']]==j['lemmas'] and [l['kind'] for l in a['lemmas']]==j['lemma_kinds'] and [m['form'] for m in a['morphemes']]==j['morphemes'] and [m['kind'] for m in a['morphemes']]==j['morpheme_kinds']
            assert observation['typed_path_present']==any(matches(a) for a in frame['analysis']['analyses']), 'canonical path existence independent of provenance'
    prior=[f for c in captures['captures'] if c['normalization']=='NFC' and c['mode']=='all' and c['cache_bytes']==0 for f in c['frames'] if f['kind']=='word']
    assert v['prior_paths']==prior and len(prior)==59, 'every original raw word/path/assessment/order retained'
    return dict(source_groups=4,private_cases=24,required=17,forbidden=7,full_native_owners=31,baseline_runs=36,prior_word_records=59,context_register_independent_review='pending',full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
