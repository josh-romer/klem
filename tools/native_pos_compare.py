"""Audit the reviewed POS change against the original eight broad streams."""
import argparse
import copy
import gzip
import hashlib
import itertools
import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--before-cli', type=Path, required=True)
parser.add_argument('--cli', type=Path, required=True)
parser.add_argument('--dictionary', type=Path, default=ROOT / 'data/dictionaries/krdict/krdict.db')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    parser.error('Refusing to overwrite observations: ' + str(args.output))


def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def run_word(cli, surface, dictionary, flags):
    return json.loads(subprocess.check_output([str(cli), 'word', surface, '--dictionary', str(dictionary), *flags]))


def project(annotation, adjective=False):
    result = copy.deepcopy(annotation)
    for slot in result['lemmas']:
        for entry in slot['entries']:
            evidence = entry.pop('independent_pos', None)
            if evidence is not None:
                assert entry['id'] == 'krdict:600930' and entry['pos'] == '동사'
                assert evidence['source_id'] == 'opendict:569243'
                assert evidence['native_profile_sha256'] == sources['native_profile_sha256']
                if adjective:
                    entry['pos'] = '형용사'
    return result


sources = json.load((ROOT / 'tests/fixtures/native-pos-sources.json').open())
prior = json.load((ROOT / 'docs/complex-bieup-observations.json').open())
comparisons, changes, control_cache = [], [], {}
with tempfile.TemporaryDirectory(prefix='klem-native-pos-control-') as temporary:
    control = Path(temporary) / 'authored-adjective-control.db'
    with sqlite3.connect(args.dictionary.resolve().as_uri() + '?mode=ro', uri=True) as native, sqlite3.connect(control) as adapter:
        native.backup(adapter)
        row = adapter.execute('SELECT data FROM entries WHERE id=?', ('krdict:600930',)).fetchone()
        entry = json.loads(row[0])
        assert entry == sources['source_entries'][0]
        # Explicitly authored counterfactual adapter, never a repaired export.
        entry['pos'] = '형용사'
        adapter.execute('UPDATE entries SET pos=?,data=? WHERE id=?', ('형용사', json.dumps(entry, ensure_ascii=False), 'krdict:600930'))
        adapter.commit()

    def audit(before, after, mode, flags):
        assert {k: v for k, v in before.items() if k not in ('analysis', 'dictionary', 'spacing', 'breakdowns')} == {
            k: v for k, v in after.items() if k not in ('analysis', 'dictionary', 'spacing', 'breakdowns')}
        if before.get('analysis') is not None:
            assert after.get('analysis') is not None
            if 'compatible' not in mode:
                assert before['analysis'] == after['analysis']
            if before != after:
                surface = after['analysis']['normalized']
                key = (surface, tuple(flags))
                if key not in control_cache:
                    control_cache[key] = run_word(args.before_cli, surface, control, flags)
                expected = control_cache[key]
                assert after['analysis'] == {k: v for k, v in expected.items() if k != 'dictionary'}, (mode, surface)
                assert project(after['dictionary'], True) == expected['dictionary'], (mode, surface, 'class-control mismatch')
                # Every native field retained for remaining lookup entries.
                projected = project(after['dictionary'])
                for slot in projected['lemmas']:
                    previous = next(s for s in before['dictionary']['lemmas'] if s['lemma'] == slot['lemma'])
                    assert slot == previous, (mode, surface, 'native fields changed')
                assert (projected['source'], projected['fingerprint']) == (before['dictionary']['source'], before['dictionary']['fingerprint'])
                # Any membership/assessment change requires the reviewed entry.
                assert any(e['id'] == 'krdict:600930' for s in before['dictionary']['lemmas'] for e in s['entries'])
        if 'spacing' in before:
            bs, ns = before['spacing'], after['spacing']
            assert {k: v for k, v in bs.items() if k != 'alternatives'} == {k: v for k, v in ns.items() if k != 'alternatives'}
            assert len(bs['alternatives']) == len(ns['alternatives'])
            for b, a in zip(bs['alternatives'], ns['alternatives']):
                assert {k: v for k, v in b.items() if k != 'records'} == {k: v for k, v in a.items() if k != 'records'}
                assert len(b['records']) == len(a['records'])
                for br, ar in zip(b['records'], a['records']):
                    audit(br, ar, mode, flags)
        if 'breakdowns' in before:
            if 'compatible' not in mode:
                assert before['breakdowns'] == after['breakdowns']
            else:
                # Reindex only retained candidates, preserving component order.
                for analysis, parts in zip(after['analysis']['analyses'], after['breakdowns']):
                    if analysis in before['analysis']['analyses']:
                        index = before['analysis']['analyses'].index(analysis)
                        assert parts == before['breakdowns'][index]

    for previous in prior['comparisons']:
        mode, source = previous['mode'], Path(previous['source'])
        assert sha(source) == previous['source_sha256']
        flags = ['--dict-compatible'] if 'compatible' in mode else ['--dict-only'] if 'headword' in mode else []
        command = ['text', str(source), '--dictionary', str(args.dictionary), *flags]
        if 'spacing' in mode:
            command.append('--suggest-spacing')
        processes = [subprocess.Popen([str(cli), *command], stdout=subprocess.PIPE) for cli in (args.before_cli, args.cli)]
        before_hash, after_hash = hashlib.sha256(), hashlib.sha256()
        count = changed = 0
        try:
            for b, a in itertools.zip_longest(*(p.stdout for p in processes)):
                assert b is not None and a is not None
                count += 1
                before_hash.update(b); after_hash.update(a)
                if b != a:
                    before, after = json.loads(b), json.loads(a)
                    audit(before, after, mode, flags)
                    changes.append(dict(mode=mode, record_index=count - 1, before=before, after=after))
                    changed += 1
            assert all(p.wait() == 0 for p in processes)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate(); process.wait()
        assert count == previous['records']
        assert before_hash.hexdigest() == previous['after_jsonl_sha256'], (mode, 'original baseline hash differs')
        comparisons.append(dict(mode=mode, source=str(source), source_sha256=sha(source), records=count,
            before_jsonl_sha256=before_hash.hexdigest(), after_jsonl_sha256=after_hash.hexdigest(), changed_records=changed))
        print(mode, count, 'records;', changed, 'changed', flush=True)

report = dict(schema_version=1, checklist='COV-021q', before_revision='be1b115',
    before_cli=str(args.before_cli), before_cli_sha256=sha(args.before_cli), cli=str(args.cli), cli_sha256=sha(args.cli),
    dictionary_sha256=sha(args.dictionary), comparisons=comparisons, complete_changed_records=changes,
    all_raw_and_headword_candidates_unchanged=True, native_fields_unchanged=True,
    all_original_baseline_hashes_verified=True, all_changes_match_the_authored_adjective_control=True,
    control_scope='POS-only authored counterfactual adapter, not a native source repair or contextual gold.',
    interpretation='Exhaustive stream observations; no precision or contextual grammaticality claim.')
with args.output.open('x') as file:
    json.dump(report, file, ensure_ascii=False, indent=2); file.write('\n')
print('Completed', sum(c['records'] for c in comparisons), 'records', flush=True)
