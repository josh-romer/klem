"""Verify complete -시 sources, finite licenses, immutable parents and tracked changes."""
import argparse
import copy
import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

from native_lmf import verify_native_lmf
from well_doeda_audit import MODES, ROOT, digest, read, sha, word_records

SOURCE = ROOT / 'docs/nominal-si-preflight.json.gz'
FIXTURE = ROOT / 'tests/fixtures/nominal-si-sources.json'
LMF = ROOT / 'tests/fixtures/krdict-nominal-si.json'
REPORT = ROOT / 'docs/nominal-si-diagnostics.json.gz'
RULE = 'suffix.nominal.si'


def inspect_source(source):
    assert source['schema_version'] == 1 and source['checklist'] == 'COV-022o'
    assert source['before_cli_sha256'] == read(ROOT / 'docs/well-doeda-packaged-checks.json.gz')['cli_sha256']
    assert source['reviewer'] == 'agent' and source['independent_review'] == 'pending'
    assert source['contextual_verdict'] == 'unjudged'
    native = source['complete_native_entries']
    assert len(native) == 44
    suffix = native[source['primary_nominal_suffix']]
    assert (suffix['id'], suffix['headword'], suffix['pos'], suffix['origins']) == ('krdict:71567', '-시', '접사', ['視'])
    assert suffix['notes'] == ['일부 명사 뒤에 붙는다.']
    examples = [t for s in suffix['senses'] for group in s['examples'] for t in group]
    assert len(examples) == len(set(examples)) == 10
    passive = native[source['primary_passive_suffix']]
    assert (passive['id'], passive['headword'], passive['pos']) == ('krdict:74902', '-되다', '접사')
    assert len(passive['senses']) == 2
    assert [f['head'] for f in source['families']] == examples
    nominal, derived = [], []
    for family in source['families']:
        head, base = family['head'], family['base']
        assert head == base + '시'
        for field, spelling in [('base_ids', base), ('whole_nominal_ids', head),
                                ('whole_passive_ids', head + '되다'), ('whole_hada_ids', head + '하다')]:
            assert family[field] == [ident for ident, e in native.items() if e['headword'] == spelling]
        noun = any(native[i]['pos'] == '명사' and native[i]['origins'] for i in family['base_ids'])
        verb = noun and any(native[i]['pos'] == '동사' and any(o.endswith('視되다') for o in native[i]['origins']) for i in family['whole_passive_ids'])
        assert family['nominal_supported'] == noun and family['passive_supported'] == verb
        if noun:
            nominal.append(base)
        if verb:
            derived.append(base)
            noun_origins = {o for i in family['base_ids'] for o in native[i]['origins']}
            assert all(o.removesuffix('視되다') in noun_origins for i in family['whole_passive_ids'] for o in native[i]['origins'])
    assert nominal == ['동일', '문제', '야만', '의문', '적대', '죄악', '중요']
    assert derived == ['동일', '문제', '의문', '죄악', '중요']
    assert sha(LMF) == source['lmf_sha256']
    verify_native_lmf(read(LMF), native)
    verify_native_lmf(read(ROOT / 'tests/fixtures/krdict-nominal-si-labels.json'), {'krdict:71567':suffix})
    fixture = read(FIXTURE)
    assert fixture['source_sha256'] == sha(SOURCE)
    for field in ['families', 'corpora', 'complete_native_entries']:
        assert fixture[field] == source[field]
    ledger = read(ROOT / 'tests/fixtures/validity.json')
    assert [c for c in ledger['cases'] if c['id'].startswith('nominal-si-')] == fixture['cases']
    assert ledger['sources']['nominal-si-krdict'] == suffix['url']
    cases = fixture['cases']
    assert len(cases) == len({c['id'] for c in cases}) == 210
    assert sum(c['judgments'][0]['verdict'] == 'required' for c in cases) == 200
    assert len(source['words']) == len(set(source['words'])) == 252
    assert source['input'] == ' '.join(source['words'])
    assert set(source['before']) == set(MODES)
    for mode, run in source['before'].items():
        assert run['exit_code'] == 0 and hashlib.sha256(run['jsonl'].encode()).hexdigest() == run['sha256']
        records, words = word_records(run['jsonl'])
        assert ''.join(r['surface'] for r in records) == source['input']
        assert set(words) == set(source['words'])
        assert all(RULE not in a['rules'] for r in words.values() for a in r['analysis']['analyses'])
        if mode == 'raw':
            assert fixture['before_analyses'] == {w: r['analysis'] for w, r in words.items()}
    rows = []
    assert len(source['corpora']) == 6
    for corpus in source['corpora']:
        path = ROOT / corpus['source']
        if path.exists():
            assert sha(path) == corpus['sha256']
        for row in corpus['rows']:
            assert len(row['original_row']) == 10
            assert '\t'.join(row['original_row']) in row['complete_sentence'].splitlines()
            if path.exists():
                assert row['complete_sentence'] in path.read_text()
            rows.append(row)
    assert len(rows) == 34
    assert any(r['original_lemma'] == '문제시+하+지+도' for r in rows)
    assert hashlib.sha256(source['producer']['text'].encode()).hexdigest() == source['producer']['sha256']
    return len(cases), len(source['words']), len(native), len(rows)


