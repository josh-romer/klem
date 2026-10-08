"""Require a successful immutable package receipt before accepting release runtime evidence."""
from literary_question_geona_runtime import ROOT, read, sha


def package_paths(report):
    receipt_path = ROOT / 'docs/literary-question-geona-package-nix.json'
    assert report['package_sha256'] == sha(receipt_path.read_bytes()), 'package receipt bytes'
    receipt = read(receipt_path)
    assert receipt['state'] == 'passed' and receipt['exit_code'] == 0, 'installed package success'
    assert receipt['snapshot_unchanged'] is True, 'unchanged package sources'
    assert sha(receipt['producer']['text'].encode()) == receipt['producer']['sha256'], 'package producer bytes'
    assert report['snapshot_files'] == receipt['snapshot']['files'], 'complete package source scope'
    assert len(report['snapshot_files']) == 957, 'complete package source scope'
    outputs = receipt['outputs']
    assert len(outputs) == len(set(outputs)) == 3, 'three actual packages'
    paths = {}
    for label, suffix in [('klem', '-klem-0.1.0'), ('web-assets', '-klem-web-assets-0.1.0'),
                          ('corpus-adapter', '-klem-corpus-adapter-0.1.0')]:
        matching = [p for p in outputs if p.startswith('/nix/store/') and p.endswith(suffix)]
        assert len(matching) == 1, 'unique actual package output'
        paths[label] = matching[0]
    return paths
