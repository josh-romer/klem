"""Verify complete past-prefinal sources, exact judgments and source aliases offline."""
import gzip
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from native_lmf import entry, verify_native_lmf

ROOT = Path(__file__).resolve().parents[1]

PRIMARY = {'krdict:66954', 'krdict:68719', 'krdict:68723'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    data = (ROOT / name).read_bytes()
    return json.loads(gzip.decompress(data) if name.endswith('.gz') else data)


def producer(report):
    assert sha(report['producer']['text'].encode()) == report['producer']['sha256']


def identity(o):
    return o['source'], o['sense'], o['index'], o['text_index'], tuple(o['character_span'])


def verify_sources(capture, primary, owners):
    for report in (capture, primary, owners):
        producer(report)
        assert report['preparation_only'] is True
        assert report['contextual_verdict'] == 'unjudged'
        assert report['independent_review'] == 'pending'
    native = owners['complete_native_entries']
    assert len(native) == 99 and set(owners['primary_entry_ids']) == PRIMARY
    assert {key: entry(raw) for key, raw in owners['original_lmf'].items()} == native
    verify_native_lmf(owners['english_projection'], native)
    assert primary['complete_native_entries'] == capture['sqlite_entries'] == {key: native[key] for key in PRIMARY}
    assert primary['original_lmf'] == {key: owners['original_lmf'][key] for key in PRIMARY}
    verify_native_lmf(primary['english_projection'], primary['complete_native_entries'])
    assert primary['source_hashes'] == owners['source_hashes']
    manifest = json.loads(capture['dictionary_metadata']['manifest'])
    assert {Path(key).name: value for key, value in owners['source_hashes'].items()} == {f['name']: f['sha256'] for f in manifest['files']}
    assert len(manifest['files']) == 11
    assert manifest['license'] == 'CC-BY-SA-2.0-KR'
    groups = [{'source': key, 'sense': sense['id'], 'index': i, 'original': group}
              for key in sorted(PRIMARY) for sense in native[key]['senses']
              for i, group in enumerate(sense['examples'])]
    assert len(groups) == 38 and groups == capture['all_original_groups']
    assert all([s['id'] for s in native[key]['senses']] == ['1', '2', '3'] for key in PRIMARY)
    assert capture['input'] == '\n'.join(text for group in groups for text in group['original'])+'\n'
    assert native['krdict:66954']['notes'] == ['끝음절의 모음이 ‘ㅏ, ㅗ’인 동사와 형용사 뒤에, 다른 어미 앞에 붙여 쓴다.']
    eo = native['krdict:68719']
    assert eo['notes'] == []
    assert eo['senses'][0]['notes'] == ['‘이다’, 끝음절의 모음이 ‘ㅏ, ㅗ’가 아닌 동사와 형용사 뒤에, 다른 어미 앞에 붙여 쓴다.']
    assert all(s['notes'] == ['끝음절의 모음이 ‘ㅏ, ㅗ’가 아닌 동사와 형용사 뒤에, 다른 어미 앞에 붙여 쓴다.'] for s in eo['senses'][1:])
    assert native['krdict:68723']['notes'] == ['‘하다’나 ‘하다’가 붙는 동사와 형용사 뒤에, 다른 어미 앞에 붙여 쓴다.']
    assert any(f['kind'] == '활용' and f['written'] == '하여' for f in native['krdict:73277']['forms'])


def verify_targets(capture, draft, inventory, suite):
    producer(draft)
    producer(inventory)
    assert draft['preparation_only'] and inventory['preparation_only']
    positive = [case for case in draft['cases'] if 'source_occurrence' in case]
    assert len(positive) == 44
    keys = {identity(case['source_occurrence']) for case in positive}
    assert len(keys) == 44
    observed = []
    for group in capture['all_original_groups']:
        for ti, text in enumerate(group['original']):
            for match in re.finditer(r'[가-힣]+', text):
                if any((ord(ch)-0xAC00) % 28 == 20 for ch in match[0]):
                    observed.append(({**group, 'text_index': ti, 'character_span': [match.start(),match.end()]}, match[0]))
    assert len(observed) == len(inventory['literal_observations']) == 56
    target_ids = {identity(case['source_occurrence']): case['id'] for case in positive}
    incidental = []
    for (occurrence, surface), row in zip(observed, inventory['literal_observations'], strict=True):
        assert row['source_occurrence'] == occurrence and row['surface'] == surface
        assert row['contextual_verdict'] == 'unjudged' and row['independent_review'] == 'pending'
        key = identity(occurrence)
        if key in keys:
            assert row['role'] == 'primary_structural_proposal' and row['case'] == target_ids[key]
        else:
            assert row['role'] == 'incidental_not_primary_target' and row['reason']
            incidental.append(surface)
    assert incidental == ['재미있었어','있어','확인했어','했어','있던','했어','말았다','앓았던','힘들었는데','났으니','일어났으니','봤자']
    assert {(c['source_occurrence']['source'], c['source_occurrence']['sense']) for c in positive} == {(key,sense) for key in PRIMARY for sense in ['1','2','3']}
    assert len({(c['source_occurrence']['source'],c['source_occurrence']['sense'],c['source_occurrence']['index']) for c in positive}) == 38
    for case in positive:
        occurrence = case['source_occurrence']
        group = {key: occurrence[key] for key in ('source','sense','index','original')}
        assert group in capture['all_original_groups']
        start,end = occurrence['character_span']
        assert occurrence['original'][occurrence['text_index']][start:end] == case['surface']
        for judgment in case['judgments']:
            assert judgment['verdict'] == 'required'
            assert draft['sources'][judgment['source']].endswith('ParaWordNo='+occurrence['source'].split(':')[1])
            assert judgment['required_rules'] == ['prefinal.past']
    assert suite['cases'] == [{key:case[key] for key in ('id','surface','judgments')} for case in draft['cases']]
    assert suite['sources'] == draft['sources']
    judgments = [j for case in suite['cases'] for j in case['judgments']]
    assert sum(j['verdict']=='required' for j in judgments) == 45
    assert sum(j['verdict']=='forbidden' for j in judgments) == 5
    negatives = [case for case in suite['cases'] if case['judgments'][0]['verdict']=='forbidden']
    assert [(c['surface'],c['judgments'][0]['lemmas'][0],c['judgments'][0]['source']) for c in negatives] == [
        ('가었다','가다','past-prefinal-68719'),('먹았다','먹다','past-prefinal-66954'),
        ('하았다','하다','past-prefinal-68723'),('하었다','하다','past-prefinal-68723'),('좋었다','좋다','past-prefinal-68719')]
    assert all(c['judgments'][0]['morphemes']==['었','다'] and c['judgments'][0]['morpheme_kinds']==['prefinal','ending'] for c in negatives)
    # A broad attachment note cannot erase its own eu-deletion example.
    assert any(c['surface']=='잠갔니' and c['judgments'][0]['lemmas']==['잠그다'] for c in positive)
    polite = next(c for c in positive if c['surface']=='보셨어요')
    assert [j['morphemes'] for j in polite['judgments']] == [['시','었','어','요'],['시','었','어요']]


def verify_streams(capture, boundary):
    assert capture['inputs_unchanged'] is True and boundary['inputs_unchanged'] is True
    producer(boundary)
    assert {(r['encoding'],r['mode']) for r in capture['runs']} == {(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']}
    assert len(capture['runs']) == 6
    for run in capture['runs']:
        data = unicodedata.normalize(run['encoding'],capture['input']).encode()
        assert sha(data) == run['input_sha256']
        assert run['exit_code']==0 and sha(run['jsonl'].encode()) == run['sha256']
        assert run['command'][0] in capture['frozen_inputs']
        assert run['command'][1:4] == ['text','-','--dictionary']
        assert run['command'][4] in capture['frozen_inputs']
        assert run['command'][5:] == {'raw':[],'headword':['--dict-only'],'compatible':['--dict-compatible']}[run['mode']]
        frames = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(frames)==run['records']==638
        cursor = 0
        for frame in frames:
            assert frame['span']['start']==cursor
            cursor = frame['span']['end']
            assert data[frame['span']['start']:cursor] == frame['surface'].encode()
        assert cursor == len(data)
    assert boundary['frozen_inputs'] == capture['frozen_inputs']
    assert len(boundary['runs']) == 40
    triples = {(r['surface'],r['encoding'],r['mode']) for r in boundary['runs']}
    words = {'가었다','먹았다','하았다','하었다','좋었다','먹었다','갔다','했다','잠갔니','예뻤다'}
    assert triples == {(w,e,m) for w in words for e in ['NFC','NFD'] for m in ['raw','compatible']}
    for run in boundary['runs']:
        assert sha(run['json'].encode())==run['sha256'] and run['exit_code']==0
        response = json.loads(run['json'])
        assert response['normalized']==run['surface']
        assert run['command'][1]=='word' and run['command'][2]==unicodedata.normalize(run['encoding'],run['surface'])
        assert run['command'][0] in boundary['frozen_inputs'] and run['command'][3]=='--dictionary' and run['command'][4] in boundary['frozen_inputs']
        assert run['command'][5:]==([] if run['mode']=='raw' else ['--dict-compatible'])
        matched = [a for a in response['analyses'] if [l['text'] for l in a['lemmas']]==[run['queried_lemma']] and any(m['form']=='었' and m['kind']=='prefinal' for m in a['morphemes'])]
        assert bool(matched) == (run['surface'] not in {'가었다','먹았다','하았다','하었다','좋었다'})


def verify():
    capture_path = 'docs/past-prefinal-source-discovery.json.gz'
    draft_path = 'docs/past-prefinal-judgments.json'
    owners_path = 'docs/past-prefinal-owner-preparation.json.gz'
    boundary_path = 'docs/past-prefinal-boundary-capture.json.gz'
    capture, draft, owners, boundary = map(read, [capture_path,draft_path,owners_path,boundary_path])
    primary = read('docs/past-prefinal-native-preparation.json.gz')
    inventory = read('docs/past-prefinal-literal-inventory.json')
    assert sha((ROOT / capture_path).read_bytes()) == draft['source_capture_sha256'] == owners['source_capture_sha256'] == primary['source_capture_sha256'] == inventory['source_capture_sha256']
    assert sha((ROOT / draft_path).read_bytes()) == inventory['effective_draft_sha256'] == owners['target_proposals_sha256']
    assert sha(gzip.decompress((ROOT / boundary_path).read_bytes())) == draft['boundary_capture_sha256']
    verify_sources(capture,primary,owners)
    suite = read('tests/fixtures/past-prefinal-validity.json')
    verify_targets(capture,draft,inventory,suite)
    verify_streams(capture,boundary)
    native = read('tests/fixtures/past-prefinal-native.json')
    english = read('tests/fixtures/krdict-past-prefinal-english.json')
    assert native == owners['complete_native_entries'] and english == owners['english_projection']
    history = read('docs/past-prefinal-preparation-history.json.gz')
    for archived in history.values():
        data = bytes.fromhex(archived['content']) if archived['encoding']=='hex' else archived['content'].encode()
        assert sha(data)==archived['sha256']
    receipt = json.loads(history['klem-past-prefinal-review-v2-rust.json']['content'])
    assert receipt['state']=='passed' and receipt['exit_code']==0 and receipt['tests_passed']==3
    assert sha((ROOT / draft_path).read_bytes())==receipt['source_draft_sha256']
    assert sha((ROOT / owners_path).read_bytes())==receipt['owner_preparation_sha256']
    assert sha(gzip.decompress((ROOT / boundary_path).read_bytes()))==receipt['boundary_capture_sha256']
    assert history['klem-past-prefinal-review-v2-rust.log']['sha256']==receipt['log_sha256']
    assert all(history['v2/'+p]['sha256']==h for p,h in receipt['wrapper_files'].items())
    verify_main_and_before_api(capture,owners,suite)
    verify_browser(read('docs/past-prefinal-main-browser.json.gz'), owners, suite)
    return {'state':'bounded-source-audit-passed','primary_entries':3,'senses':9,'original_groups':38,'literal_ss_words':56,'primary_occurrences':44,'incidental_dispositions':12,'required':45,'forbidden':5,'complete_named_owners':99,'streams':6,'frames_per_stream':638,'boundary_calls':40,'contextual_verdict':'unjudged','independent_review':'pending'}


def verify_browser(browser, owners, suite):
    """Replay the archived API and candidate comparisons without a browser/runtime."""
    before = read('docs/past-prefinal-before-api.json.gz')
    assert browser['errors'] == []
    assert browser['producer_sha256'] == sha((ROOT/'web/tests/past-prefinal.mjs').read_bytes())
    assert browser['suite_sha256'] == sha((ROOT/'tests/fixtures/past-prefinal-validity.json').read_bytes())
    assert len(browser['responses']) == 2
    assert {r['encoding'] for r in browser['responses']} == {'NFC','NFD'}
    for run in browser['responses']:
        original = next(r for r in before['runs'] if r['encoding'] == run['encoding'])
        assert run['request'] == original['request']
        response = run['response']
        for key in ['records','rules','breakdowns','glosses']:
            assert response[key] == original['response'][key]
        assert {k:v for k,v in response['grammar'].items() if k!='-었-'} == {k:v for k,v in original['response']['grammar'].items() if k!='-었-'}
        assert response['grammar']['-었-'][0] == original['response']['grammar']['-었-'][0]
        assert response['grammar']['-었-'] == [
            {key:owners['complete_native_entries'][eid][key] for key in ['headword','homonym','id','pos']}
            for eid in ['krdict:68719','krdict:66954','krdict:68723']]
    assert len(browser['native']) == 99
    assert {r['id']:r['response']['entry'] for r in browser['native']} == owners['complete_native_entries']
    assert browser['opened'] == [{'id':eid,'head':owners['complete_native_entries'][eid]['headword']}
                                for eid in ['krdict:66954','krdict:68719','krdict:68723']]
    expected = {(case['id'],j['id'],encoding): (case,j)
                for case in suite['cases'] for j in case['judgments'] if j['verdict']=='required'
                for encoding in ['NFC','NFD']}
    assert len(browser['diagrams']) == len(expected) == 90
    assert {(r['case_id'],r['judgment_id'],r['encoding']) for r in browser['diagrams']} == set(expected)
    for row in browser['diagrams']:
        case,j = expected[row['case_id'],row['judgment_id'],row['encoding']]
        assert row['surface'] == case['surface']
        a = row['analysis']
        assert [l['text'] for l in a['lemmas']] == j['lemmas']
        assert [l['kind'] for l in a['lemmas']] == j['lemma_kinds']
        assert [m['form'] for m in a['morphemes']] == j['morphemes']
        assert [m['kind'] for m in a['morphemes']] == j['morpheme_kinds']
        assert set(j.get('required_rules',[])) <= set(a['rules'])
        assert all(str(eid) in row['title'] for eid in [68719,66954,68723])
    assert len(browser['exports']) == 6
    assert {(r['encoding'],r['mode']) for r in browser['exports']} == {(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']}


def verify_main_and_before_api(capture,owners,suite):
    import copy
    ledger=read('tests/fixtures/validity.json')
    indexed={case['id']:case for case in ledger['cases']}
    assert all(indexed[case['id']]==case for case in suite['cases'])
    assert all(ledger['sources'][key]==value for key,value in suite['sources'].items())
    before=read('docs/past-prefinal-before-api.json.gz')
    producer(before)
    assert before['state']=='before-api-captured' and before['inputs_unchanged'] is True
    assert len(before['runs'])==2
    assert {run['encoding'] for run in before['runs']}=={'NFC','NFD'}
    assert len(before['complete_primary_native_endpoints'])==3
    for run in before['runs']:
        assert sha(run['json'].encode())==run['sha256'] and run['status']==200
        assert json.loads(run['json'])==run['response']
        assert run['request']=={'text':unicodedata.normalize(run['encoding'],capture['input'])}
        original=next(r for r in capture['runs'] if r['encoding']==run['encoding'] and r['mode']=='raw')
        assert run['response']['records']==[json.loads(line) for line in original['jsonl'].splitlines()]
        assert [e['id'] for e in run['response']['grammar']['-었-']]==['krdict:68719']
    assert {r['request']['id'] for r in before['complete_primary_native_endpoints']}==PRIMARY
    for result in before['complete_primary_native_endpoints']:
        assert result['status']==200 and sha(result['json'].encode())==result['sha256']
        assert json.loads(result['json'])==result['response']
        assert result['response']['entry']==owners['complete_native_entries'][result['request']['id']]
    catalog=read('web/src/grammar-labels.json')
    assert catalog['-었-']['kind']=='prefinal'
    assert catalog['-었-']['sources']==[
        {'id':68719,'headword':'-었-','pos':'어미'},
        {'id':66954,'headword':'-았-','pos':'어미'},
        {'id':68723,'headword':'-였-','pos':'어미'}]
    captured_before=read('docs/past-prefinal-catalog-before.json')
    captured_after=read('docs/past-prefinal-catalog-after.json')
    assert sha((ROOT/'docs/past-prefinal-catalog-before.json').read_bytes())==before['frozen_inputs']['/home/josh/projects/klem/web/src/grammar-labels.json']
    previous=copy.deepcopy(captured_after)
    previous['-었-']['sources']=previous['-었-']['sources'][:1]
    assert previous==captured_before
    assert captured_after['-었-']==catalog['-었-']
    label_native={key:owners['complete_native_entries'][key] for key in ['krdict:66954','krdict:68723']}
    verify_native_lmf(read('tests/fixtures/krdict-past-prefinal-labels.json'),label_native)


if __name__=='__main__':
    print(json.dumps(verify(),ensure_ascii=False))