def inspect_comparison(source, report):
    assert report['source_sha256'] == sha(SOURCE)
    assert report['fixture_sha256'] == sha(FIXTURE)
    assert report['before_cli_sha256'] == source['before_cli_sha256']
    assert report['dictionary_sha256'] == source['dictionary_sha256']
    assert set(report['runs']) == set(MODES)
    changes = []
    native = source['complete_native_entries']
    _, raw_before = word_records(source['before']['raw']['jsonl'])
    for mode, runs in report['runs'].items():
        assert set(runs) == {'NFC-cached', 'NFC-uncached', 'NFD-cached', 'NFD-uncached'}
        _, before = word_records(source['before'][mode]['jsonl'])
        parity = None
        for encoding_cache, run in runs.items():
            assert run['exit_code'] == 0
            assert hashlib.sha256(run['jsonl'].encode()).hexdigest() == run['sha256']
            records, after = word_records(run['jsonl'])
            assert set(after) == set(before)
            assert ''.join(r['surface'] for r in records) == unicodedata.normalize(encoding_cache.split('-')[0], source['input'])
            values = {w: (r['analysis'], r['dictionary']) for w, r in after.items()}
            if parity is None:
                parity = values
            else:
                assert values == parity
        for word, record in after.items():
            old, new = before[word]['analysis']['analyses'], record['analysis']['analyses']
            assert [a for a in new if RULE not in a['rules']] == old, word
            for i, a in enumerate(new):
                reading = record['dictionary']['readings'][i]
                if RULE not in a['rules']:
                    assert reading == before[word]['dictionary']['readings'][old.index(a)], word
                    continue
                assert a['lemmas'][0]['kind'] == 'nominal'
                assert a['morphemes'][0] == {'form': '시', 'kind': 'suffix'}
                base = a['lemmas'][0]['text']
                assert base in ['동일', '문제', '야만', '의문', '적대', '죄악', '중요']
                nested = len(a['morphemes']) > 1 and a['morphemes'][1] == {'form': '되다', 'kind': 'suffix'}
                if nested:
                    assert base in ['동일', '문제', '의문', '죄악', '중요']
                    assert 'suffix.verb.doeda' in a['rules']
                parents = []
                for count, kind, head in [(1, 'nominal', base + '시'),
                                          (2, 'predicate', base + '시되다')]:
                    if count == 2 and not nested:
                        continue
                    parent = copy.deepcopy(a)
                    parent['lemmas'][0] = {'text':head,'kind':kind}
                    parent['morphemes'] = parent['morphemes'][count:]
                    for path in parent.get('spelling_paths', []):
                        assert all(r['morpheme_index'] >= count for r in path)
                        for recovery in path:
                            recovery['morpheme_index'] -= count
                    parents.extend(p for p in raw_before[word]['analysis']['analyses'] if {k:v for k,v in p.items() if k != 'rules'} == {k:v for k,v in parent.items() if k != 'rules'})
                if not parents:
                    # Bare nouns have only an identity candidate before adding
                    # the finite derivation; their license is the source example.
                    assert not nested and a['morphemes'] == [{'form':'시','kind':'suffix'}]
                    assert a['lemmas'] == [{'text':base,'kind':'nominal'}]
                    assert word == base + '시' and a['rules'] == [RULE]
                else:
                    allowed = {r for p in parents for r in p['rules']} | {RULE}
                    if nested:
                        allowed.add('suffix.verb.doeda')
                    assert set(a['rules']) <= allowed
                for entry in reading['lemmas'][0]['entries']:
                    identity = entry.get('derivational_identity')
                    if identity is None:
                        continue
                    assert nested and identity['morpheme_index'] == 1
                    assert all(native[i]['headword'] == base + '시되다' for i in identity['whole_entries'])
                    assert identity['expected_origins'] == [o.removesuffix('視되다') for i in identity['whole_entries'] for o in native[i]['origins']]
                changes.append({'id':'nominal-si-change-'+digest([mode,word,a]),'mode':mode,
                                'surface':word,'analysis':a,'reading':reading,
                                'contextual_verdict':'unjudged','independent_review':'pending'})
    assert report['changes'] == changes
    return len(changes)


