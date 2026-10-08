"""Independently derive the next source cohort and every preserved/new observation."""
import gzip
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from native_lmf import entry, verify_native_lmf

sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda p: json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())

def matches(path, expected):
    return ([l['text'] for l in path['lemmas']] == expected['lemmas']
            and [l['kind'] for l in path['lemmas']] == expected['lemma_kinds']
            and [m['form'] for m in path['morphemes']] == expected['morphemes']
            and [m['kind'] for m in path['morphemes']] == expected['morpheme_kinds']
            and set(expected['required_rules']) <= set(path['rules']))

def inspect(source, prepared, replay):
    for capture in [source, prepared, replay]:
        assert sha(capture['producer']['text'].encode()) == capture['producer']['sha256']
    assert source['state'] == replay['state'] == 'passed'
    assert source['exit_code'] == replay['exit_code'] == 0
    assert source['inputs_unchanged'] is replay['inputs_unchanged'] is True
    assert prepared['preparation_only'] is True
    assert source['baseline_package_sha256'] == sha((ROOT/'docs/literary-question-go-package-nix.json').read_bytes())
    package_cli = read(ROOT/'docs/literary-question-go-packaged-cli-replay.json')
    assert source['frozen_inputs'][package_cli['cli']] == package_cli['cli_sha256']
    assert source['primary_ids'] == prepared['primary_entry_ids'] == ['krdict:81026','krdict:81032']
    native = prepared['complete_native_entries']
    assert len(native) == len(prepared['original_lmf']) == 72
    for ident, raw in prepared['original_lmf'].items(): assert entry(raw) == native[ident]
    verify_native_lmf(prepared['english_projection'], native)
    assert all(native[ident] == value for ident, value in source['sqlite_entries'].items())
    groups, lines, targets, cursor = [], [], [], 0
    for ident, value in source['sqlite_entries'].items():
        for sense in value['senses']:
            for index, original in enumerate(sense['examples']):
                groups.append({'source':ident,'sense':sense['id'],'index':index,'original':original})
                for line_index, text in enumerate(original):
                    lines.append(text)
                    for found in re.finditer(r'[가-힣]+꼬(?=$|[\s.,!?])', text):
                        assert (ord(found.group()[-2])-0xAC00)%28 == 8
                        targets.append({'source':ident,'sense':sense['id'],'group_index':index,
                                        'line_index':line_index,'surface':found.group(),
                                        'char_span':{'start':cursor+found.start(),'end':cursor+found.end()}})
                    cursor += len(text)+1
    assert groups == source['all_original_groups'] and len(groups) == 19
    assert '\n'.join(lines)+'\n' == source['input']
    assert targets == source['targets'] and len(targets) == 19
    conflict = source['source_note_conflicts']
    assert len(conflict) == 1 and conflict[0]['source'] == 'krdict:81026' and conflict[0]['sense'] == '2'
    assert conflict[0]['note'] == native['krdict:81026']['senses'][1]['notes']
    cases = prepared['original_cases']; assert len(cases) == 19
    parents = prepared['parent_capture']; assert parents['exit_code'] == 0
    assert sha(parents['input'].encode()) == parents['input_sha256']
    assert sha(parents['jsonl'].encode()) == parents['sha256']
    parent_rows = {r['surface']:r for r in map(json.loads,parents['jsonl'].splitlines()) if r.get('analysis')}
    assert len(parent_rows) == 18
    ids = set()
    for case, target in zip(cases, targets, strict=True):
        assert case['source_occurrence'] == target and case['surface'] == target['surface']
        expected_id = f"literary-future-kko-original-{target['source'].split(':')[1]}-{target['sense']}-{target['group_index']}"
        assert case['id'] == expected_id and expected_id not in ids; ids.add(expected_id)
        assert case['structural_verdict'] == 'proposed-required'
        assert case['contextual_verdict'] == 'unjudged' and case['independent_review'] == 'pending'
        parent = case['earlier_parent']; assert parent['surface'] == target['surface'][:-1]+'까'
        row = parent_rows[parent['surface']]; index = row['analysis']['analyses'].index(parent['analysis'])
        assert row['dictionary']['readings'][index] == parent['assessment']
        expected = case['expected']; old = dict(expected,morphemes=expected['morphemes'][:-1]+['을까'],required_rules=[])
        assert expected['required_rules'] == ['ending.literary_future_question_kko']
        assert expected['morphemes'][-1] == '을꼬' and matches(parent['analysis'], old)
    keys = [(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']]
    assert [(r['encoding'],r['mode']) for r in source['runs']] == keys
    assert [(r['encoding'],r['mode']) for r in replay['runs']] == keys
    observations, before_observations, additions, owners = [], [], [], set()
    for before, after in zip(source['runs'],replay['runs'],strict=True):
        encoding, mode = before['encoding'], before['mode']
        text = unicodedata.normalize(encoding,source['input']); encoded = text.encode()
        assert sha(encoded) == before['input_sha256'] == after['input_sha256']
        assert sha(before['jsonl'].encode()) == before['sha256'] == after['before_sha256']
        assert sha(after['jsonl'].encode()) == after['after_sha256'] and after['exit_code'] == 0
        old, now = list(map(json.loads,before['jsonl'].splitlines())), list(map(json.loads,after['jsonl'].splitlines()))
        assert len(old) == len(now) == after['records'] == before['records'] == 253
        cursor = 0
        for index,(previous,current) in enumerate(zip(old,now,strict=True)):
            assert current['span']['start'] == cursor
            assert current['surface'] == encoded[cursor:current['span']['end']].decode()
            cursor = current['span']['end']
            assert {k:v for k,v in previous.items() if k not in ['analysis','dictionary']} == {k:v for k,v in current.items() if k not in ['analysis','dictionary']}
            if previous.get('analysis') is None: assert previous == current; continue
            oa, na = previous['analysis']['analyses'], current['analysis']['analyses']
            assert [p for p in na if p in oa] == oa
            od, nd = previous['dictionary'], current['dictionary']
            assert od['source'] == nd['source'] and od['fingerprint'] == nd['fingerprint']
            for path, assessment in zip(oa,od['readings'],strict=True): assert nd['readings'][na.index(path)] == assessment
            assert all(match in nd['lemmas'] for match in od['lemmas'])
            for n,path in enumerate(na):
                if path in oa: continue
                assert 'ending.literary_future_question_kko' in path['rules']
                assessment = nd['readings'][n]
                owners.update(e['id'] for slot in assessment['lemmas'] for e in slot['entries'])
                ident = 'literary-future-kko-source-addition-'+sha(json.dumps([encoding,mode,index,path],ensure_ascii=False,sort_keys=True).encode())[:24]
                additions.append({'encoding':encoding,'mode':mode,'frame_index':index,'surface':current['surface'],
                                  'span':current['span'],'analysis':path,'assessment':assessment,'id':ident,
                                  'structural_verdict':'unjudged','contextual_verdict':'unjudged','independent_review':'pending'})
        assert cursor == len(encoded)
        for case in cases:
            target = case['source_occurrence']; start,end = target['char_span']['start'],target['char_span']['end']
            span = {'start':len(unicodedata.normalize(encoding,source['input'][:start]).encode()),
                    'end':len(unicodedata.normalize(encoding,source['input'][:end]).encode())}
            row = next(r for r in now if r['span'] == span)
            baseline = next(r for r in old if r['span'] == span)
            before_paths = baseline['analysis']['analyses'] if baseline.get('analysis') else []
            count = sum(any(m['kind'] == 'ending' and m['form'] in ['ㄹ꼬','을꼬']
                            for m in path['morphemes']) for path in before_paths)
            assert count == 0
            before_observations.append({'target':target,'encoding':encoding,'mode':mode,'span':span,
                                        'whole_literary_future_question_ending_paths':count,
                                        'analysis_count':len(before_paths),'record':baseline})
            if encoding == 'NFC' and mode == 'raw': assert case['before'] == baseline['analysis']
            hits = [n for n,path in enumerate(row['analysis']['analyses']) if matches(path,case['expected'])]
            assert len(hits) == 1
            n = hits[0]
            observations.append({'encoding':encoding,'mode':mode,'target':target,'span':span,
                                 'case_id':case['id'],'expected':case['expected'],
                                 'analysis':row['analysis']['analyses'][n],'assessment':row['dictionary']['readings'][n],
                                 'structural_verdict':'proposed-required','contextual_verdict':'unjudged','independent_review':'pending'})
    assert observations == replay['original_targets'] and len(observations) == 114
    assert before_observations == source['target_observations']
    assert additions == replay['individual_additions'] and len(additions) == 328
    assert len({a['id'] for a in additions}) == 328
    assert sorted(owners) == replay['matched_native_owner_ids'] == prepared['matched_native_owner_ids']
    assert len(owners) == 65 and owners <= native.keys()
    return {'source_frames':1518,'original_proposed_structures':19,'original_observations':114,
            'all_individual_additions_retained':328,'matched_native_owners':65,'complete_native_entries':72,
            'contextual_verdict':'unjudged','independent_review':'pending','production_integration':'pending'}

def inputs():
    return [read(ROOT/'docs'/name) for name in ['literary-future-kko-source-discovery.json.gz',
            'literary-future-kko-source-owner-preparation.json.gz',
            'literary-future-kko-prototype-source-replay.json.gz']]

if __name__ == '__main__': print(inspect(*inputs()))
