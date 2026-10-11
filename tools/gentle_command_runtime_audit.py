"""Audit complete runtime captures without changing original judgments or gold."""
import gzip
import hashlib
import json
import unicodedata
from pathlib import Path

import gentle_command_source_audit as source_audit

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
MANIFEST_SHA256 = '5500e8b18cc6a6051d5792c2397c2f429684a24d8f8f1d73cd21e11dfeeaad69'
PARENTS = {
    'gold': ('willingness-question-distribution-proof-willingness-corpora.json.gz', 'a436df9184a7db2d440a88afcbe118c5b5ccc6596b8311458e0a155e135b5b6d'),
    'broad': ('willingness-question-distribution-proof-willingness-broad.json.gz', 'b361afea8a34f690fa4df13e31d9949775ae4f1461ee286f88e1a5f53831ae56'),
    'broad_inputs': ('reported-deoni-broad-inputs.json.gz', '7d43206bb6add22e79cb27173ff049cf501e9dcdabe307c9d5a4cacc2ab26902'),
    'annotations': ('literary-question-geona-prototype-corpora.json.gz', '12b9e453369bd11bd4c963bda66eaa69e438aff5c9d47999151445d4a2d220a3'),
}


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def inputs():
    docs = ROOT / 'docs'
    manifest_raw = (docs / 'gentle-command-runtime-proof-archive.json').read_bytes()
    assert sha(manifest_raw) == MANIFEST_SHA256, 'original runtime manifest cannot be refreshed'
    manifest = json.loads(manifest_raw)
    proof = {}
    for name, item in manifest['files'].items():
        raw = (docs / item['path']).read_bytes()
        assert sha(raw) == item['archive_sha256'], 'unchanged runtime archive'
        original = raw if name.endswith('.gz') else gzip.decompress(raw)
        assert sha(original) == item['source_sha256'], 'unchanged original runtime bytes'
        if name.endswith(('.json', '.json.gz')):
            proof[name] = json.loads(gzip.decompress(raw))
    parents = {}
    for name, (file, digest) in PARENTS.items():
        raw = (docs / file).read_bytes()
        assert sha(raw) == digest, 'unchanged prior distribution archive'
        parents[name] = json.loads(gzip.decompress(raw))
    closure = proof['gentle-command-current-production-closure.json']
    current_production = {p: sha((ROOT / Path(p).relative_to('/tmp/klem-gentle-command')).read_bytes())
                          for p in closure['production_inputs']}
    return dict(source_evidence=source_audit.inputs(), parents=parents,
                original_sha256={name: item['source_sha256'] for name, item in manifest['files'].items()},
                current_production=current_production,
                streams=proof['gentle-command-source-runtime.json.gz'],
                native=proof['gentle-command-native-cli.json'],
                gold=proof['gentle-command-corpora.json.gz'], broad=proof['gentle-command-broad.json.gz'],
                context=proof['gentle-command-novel-context-review.json'],
                binding=proof['gentle-command-current-production-binding.json'],
                closure=closure,
                adapter=proof['gentle-command-adapter-binding.json'],
                full=proof['gentle-command-merged-full-rust-retry2.json'])


def terminal(report, state):
    assert report['state'] == state and report['inputs_unchanged'], 'terminal unchanged runtime capture'
    assert sha(report['producer']['text'].encode()) == report['producer']['sha256'], 'actual runtime producer'


def matches(path, target):
    return all([part[key] for part in path[field]] == target[name]
               for field, key, name in [('lemmas', 'text', 'lemmas'), ('lemmas', 'kind', 'lemma_kinds'),
                                       ('morphemes', 'form', 'morphemes'), ('morphemes', 'kind', 'morpheme_kinds')]) and set(target.get('required_rules', [])) <= set(path['rules'])


def additions(old, new):
    assert {k: old[k] for k in ['surface', 'span', 'kind']} == {k: new[k] for k in ['surface', 'span', 'kind']}, 'original token ownership'
    before, after = old.get('analysis') or {}, new.get('analysis') or {}
    old_paths, new_paths = before.get('analyses', []), after.get('analyses', [])
    assert [p for p in new_paths if p in old_paths] == old_paths, 'every original candidate and order'
    added = [p for p in new_paths if p not in old_paths]
    assert all('ending.gentle_command' in p['rules'] and any(m == {'form': '으렴', 'kind': 'ending'} for m in p['morphemes']) for p in added), 'only canonical gentle-command additions'
    for index, path in enumerate(old_paths):
        assert old['dictionary']['readings'][index] == new['dictionary']['readings'][new_paths.index(path)], 'every original Native assessment'
    if old['kind'] == 'word':
        assert all(owner in new['dictionary']['lemmas'] for owner in old['dictionary']['lemmas']), 'every original Native owner'
        assert {k: v for k, v in before.items() if k != 'analyses'} == {k: v for k, v in after.items() if k != 'analyses'}, 'original analysis fields'
    return added


