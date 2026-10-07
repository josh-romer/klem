"""Replay actual CLI outputs against complete RI captures without changing them."""
import argparse
import gzip
import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

from doeda_native_corpora import words_from_cli
from literary_ri_prefinal_audit import BASE, ROOT, match, read, sha
from literary_ri_prefinal_preservation import digest


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def replay(cli, output, broad=True):
    assert not output.exists(), 'Preserve each terminal attempt under its original path'
    cli = cli.resolve(strict=True)
    database = ROOT / 'data/dictionaries/krdict/krdict.db'
    paths = [cli, database, Path(__file__), BASE / 'literary-ri-prefinal-source-discovery.json.gz',
             BASE / 'literary-ri-prefinal-prototype-cli.json.gz',
             BASE / 'literary-ri-prefinal-mode-scope-review.json',
             BASE / 'literary-ri-prefinal-supplemental-b.json',
             BASE / 'literary-ri-prefinal-prototype-broad.json.gz',
             BASE / 'literary-ri-prefinal-prototype-corpora.json.gz',
             ROOT / 'tests/fixtures/literary-ri-prefinal-policy-validity.json']
    frozen = {str(p): file_sha(p) for p in paths}
    source, prototype, modes, supplement, broad_capture, corpora, policy = [read(p) for p in paths[3:]]
    report = {'schema_version': 1, 'state': 'running', 'cli': str(cli),
              'cli_sha256': frozen[str(cli)], 'frozen_inputs': frozen,
              'runs': [], 'probes': [], 'broad': [], 'corpora': None,
              'producer': {'text': Path(__file__).read_text(), 'sha256': file_sha(__file__)},
              'scope': 'Actual current CLI equality with immutable reviewed captures. '
                       'Broad stream hashes bind every output byte; annotated gold outcomes '
                       'are separately recomputed by the preservation audit. '
                       'Added RI paths retain their unjudged context and independent review.'}

    def save():
        data = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode()
        output.write_bytes(gzip.compress(data, mtime=0) if output.suffix == '.gz' else data)

    save()
    try:
        for run in prototype['streams']:
            original = next(r for r in source['runs'] if (r['encoding'], r['mode']) == (run['encoding'], run['mode']))
            command = [str(cli), *original['command'][1:]]
            result = subprocess.run(command, cwd=ROOT,
                input=unicodedata.normalize(run['encoding'], source['input']).encode(),
                capture_output=True, check=True)
            assert result.stdout.decode() == run['jsonl']
            assert len(result.stdout.splitlines()) == 275
            report['runs'].append({'encoding': run['encoding'], 'mode': run['mode'],
                'command': command, 'exit_code': 0, 'records': 275,
                'sha256': sha(result.stdout), 'exact_prototype_output': True})
        conditional = {c['case_id'] for c in modes['cases']}
        expected_probes = {(r['case'], r['encoding'], r['mode']): r for r in prototype['probes']}
        for run in supplement['probes']:
            expected_probes[(run['case'], run['encoding'], run['mode'])] = run
        assert len(expected_probes) == 168
        for case in policy['cases']:
            for encoding in ['NFC', 'NFD']:
                for mode in ['raw', 'compatible']:
                    text = unicodedata.normalize(encoding, case['surface'])
                    command = [str(cli), 'word', text, '--dictionary', str(database),
                               *(['--dict-compatible'] if mode == 'compatible' else [])]
                    result = subprocess.run(command, cwd=ROOT, capture_output=True, check=True)
                    expected = expected_probes[(case['id'], encoding, mode)]
                    assert result.stdout.decode() == expected['json']
                    word = json.loads(result.stdout)
                    assert word['normalized'] == case['surface']
                    observations = []
                    for judgment in case['judgments']:
                        present = [p for p in word['analyses'] if match(p, judgment)]
                        verdict = 'unjudged' if case['id'] in conditional and mode == 'raw' else judgment['verdict']
                        assert bool(present) == (verdict != 'forbidden')
                        observations.append({'judgment': judgment['id'], 'mode_verdict': verdict,
                                             'matching_paths': present})
                    report['probes'].append({'case': case['id'], 'encoding': encoding, 'mode': mode,
                        'command': command, 'exit_code': 0, 'sha256': sha(result.stdout),
                        'exact_prototype_output': True, 'observations': observations})
        save()
        print('Actual CLI:6x275 source frames and168 exact named NFC/NFD outputs passed.', flush=True)
        if broad:
            for previous in broad_capture['comparisons']:
                path = Path(previous['source'])
                assert file_sha(path) == previous['source_sha256']
                frozen[str(path)] = file_sha(path)
                command = [str(cli), *previous['commands'][1][1:]]
                h, count, cursor = hashlib.sha256(), 0, 0
                original = path.read_bytes()
                with subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE) as child:
                    for line in child.stdout:
                        h.update(line)
                        row = json.loads(line)
                        assert row['span']['start'] == cursor
                        cursor = row['span']['end']
                        assert original[row['span']['start']:cursor].decode() == row['surface']
                        count += 1
                    assert child.wait() == 0
                assert cursor == len(original) and count == previous['records']
                assert h.hexdigest() == previous['after_jsonl_sha256']
                report['broad'].append({'source': str(path), 'source_sha256': frozen[str(path)],
                    'mode': previous['mode'], 'command': command, 'exit_code': 0, 'records': count,
                    'sha256': h.hexdigest(), 'exact_prototype_output': True, 'original_bytes_conserved': True})
                save()
                print(previous['mode'], count, 'actual frames byte-exact', flush=True)
        words = words_from_cli(cli, sorted(corpora['after_words']))
        assert words == corpora['after_words']
        report['corpora'] = {'unique_surfaces': len(words), 'word_analyses_sha256': digest(words),
                             'exact_prototype_word_analyses': True, 'annotated_rows': 66570}
        assert all(file_sha(p) == h for p, h in frozen.items())
        report.update(state='passed', exit_code=0, inputs_unchanged=True,
                      contextual_verdict='unjudged', independent_review='pending')
        save()
        print('Actual CLI corpus:32096 exact word analyses; all inputs unchanged.', flush=True)
    except BaseException as error:
        report.update(state='failed', error=repr(error), inputs_unchanged=all(file_sha(p) == h for p, h in frozen.items()))
        save()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skip-broad', action='store_true')
    args = parser.parse_args()
    replay(args.cli, args.output, not args.skip_broad)
