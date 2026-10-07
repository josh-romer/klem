"""Verify exact historical sources of both tested literary-prefinal packages."""
import argparse
import gzip
import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from reported_dana_sources import inspect as verify_baseline, nar_contents, source_texts
from reported_deoni_complete_sources import source_store_path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


@lru_cache(maxsize=1)
def baseline_texts():
    verify_baseline()
    texts = source_texts()
    for name, update in read(ROOT / 'docs/reported-dana-integration.json.gz')['files'].items():
        assert update['before_sha256'] == (sha(texts[name].encode()) if name in texts else None)
        assert sha(update['after_text'].encode()) == update['after_sha256']
        texts[name] = update['after_text']
    manifest = read(ROOT / 'docs/reported-dana-package-sources.json')
    assert set(texts) == set(manifest['files']) and len(texts) == 859
    for name, text in texts.items():
        assert sha(text.encode()) == manifest['files'][name]['sha256']
    return texts


def verify(proof, receipt, baseline):
    assert proof['state'] == receipt['state'] == 'passed'
    assert receipt['exit_code'] == 0 and receipt['snapshot_unchanged']
    assert proof['snapshot_files'] == receipt['snapshot']['files']
    assert len(proof['snapshot_files']) == 901 and len(baseline) == 859
    assert sha(proof['producer']['text'].encode()) == proof['producer']['sha256']
    current = dict(baseline)
    assert len(proof['updates']) == 53
    for name, update in proof['updates'].items():
        assert update['before_sha256'] == (sha(baseline[name].encode()) if name in baseline else None)
        assert sha(update['after_text'].encode()) == update['after_sha256']
        assert name not in baseline or update['after_sha256'] != update['before_sha256']
        current[name] = update['after_text']
    assert set(current) == set(proof['snapshot_files'])
    for name, text in current.items():
        record = proof['snapshot_files'][name]
        assert sha(text.encode()) == record['sha256'] and len(text.encode()) == record['bytes'], name
    assert set(proof['profiles']) == {'klem', 'web-assets'}
    mapped = set()
    for label, profile in proof['profiles'].items():
        assert profile['source'] == receipt['source_profiles'][label]
        assert profile['package'] in receipt['outputs']
        assert profile['actual_dump_verified'] is True
        raw = profile['derivation_json_text']
        assert sha(raw.encode()) == profile['derivation_json_sha256']
        drv = json.loads(raw)
        assert set(drv) == {profile['derivation']}
        assert drv[profile['derivation']]['env']['src'] == profile['source']
        assert drv[profile['derivation']]['outputs']['out']['path'] == profile['package']
        files = profile['files']
        assert len(files) == (884 if label == 'klem' else 18)
        texts = {}
        for name, record in files.items():
            path = name if label == 'klem' else 'web/' + name
            assert record['snapshot_path'] == path and isinstance(record['executable'], bool)
            assert {k: v for k, v in record.items() if k not in ['snapshot_path', 'executable']} == proof['snapshot_files'][path]
            texts[name] = current[path]
            mapped.add(path)
        digest, count = nar_contents(files, profile['directories'], texts)
        assert (digest, count) == (profile['nar_sha256'], profile['nar_bytes'])
        assert source_store_path(digest) == profile['source']
        assert profile['nar_command'] == ['nix-store', '--dump', profile['source']]
    assert mapped == set(current)
    return current


def inspect(proof_path):
    proof = read(proof_path)
    assert proof['receipt_sha256'] == sha((ROOT / 'docs/literary-ri-prefinal-package-nix.json').read_bytes())
    for key in ['source_manifest', 'integration']:
        assert proof['baseline'][key + '_sha256'] == sha((ROOT / proof['baseline'][key]).read_bytes())
    return verify(proof, read(ROOT / 'docs/literary-ri-prefinal-package-nix.json'), baseline_texts())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof', type=Path, required=True)
    args = parser.parse_args()
    print('Verified all historical literary-prefinal source inputs:', len(inspect(args.proof)))


@lru_cache(maxsize=1)
def package_source_texts_cached():
    return inspect(ROOT / "docs/literary-ri-prefinal-historical-sources.json.gz")


def package_source_texts(package):
    assert package == read(ROOT / "docs/literary-ri-prefinal-package-nix.json")
    return package_source_texts_cached()
