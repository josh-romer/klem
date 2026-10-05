"""Verify complete -화 sources, finite licenses, immutable parents and tracked changes."""
import argparse
import copy
import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

from native_lmf import verify_native_lmf
from well_doeda_audit import MODES, ROOT, digest, read, sha, word_records

SOURCE = ROOT / 'docs/nominal-hwa-preflight.json.gz'
FIXTURE = ROOT / 'tests/fixtures/nominal-hwa-sources.json'
LMF = ROOT / 'tests/fixtures/krdict-nominal-hwa.json'
REPORT = ROOT / 'docs/nominal-hwa-diagnostics.json.gz'
RULE = 'suffix.nominal.hwa'



SUPPLEMENT = ROOT / 'docs/nominal-hwa-supplemental-preflight.json.gz'
def before_words(source, mode):
    _, original = word_records(source['before'][mode]['jsonl'])
    _, extra = word_records(read(SUPPLEMENT)['before'][mode]['jsonl'])
    assert not (original.keys() & extra.keys())
    return original | extra

def source_input(source):
    return source['input'] + ' ' + read(SUPPLEMENT)['input']


def inspect_source(source):
    assert source['schema_version'] == 1 and source['checklist'] == 'COV-022p'
    assert source['before_cli_sha256'] == read(ROOT / 'docs/nominal-si-packaged-checks.json.gz')['cli_sha256']
    assert source['reviewer'] == 'agent' and source['independent_review'] == 'pending'
    assert source['contextual_verdict'] == 'unjudged'
    native = source['complete_native_entries']
    assert len(native) == 164
    suffix = native[source['primary_nominal_suffix']]
    assert (suffix['id'], suffix['headword'], suffix['pos'], suffix['origins']) == ('krdict:88499', '-화', '접사', ['化'])
    assert suffix['notes'] == ['일부 명사 뒤에 붙는다.']
    examples = [t for s in suffix['senses'] for group in s['examples'] for t in group]
    assert len(examples) == len(set(examples)) == 38
    passive = native[source['primary_passive_suffix']]
    assert (passive['id'], passive['headword'], passive['pos']) == ('krdict:74902', '-되다', '접사')
    assert len(passive['senses']) == 2
    assert [f['head'] for f in source['families']] == examples
    nominal, derived = [], []
    for family in source['families']:
        head, base = family['head'], family['base']
        assert head == base + '화'
        for field, spelling in [('base_ids', base), ('whole_nominal_ids', head),
                                ('whole_passive_ids', head + '되다'), ('whole_hada_ids', head + '하다')]:
            assert family[field] == [ident for ident, e in native.items() if e['headword'] == spelling]
        noun_origins = {variant for i in family['base_ids'] if native[i]['pos'] == '명사' for origin in native[i]['origins'] for variant in origin.split('/')}
        whole_origins = {o.removesuffix('化') for i in family['whole_nominal_ids'] for o in native[i]['origins']}
        noun = any(native[i]['pos'] == '명사' for i in family['base_ids']) and (not family['whole_nominal_ids'] or bool(noun_origins & whole_origins))
        verb = noun and any(native[i]['pos'] == '동사' and any(o.endswith('化되다') for o in native[i]['origins']) for i in family['whole_passive_ids'])
        assert family['nominal_supported'] == noun and family['passive_supported'] == verb
        if noun:
            nominal.append(base)
        if verb:
            derived.append(base)
            noun_origins = {o for i in family['base_ids'] for o in native[i]['origins']}
            assert all(o.removesuffix('化되다') in noun_origins for i in family['whole_passive_ids'] for o in native[i]['origins'])
    assert nominal == ['가속', '가시', '개념', '개방', '개별', '객관', '격식', '내면', '내실', '노령', '민영', '민주', '보편', '상품', '생활', '온난', '이론', '이상', '일반', '일상', '제도', '조직', '최소', '토착', '특수', '표준', '합리', '황폐']
    assert derived == ['가속', '가시', '개방', '객관', '내면', '민영', '민주', '보편', '상품', '생활', '이론', '이상', '일반', '일상', '제도', '조직', '토착', '특수', '표준', '합리', '황폐']
    assert sha(LMF) == source['lmf_sha256']
    verify_native_lmf(read(LMF), native)
    verify_native_lmf(read(ROOT / 'tests/fixtures/krdict-nominal-hwa-labels.json'), {'krdict:88499':suffix})
    supplemental = read(SUPPLEMENT)
    assert supplemental['original_preflight_sha256'] == sha(SOURCE)
    assert supplemental['before_cli_sha256'] == source['before_cli_sha256']
    assert len(supplemental['words']) == len(set(supplemental['words'])) == 6
    assert supplemental['input'] == ' '.join(supplemental['words'])
    assert hashlib.sha256(supplemental['producer']['text'].encode()).hexdigest() == supplemental['producer']['sha256']
    for mode, run in supplemental['before'].items():
        assert run['exit_code'] == 0 and hashlib.sha256(run['jsonl'].encode()).hexdigest() == run['sha256']
        records, words = word_records(run['jsonl'])
        assert ''.join(r['surface'] for r in records) == supplemental['input']
        assert set(words) == set(supplemental['words'])
    fixture = read(FIXTURE)
    assert fixture['supplemental_sha256'] == sha(SUPPLEMENT)
    assert fixture['source_sha256'] == sha(SOURCE)
    for field in ['families', 'corpora', 'complete_native_entries']:
        assert fixture[field] == source[field]
    ledger = read(ROOT / 'tests/fixtures/validity.json')
    assert [c for c in ledger['cases'] if c['id'].startswith('nominal-hwa-')] == fixture['cases']
    assert ledger['sources']['nominal-hwa-krdict'] == suffix['url']
    cases = fixture['cases']
    assert len(cases) == len({c['id'] for c in cases}) == 583
    assert sum(c['judgments'][0]['verdict'] == 'required' for c in cases) == 546
    assert sum(c['judgments'][0]['verdict'] == 'forbidden' for c in cases) == 37
    for case in cases:
        judgment = case['judgments'][0]
        identity = {k: v for k, v in judgment.items() if k not in {'id', 'source'}}
        case_hash = hashlib.sha256(json.dumps([case['surface'], identity], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]
        assert case['id'] == 'nominal-hwa-' + case_hash
        assert judgment['id'] == case['id'] + '-structure'
        assert judgment['source'] == 'nominal-hwa-krdict'
        if judgment['verdict'] == 'required':
            assert judgment['lemmas'][0] in nominal
            assert judgment['lemma_kinds'][0] == 'nominal'
            assert judgment['morphemes'][0] == '화' and judgment['morpheme_kinds'][0] == 'suffix'
            assert RULE in judgment['required_rules']
            if 'suffix.verb.doeda' in judgment['required_rules']:
                assert judgment['lemmas'][0] in derived
                assert judgment['morphemes'][1] == '되다' and judgment['morpheme_kinds'][1] == 'suffix'
    assert len(source['words']) == len(set(source['words'])) == 953
    assert source['input'] == ' '.join(source['words'])
    assert set(source['before']) == set(MODES)
    for mode, run in source['before'].items():
        assert run['exit_code'] == 0 and hashlib.sha256(run['jsonl'].encode()).hexdigest() == run['sha256']
        records, words = word_records(run['jsonl'])
        assert ''.join(r['surface'] for r in records) == source['input']
        assert set(words) == set(source['words'])
        assert all(RULE not in a['rules'] for r in words.values() for a in r['analysis']['analyses'])
        if mode == 'raw':
            assert fixture['before_analyses'] == {w: r['analysis'] for w, r in before_words(source, 'raw').items()}
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
    assert len(rows) == 185
    assert any('화+하' in r['original_lemma'] for r in rows)
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
    raw_before = before_words(source, 'raw')
    for mode, runs in report['runs'].items():
        assert set(runs) == {'NFC-cached', 'NFC-uncached', 'NFD-cached', 'NFD-uncached'}
        before = before_words(source, mode)
        parity = None
        for encoding_cache, run in runs.items():
            assert run['exit_code'] == 0
            assert hashlib.sha256(run['jsonl'].encode()).hexdigest() == run['sha256']
            records, after = word_records(run['jsonl'])
            assert set(after) == set(before)
            assert ''.join(r['surface'] for r in records) == unicodedata.normalize(encoding_cache.split('-')[0], source_input(source))
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
                assert a['morphemes'][0] == {'form': '화', 'kind': 'suffix'}
                base = a['lemmas'][0]['text']
                assert base in ['가속', '가시', '개념', '개방', '개별', '객관', '격식', '내면', '내실', '노령', '민영', '민주', '보편', '상품', '생활', '온난', '이론', '이상', '일반', '일상', '제도', '조직', '최소', '토착', '특수', '표준', '합리', '황폐']
                nested = len(a['morphemes']) > 1 and a['morphemes'][1] == {'form': '되다', 'kind': 'suffix'}
                if nested:
                    assert base in ['가속', '가시', '개방', '객관', '내면', '민영', '민주', '보편', '상품', '생활', '이론', '이상', '일반', '일상', '제도', '조직', '토착', '특수', '표준', '합리', '황폐']
                    assert 'suffix.verb.doeda' in a['rules']
                parents = []
                for count, kind, head in [(1, 'nominal', base + '화'),
                                          (2, 'predicate', base + '화되다')]:
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
                    assert not nested and a['morphemes'] == [{'form':'화','kind':'suffix'}]
                    assert a['lemmas'] == [{'text':base,'kind':'nominal'}]
                    assert word == base + '화' and a['rules'] == [RULE]
                else:
                    allowed = {r for p in parents for r in p['rules']} | {RULE}
                    if nested:
                        allowed.add('suffix.verb.doeda')
                    assert set(a['rules']) <= allowed
                family = next(f for f in source['families'] if f['base'] == base)
                whole_ids = family['whole_passive_ids'] if nested else family['whole_nominal_ids']
                suffix = '化되다' if nested else '化'
                for entry in reading['lemmas'][0]['entries']:
                    identity = entry.get('derivational_identity')
                    actual = native[entry['id']]
                    if not whole_ids or actual['pos'] != '명사':
                        assert identity is None
                        continue
                    assert identity is not None
                    assert identity['morpheme_index'] == (1 if nested else 0)
                    assert identity['whole_entries'] == whole_ids
                    assert all(native[i]['headword'] == base + ('화되다' if nested else '화') for i in whole_ids)
                    expected = sorted({o.removesuffix(suffix) for i in whole_ids for o in native[i]['origins']})
                    assert identity['expected_origins'] == expected
                    assert identity['whole_origins_complete'] == all(native[i]['origins'] for i in whole_ids)
                    matched = any(o in expected for o in actual['origins'])
                    # The sole slash-form here is an explicitly recorded nominal variant.
                    if not nested and whole_ids == ['krdict:68615'] and actual['origins'] == ['溫暖/溫煖']:
                        matched = True
                    relation = 'recorded_match' if matched else 'recorded_difference' if actual['origins'] else 'unknown'
                    assert identity['relation'] == relation
                changes.append({'id':'nominal-hwa-change-'+digest([mode,word,a]),'mode':mode,
                                'surface':word,'analysis':a,'reading':reading,
                                'contextual_verdict':'unjudged','independent_review':'pending'})
    assert report['changes'] == changes
    return len(changes)


def capture(cli, output):
    import gzip
    assert not output.exists()
    source = read(SOURCE)
    inspect_source(source)
    report = {'schema_version':1,'checklist':'COV-022p','source_sha256':sha(SOURCE),
              'fixture_sha256':sha(FIXTURE),'before_cli_sha256':source['before_cli_sha256'],
              'cli_sha256':sha(cli),'dictionary_sha256':sha(ROOT/'data/dictionaries/krdict/krdict.db'),
              'runs':{},'changes':[]}
    for mode, flags in MODES.items():
        report['runs'][mode] = {}
        for encoding in ['NFC','NFD']:
            for cache, budget in [('cached','8388608'),('uncached','0')]:
                command = [str(cli),'text','-','--dictionary',str(ROOT/'data/dictionaries/krdict/krdict.db'),*flags,'--cache-bytes',budget]
                result = subprocess.run(command,input=unicodedata.normalize(encoding,source_input(source)),text=True,capture_output=True,check=True)
                report['runs'][mode][encoding+'-'+cache] = {'command':command,'exit_code':result.returncode,
                    'jsonl':result.stdout,'sha256':hashlib.sha256(result.stdout.encode()).hexdigest()}
        _, words = word_records(report['runs'][mode]['NFC-cached']['jsonl'])
        for word, record in words.items():
            for i,a in enumerate(record['analysis']['analyses']):
                if RULE in a['rules']:
                    report['changes'].append({'id':'nominal-hwa-change-'+digest([mode,word,a]),'mode':mode,
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