def inspect_bindings(v):
    full, binding, closure = v['full'], v['binding'], v['closure']
    terminal(full, 'passed')
    assert full['totals'] == {'passed': 1182, 'failed': 0, 'ignored': 1} and full['batches'] == 253, 'complete actual Rust suite'
    assert full['head_unchanged'] and full['index_unchanged'] and len(full['frozen_inputs']) == 6474, 'complete frozen source/head/index'
    assert binding['state'] == closure['state'] == 'passed' and binding['inputs_unchanged'] and closure['inputs_unchanged'], 'actual production bindings'
    assert binding['captured_head'] == closure['captured_head'] == full['head'], 'same captured production checkpoint'
    assert len(binding['production_inputs']) == 43 and len(closure['production_inputs']) == 44, 'complete production closure'
    assert all(closure['production_inputs'][p] == digest == full['frozen_inputs'][p] for p, digest in binding['production_inputs'].items()), 'every compiled production input'
    extras = set(closure['production_inputs']) - set(binding['production_inputs'])
    assert len(extras) == 1 and next(iter(extras)).endswith('/src/dictionary/proper_names.json'), 'compiled proper-name JSON retained'
    assert all(full['frozen_inputs'][p] == digest for p, digest in closure['production_inputs'].items()), 'complete compiled data/source bytes'
    assert binding['binaries'] == closure['binaries'], 'exact actual executable identity'
    current_matches = v['current_production'] == closure['production_inputs']
    if not current_matches:
        # Keep this entire historical capture unchanged. The separately audited
        # long-ending revision binds its own binaries, complete 44 inputs and
        # five declared changes; arbitrary later source edits remain rejected.
        import gentle_command_long_revision as revision
        current_matches = revision.accepts_production(v['current_production'])
    assert current_matches, 'current complete production closure matches captures'
    # These production receipts were captured while the full suite was running.
    # Its later terminal receipt is checked separately above; do not rewrite the
    # earlier receipt hash or claim that it already attested a completed suite.
    assert closure['observed_full_rust_state'] == binding['observed_full_rust_state'] == 'running', 'original in-progress production binding retained'
    assert closure['production_binding_sha256'] == v['original_sha256']['gentle-command-current-production-binding.json'], 'actual production receipt binding'
    return binding['binaries']['klem']['path']