def capture(cli, output):
    import gzip
    assert not output.exists()
    source = read(SOURCE)
    inspect_source(source)
    report = {'schema_version':1,'checklist':'COV-022o','source_sha256':sha(SOURCE),
              'fixture_sha256':sha(FIXTURE),'before_cli_sha256':source['before_cli_sha256'],
              'cli_sha256':sha(cli),'dictionary_sha256':sha(ROOT/'data/dictionaries/krdict/krdict.db'),
              'runs':{},'changes':[]}
    for mode, flags in MODES.items():
        report['runs'][mode] = {}
        for encoding in ['NFC','NFD']:
            for cache, budget in [('cached','8388608'),('uncached','0')]:
                command = [str(cli),'text','-','--dictionary',str(ROOT/'data/dictionaries/krdict/krdict.db'),*flags,'--cache-bytes',budget]
                result = subprocess.run(command,input=unicodedata.normalize(encoding,source['input']),text=True,capture_output=True,check=True)
                report['runs'][mode][encoding+'-'+cache] = {'command':command,'exit_code':result.returncode,
                    'jsonl':result.stdout,'sha256':hashlib.sha256(result.stdout.encode()).hexdigest()}
        _, words = word_records(report['runs'][mode]['NFC-cached']['jsonl'])
        for word, record in words.items():
            for i,a in enumerate(record['analysis']['analyses']):
                if RULE in a['rules']:
                    report['changes'].append({'id':'nominal-si-change-'+digest([mode,word,a]),'mode':mode,
                        'surface':word,'analysis':a,'reading':record['dictionary']['readings'][i],
                        'contextual_verdict':'unjudged','independent_review':'pending'})
    with gzip.GzipFile(filename=str(output),mode='wb',mtime=0) as stream:
        stream.write((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    inspect_comparison(source,report)
    return len(report['changes'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--cli',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--comparison',type=Path)
    args=parser.parse_args()
    if args.verify:
        source=read(SOURCE);print('Verified source/words/native/corpus:',inspect_source(source))
        if args.comparison:
            print('Verified candidate and reading changes:',inspect_comparison(source,read(args.comparison)))
    else:
        assert args.cli and args.output
        print('Captured individually tracked changes:',capture(args.cli.resolve(),args.output))
