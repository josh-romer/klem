"""Capture every actual Rust adapter row and compare with reviewed RI outputs."""
import argparse
import gzip
import json
import subprocess
from pathlib import Path

from literary_ri_prefinal_audit import BASE, ROOT, read, sha
from literary_ri_prefinal_replay import file_sha


def replay(adapter, output):
    assert not output.exists()
    adapter = adapter.resolve(strict=True)
    original = BASE / 'literary-ri-prefinal-prototype-adapter.json.gz'
    capture = read(original)
    frozen = {str(p): file_sha(p) for p in [adapter, original, Path(__file__),
        ROOT / 'examples/evaluate.rs', ROOT / 'tools/corpus.rs']}
    report = {'schema_version': 1, 'state': 'running', 'adapter': str(adapter),
              'adapter_sha256': frozen[str(adapter)], 'frozen_inputs': frozen,
              'original_capture_sha256': file_sha(original), 'runs': [],
              'producer': {'text': Path(__file__).read_text(), 'sha256': file_sha(__file__)},
              'scope': 'Every actual Rust adapter row and summary compared byte for byte '
                       'with reviewed RI captures; gold judgments retain original annotations.'}

    def save():
        data = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode()
        output.write_bytes(gzip.compress(data, mtime=0) if output.suffix == '.gz' else data)

    save()
    try:
        for previous in capture['runs']:
            source = ROOT / previous['source']
            assert file_sha(source) == previous['source_sha256']
            frozen[str(source)] = file_sha(source)
            command = [str(adapter), previous['corpus'], previous['source']]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, check=True)
            expected = next(s for s in previous['streams'] if s['mode'] == 'after')
            assert result.stdout.decode() == expected['jsonl']
            report['runs'].append({k: previous[k] for k in ['corpus', 'partition', 'source', 'source_sha256']}
                | {'command': command, 'exit_code': 0, 'rows': expected['rows'],
                   'sha256': sha(result.stdout), 'exact_prototype_output': True})
            save()
            print(previous['corpus'], previous['partition'], expected['rows'], 'actual Rust rows exact', flush=True)
        assert sum(r['rows'] for r in report['runs']) == 66570
        assert all(file_sha(p) == h for p, h in frozen.items())
        report.update(state='passed', exit_code=0, inputs_unchanged=True,
                      contextual_verdict='unjudged', independent_review='pending')
        save()
    except BaseException as error:
        report.update(state='failed', error=repr(error))
        save()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adapter', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    replay(args.adapter, args.output)