def inspect_streams(v):
    report = v['streams']; terminal(report, 'complete-gentle-command-source-runtime-passed')
    source, suite, baseline = (v['source_evidence'][k] for k in ['source', 'suite', 'baseline'])
    expected = [(family, encoding, mode, cache) for family in ['complete-source', 'individual-targets', 'individual-validity'] for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible'] for cache in [0, 4096]]
    assert [(r['family'], r['encoding'], r['mode'], r['cache_bytes']) for r in report['runs']] == expected, 'all36source policies'
    cli = v['binding']['binaries']['klem']['path']; cached = {}; observations = 0
    for run in report['runs']:
        family = run['family']
        text = '\n\n'.join('\n'.join(i['complete_original_group']) for i in source['items']) if family == 'complete-source' else ' '.join(i['surface'] for i in (suite['cases'] if family == 'individual-validity' else source['items']))
        raw = unicodedata.normalize(run['encoding'], text).encode()
        assert raw.decode() == run['input_text'] and sha(raw) == run['input_sha256'], 'complete original source bytes'
        flags = {'raw': [], 'headword': ['--dict-only'], 'compatible': ['--dict-compatible']}[run['mode']]
        assert run['command'][:4] == [cli, 'text', '-', '--dictionary'] and run['command'][4] in report['frozen_inputs'] and run['command'][5:] == flags+['--cache-bytes', str(run['cache_bytes'])], 'actual source filter/cache command'
        assert run['exit_code'] == 0 and sha(run['jsonl'].encode()) == run['jsonl_sha256'], 'complete actual source output'
        frames = [json.loads(line) for line in run['jsonl'].splitlines()]; cursor = 0
        for frame in frames:
            assert frame['span']['start'] == cursor and raw[cursor:frame['span']['end']].decode() == frame['surface'], 'contiguous original source spans'
            cursor = frame['span']['end']
        assert cursor == len(raw) and len(frames) == run['records'] and run['original_bytes_conserved'], 'all original source frames'
        derived = []
        if family != 'individual-validity':
            old = next(r for r in baseline['runs'] if all(r[k] == run[k] for k in ['family', 'encoding', 'mode', 'cache_bytes']))
            previous = [json.loads(line) for line in old['jsonl'].splitlines()]
            assert len(previous) == len(frames), 'all previous source frames'
            for before, after in zip(previous, frames, strict=True): additions(before, after)
            for item in source['items']:
                located = [(i, f) for i, f in enumerate(frames) if f['kind'] == 'word' and unicodedata.normalize('NFC', f['surface']) == item['surface']]
                assert len(located) == 1, 'every original source target'
                index, frame = located[0]; target = {**item['independent_typed_proposal'], 'required_rules': ['ending.gentle_command']}
                indices = [i for i, p in enumerate(frame['analysis']['analyses']) if matches(p, target)]
                assert indices, 'every independently authored source decomposition'
                derived.append(dict(case_id=item['id'], record_index=index, required_analysis_indices=indices))
        else:
            offset = 0
            for case in suite['cases']:
                token = unicodedata.normalize(run['encoding'], case['surface']).encode()
                located = [(i, f) for i, f in enumerate(frames) if f['span']['start'] == offset]
                assert len(located) == 1 and located[0][1]['surface'].encode() == token, 'individual judgment occurrence'
                index, frame = located[0]; offset += len(token)+1
                for j in case['judgments']:
                    indices = [i for i, p in enumerate(frame['analysis']['analyses']) if matches(p, j)]
                    assert bool(indices) == (j['verdict'] == 'required'), 'all private required/forbidden paths'
                    derived.append(dict(case_id=case['id'], judgment_id=j['id'], verdict=j['verdict'], record_index=index, analysis_indices=indices))
        assert run['observations'] == derived, 'all468individuallyrederivedobservations'
        observations += len(derived); key = (family, run['encoding'], run['mode'])
        assert key not in cached or cached[key] == run['jsonl'], 'exact cache output parity'
        cached[key] = run['jsonl']
    assert observations == 468 and report['streams'] == 36 and report['frames'] == sum(r['records'] for r in report['runs']) == 2160, 'complete finite runtime totals'
    assert report['linguistic_judgments_promoted'] is False, 'private judgments not silently promoted'


def inspect_native(v):
    report = v['native']; terminal(report, 'complete-gentle-command-native-cli-passed')
    expected = {key: entry for entries in v['source_evidence']['entries'] for key, entry in entries.items()}
    assert len(report['records']) == report['entries'] == len(expected) == 47, 'all47completeNativeowners'
    assert [r['id'] for r in report['records']] == list(expected), 'every Native owner/order'
    for row in report['records']:
        assert row['complete_original_entry'] == expected[row['id']], 'all original Native fields'
        assert len(row['captures']) == 2 and row['captures'][0]['json'] == row['captures'][1]['json'], 'both actual Native CLI versions'
        prior = v['source_evidence']['baseline']['runs'][0]['command'][0]
        for capture, cli in zip(row['captures'], [prior, v['binding']['binaries']['klem']['path']], strict=True):
            assert capture['command'][:3] == [cli, 'dict', 'entry'] and capture['command'][3] in report['frozen_inputs'] and capture['command'][4:] == [row['id']], 'actual bound Native CLI and owner'
            assert capture['exit_code'] == 0 and sha(capture['json'].encode()) == capture['stdout_sha256'], 'actual Native response bytes'
            assert json.loads(capture['json'])['entry'] == expected[row['id']], 'full original CLI entry fields'


def inspect_gold(v):
    report = v['gold']; terminal(report, 'complete-gentle-command-annotated-comparison-passed')
    adapter = v['adapter']; terminal(adapter, 'passed')
    assert [c['recovered_proposals'] for c in adapter['captures']] == [0, 8] and adapter['synthetic_probe_is_annotated_corpus'] is False, 'synthetic source probe kept separate'
    proposals = [dict(id=item['id'], surface=item['surface'], expected=item['independent_typed_proposal']['lemmas']) for item in v['source_evidence']['source']['items']]
    assert adapter['independently_authored_proposals'] == proposals and adapter['source_proposals_sha256'] == sha(v['source_evidence']['source_raw']), 'unchanged independently authored lexical proposals'
    for capture, version in zip(adapter['captures'], ['before', 'after'], strict=True):
        assert capture['command'] == [adapter['binaries'][version]['path'], 'kaist', adapter['synthetic_probe']], 'actual bound synthetic probe command'
        assert capture['exit_code'] == 0 and sha(capture['jsonl'].encode()) == capture['stdout_sha256'], 'complete synthetic probe output'
        rows = [json.loads(line) for line in capture['jsonl'].splitlines()]
        assert len(rows) == 9 and rows[0]['input_sha256'] == adapter['frozen_inputs'][adapter['synthetic_probe']], 'complete synthetic probe input binding'
        assert [dict(id=r['id'], surface=r['surface'], expected=r['expected']) for r in rows[1:]] == [dict(id='id:'+p['id']+'/1', surface=p['surface'], expected=p['expected']) for p in proposals], 'every independently authored probe row'
        assert all(r['matched'] == (version == 'after') and r['recovered'] == int(version == 'after') for r in rows[1:]), 'actual individual lexical probe recovery'
    assert len(report['runs']) == len(v['parents']['gold']['runs']) == 4, 'all four original partitions'
    for run, parent, annotation in zip(report['runs'], v['parents']['gold']['runs'], v['parents']['annotations']['corpora'], strict=True):
        assert (run['corpus'], run['partition'], run['source_sha256']) == (parent['corpus'], parent['partition'], parent['source_sha256']), 'original corpus identity'
        assert run['command'] == [adapter['binaries']['after']['path'], run['corpus'], run['source']] and run['before_command'] == [adapter['binaries']['before']['path'], run['corpus'], run['source']], 'actual bound adapters'
        assert run['exit_code'] == 0 and sha(run['jsonl'].encode()) == run['stdout_sha256'] == run['before_stdout_sha256'] == sha(parent['jsonl'].encode()), 'every original annotated output byte unchanged'
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(rows)-1 == run['rows'] and [{k: r[k] for k in ['id', 'surface', 'expected']} for r in rows[1:]] == [{k: r[k] for k in ['id', 'surface', 'expected']} for r in annotation['original_converted_rows']], 'every independent gold annotation'
        assert run['summary_changes'] == {}, 'unchanged original corpus summaries'
    assert sum(r['rows'] for r in report['runs']) == 66570 and report['individual_changed_rows'] == [], 'all66570originalrowsretained'


def inspect_broad(v):
    report = v['broad']; terminal(report, 'complete-gentle-command-broad-comparison-passed')
    modes = ['candidate-raw', 'candidate-headword', 'candidate-compatible', 'novel-raw', 'novel-headword', 'novel-compatible', 'novel-headword-spacing', 'novel-compatible-spacing']
    assert [r['mode'] for r in report['runs']] == modes and sum(r['records'] for r in report['runs']) == 1128312, 'all eight complete broad streams'
    for run, parent in zip(report['runs'], v['parents']['broad']['runs'], strict=True):
        raw = v['parents']['broad_inputs']['sources'][run['source']]['text'].encode()
        assert run['source'] == parent['source'] and run['source_sha256'] == parent['source_sha256'] == sha(raw), 'all original broad input bytes'
        assert run['exit_codes'] == [0, 0] and run['records'] == parent['records'] and run['original_bytes_conserved'], 'complete original broad frames'
        assert run['before_jsonl_sha256'] == parent['after_jsonl_sha256'], 'exact prior broad baseline'
        flags = ['--dict-compatible'] if 'compatible' in run['mode'] else ['--dict-only'] if 'headword' in run['mode'] else []
        prior = v['source_evidence']['baseline']['runs'][0]['command'][0]
        assert len(run['commands']) == 2 and [c[0] for c in run['commands']] == [prior, v['binding']['binaries']['klem']['path']], 'both actual bound broad binaries'
        for command in run['commands']:
            assert command[1:4] == ['text', run['actual_source'], '--dictionary'] and command[4] in report['frozen_inputs'] and command[5:] == flags+(['--suggest-spacing'] if 'spacing' in run['mode'] else []), 'actual broad filter/spacing command'
        if run['mode'].startswith('candidate-'):
            assert not run['changed_frames'] and run['new_family_paths'] == 0 and run['before_jsonl_sha256'] == run['after_jsonl_sha256'], 'all candidate streams unchanged'
            continue
        assert len(run['changed_frames']) == 1, 'one original novel occurrence per policy'
        change = run['changed_frames'][0]; added = additions(change['before'], change['after'])
        start, end = change['after']['span']['start'], change['after']['span']['end']
        assert raw[start:end].decode() == change['after']['surface'] == '주렴', 'exact original novel occurrence'
        begin = raw.rfind(b'\n', 0, start)+1; finish = raw.find(b'\n', end); finish = len(raw) if finish < 0 else finish
        assert change['line_byte_start'] == begin and change['complete_original_line'] == raw[begin:finish].decode(), 'complete original novel context'
        assert change['id'] == f"gentle-command-broad-{run['mode']}-{start}-{end}" and change['contextual_verdict'] == 'unjudged', 'individual novel hypothesis remains unjudged'
        heads = [['주다'], ['줗다']] if run['mode'] == 'novel-raw' else [['주다']]
        assert change['new_paths'] == added and [list(l['text'] for l in p['lemmas']) for p in added] == heads and run['new_family_paths'] == len(heads), 'all exact novel candidate additions'


def inspect_context(v):
    review = v['context']; terminal(review, 'bounded-novel-context-review-recorded')
    assert review['authored_after_runtime_observation'] and review['independent_review'] == 'pending' and not review['full_coverage_complete'], 'bounded contextual inference scope'
    lookup = review['missing_krdict_lookup']
    assert lookup['command'][:3] == [v['binding']['binaries']['klem']['path'], 'dict', 'lookup'] and lookup['command'][3] in review['frozen_inputs'] and lookup['command'][4:] == ['주렴'], 'actual bound contextual dictionary lookup'
    assert lookup['exit_code'] == 0 and sha(lookup['json'].encode()) == lookup['stdout_sha256'], 'actual contextual lookup bytes'
    assert json.loads(lookup['json'])['entries'] == [], 'actual missing dictionary headword'
    reference = review['primary_lexical_reference']
    assert reference['publisher'] == '한국가사문학관' and reference['url'] == 'https://gasa.go.kr/?gasa=18&mode=view&pg=3&uid=132' and reference['short_excerpt'] == '주렴(珠簾): 구슬 따위를 꿰어 만든 발.', 'original primary noun reference'
    assert reference['retrieval'] == 'Primary publisher search-index excerpt verified; direct web-tool fetch timed out.' and reference['classification'] == 'Reference for the noun; not a new imported KRDict entry.', 'bounded actual reference retrieval'
    changes = [(r['mode'], c) for r in v['broad']['runs'] for c in r['changed_frames']]
    assert len(review['records']) == len(changes) == 5, 'all five separately reviewed novel records'
    for row, (mode, change) in zip(review['records'], changes, strict=True):
        assert row['original_change'] == change and row['mode'] == mode, 'exact original contextual record'
        assert row['exact_command_candidate'] in change['new_paths'] and [p['text'] for p in row['exact_command_candidate']['lemmas']] == ['주다'], 'exact reviewed command hypothesis'
        assert row['inference'] is True and row['word_lemma_hypothesis'] == '주렴' and row['command_contextual_disposition'] == 'not_supported_in_this_passage', 'contextual noun inference is separate'
        assert row['raw_word_command_licence'] == 'valid possible standalone command; retain' and row['other_raw_hypotheses'] == 'unjudged' and row['independent_review'] == 'pending', 'valid raw ambiguity not globally forbidden'


def inspect(v):
    source_audit.inspect(v['source_evidence'])
    inspect_bindings(v); inspect_streams(v); inspect_native(v)
    inspect_gold(v); inspect_broad(v); inspect_context(v)
    return dict(rust_tests=1182, source_streams=36, source_frames=2160, target_checks=468,
                native_entries=47, annotated_rows=66570, changed_annotated_rows=0,
                broad_frames=1128312, changed_broad_records=5,
                contextual_review='one bounded noun inference; independent review pending',
                full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
