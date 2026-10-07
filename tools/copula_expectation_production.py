"""Replay complete prototype streams against a production CLI and evaluator."""
import argparse
import gzip
import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    path = ROOT / path
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replay(command, expected_hash, expected_records, request=None):
    digest = hashlib.sha256()
    count = 0
    # Source requests are small enough to supply through a temporary input file;
    # this avoids blocking on a write while the CLI produces a large stream.
    import tempfile
    with tempfile.TemporaryFile() as input_file:
        if request is not None:
            input_file.write(request.encode())
            input_file.seek(0)
        process = subprocess.Popen(command, cwd=ROOT, stdin=input_file, stdout=subprocess.PIPE)
        try:
            for line in process.stdout:
                digest.update(line)
                count += 1
            code = process.wait()
            assert code == 0, (command, code)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait()
    actual_hash = digest.hexdigest()
    assert (actual_hash, count) == (expected_hash, expected_records), (command, actual_hash, count)
    return {'command': command, 'exit_code': code, 'sha256': actual_hash, 'records': count,
            'expected_sha256': expected_hash}


def capture(cli, output):
    from doeda_native_corpora import words_from_cli
    cli = Path(cli).resolve()
    evaluator = cli.parent / 'examples/evaluate'
    db = ROOT / 'data/dictionaries/krdict/krdict.db'
    paths = ['docs/copula-expectation-source-streams.json.gz',
             'docs/copula-expectation-corpora.json.gz', 'docs/copula-expectation-broad.json.gz',
             'src/engine.rs', 'src/grammar.rs', 'src/dictionary/attachment.rs',
             'web/src/grammar-labels.json']
    frozen = {p: sha(ROOT / p) for p in paths}
    binaries = {str(p): sha(p) for p in [cli, evaluator, db]}
    source_runs = []
    source = read(paths[0])
    for family, report in source['reports'].items():
        original = read(f'docs/{family}-cohort.json.gz')
        assert report['prior_cohort_sha256'] == sha(ROOT / f'docs/{family}-cohort.json.gz')
        for encoding, modes in report['runs'].items():
            request = unicodedata.normalize(encoding, original['input'])
            for mode, run in modes.items():
                assert hashlib.sha256(request.encode()).hexdigest() == run['input_sha256']
                result = replay([str(cli), *run['command'][1:]], run['after_sha256'], run['records'], request)
                source_runs.append({'family': family, 'encoding': encoding, 'mode': mode,
                                    'input_sha256': run['input_sha256'], **result})
                print('source', family, encoding, mode, result['records'], flush=True)
    corpus = read(paths[1])
    corpus_runs = []
    for old in corpus['corpora']:
        assert sha(ROOT / old['source']) == old['source_sha256']
        expected_hash = hashlib.sha256(old['after_jsonl'].encode()).hexdigest()
        result = replay([str(evaluator), old['corpus'], old['source']], expected_hash, old['report_lines'])
        corpus_runs.append({k: old[k] for k in ['corpus', 'partition', 'source', 'source_sha256']} | result)
        print('corpus', old['corpus'], old['partition'], result['records'] - 1, flush=True)
    words = words_from_cli(cli, sorted(corpus['after_words']))
    assert words == corpus['after_words'] and len(words) == 32096
    word_hash = hashlib.sha256(json.dumps(words, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    broad = read(paths[2])
    broad_runs = []
    for old in broad['comparisons']:
        assert sha(old['source']) == old['source_sha256']
        command = [str(cli), *old['commands'][1][1:]]
        result = replay(command, old['after_jsonl_sha256'], old['records'])
        broad_runs.append({k: old[k] for k in ['source', 'source_sha256', 'mode']} | result)
        print('broad', old['mode'], result['records'], flush=True)
    assert len(source_runs) == 12 and sum(r['records'] for r in source_runs) == 309660
    assert sum(r['records'] - 1 for r in corpus_runs) == 66570
    assert len(broad_runs) == 8 and sum(r['records'] for r in broad_runs) == 1128312
    assert all(sha(ROOT / p) == value for p, value in frozen.items())
    assert all(sha(p) == value for p, value in binaries.items())
    producer = Path(__file__)
    result = {'schema_version': 1, 'state': 'passed', 'prototype_parity': True,
              'frozen_inputs': frozen, 'binaries': binaries, 'inputs_unchanged': True,
              'source_runs': source_runs, 'corpus_runs': corpus_runs, 'broad_runs': broad_runs,
              'corpus_words': len(words), 'corpus_word_sha256': word_hash,
              'producer': {'text': producer.read_text(), 'sha256': sha(producer)}}
    output = Path(output)
    assert not output.exists()
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('Production CLI/evaluator exactly match every preserved source, gold and broad frame.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    capture(args.cli, args.output)
