"""Bind installed integration outputs to the actual current evaluated source profiles."""
import hashlib
import json
import subprocess
from pathlib import Path

import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]
OUT = args.output
assert not OUT.exists()
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
index = subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=ROOT)
outputs = subprocess.check_output(['nix', 'build', '--offline', '--cores', '4', '--max-jobs', '1', '--no-link', '--print-out-paths', *['.#packages.x86_64-linux.' + n for n in ['klem', 'web-assets', 'corpus-adapter', 'web']]], cwd=ROOT, text=True).splitlines()
assert len(outputs) == 4
receipt = {'source_profiles': {}}
for name in ['klem', 'web-assets', 'corpus-adapter']:
    source = Path(subprocess.check_output(['nix', 'eval', '--offline', '--raw', '.#packages.x86_64-linux.' + name + '.src'], cwd=ROOT, text=True).strip())
    files = {}
    for path in source.rglob('*'):
        assert not path.is_symlink()
        if not path.is_file():
            continue
        relative = str(path.relative_to(source))
        original = 'web/' + relative if name == 'web-assets' else relative
        data = path.read_bytes()
        assert data == (ROOT / original).read_bytes()
        files[relative] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'snapshot_path': original}
    receipt['source_profiles'][name] = {'source': str(source), 'files': files}
sha = lambda raw: hashlib.sha256(raw).hexdigest()
profiles = {}
for name, source_record in receipt['source_profiles'].items():
    ending = {'klem': '-klem-0.1.0', 'web-assets': '-klem-web-assets-0.1.0', 'corpus-adapter': '-klem-corpus-adapter-0.1.0'}[name]
    package = next(p for p in outputs if p.endswith(ending))
    derivation = subprocess.check_output(['nix-store', '--query', '--deriver', package], text=True).strip()
    raw = subprocess.check_output(['nix', 'derivation', 'show', derivation])
    parsed = json.loads(raw)
    assert set(parsed) == {derivation}
    drv = parsed[derivation]
    assert drv['outputs']['out']['path'] == package
    assert drv['env']['src'] == source_record['source']
    source = Path(source_record['source'])
    actual_files = {}
    for path in source.rglob('*'):
        assert not path.is_symlink()
        if not path.is_file():
            continue
        relative = str(path.relative_to(source))
        expected = source_record['files'][relative]
        data = path.read_bytes()
        assert sha(data) == expected['sha256'] and len(data) == expected['bytes']
        assert data == (ROOT / expected['snapshot_path']).read_bytes()
        actual_files[relative] = expected
    assert actual_files == source_record['files']
    profiles[name] = {'package': package, 'derivation': derivation, 'derivation_json': raw.decode(), 'derivation_json_sha256': sha(raw), 'source': str(source), 'files': actual_files}
launcher_package = next(p for p in outputs if p.endswith('-klem-web'))
launcher = Path(launcher_package) / 'bin/klem-web'
text = launcher.read_text()
assert profiles['klem']['package'] + '/bin/klem-web' in text
assert profiles['web-assets']['package'] + '/share/klem-web' in text
assert profiles['klem']['files'] == profiles['corpus-adapter']['files']
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip() == head
assert subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=ROOT) == index
assert all(sha((ROOT / f['snapshot_path']).read_bytes()) == f['sha256']
           for p in profiles.values() for f in p['files'].values())
result = {'state': 'passed', 'outputs': outputs, 'head': head, 'exit_code': 0, 'inputs_unchanged': True, 'head_unchanged': True, 'index_unchanged': True, 'profiles': profiles, 'launcher': {'package': launcher_package, 'text': text, 'sha256': sha(launcher.read_bytes())}, 'producer': {'text': Path(__file__).read_text(), 'sha256': sha(Path(__file__).read_bytes())}, 'scope': 'All actual installed CLI/server, frontend and adapter derivations bind the exact Git-backed evaluated sources; every source file equals the current integration source. Every bound source file and HEAD/index remain unchanged during this binding. Actual launcher binds the same CLI/server and assets. Runtime/browser/adapter/performance remain separate.', 'full_coverage_complete': False}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print('Bound installed exact source profiles:', {name: len(v['files']) for name, v in profiles.items()}, 'and launcher', flush=True)
