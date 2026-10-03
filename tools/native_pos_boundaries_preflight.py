"""Freeze additional COV-021q boundary probes without replacing the first 148."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--cli', type=Path, required=True)
p.add_argument('--dictionary', type=Path, default=ROOT / 'data/dictionaries/krdict/krdict.db')
a = p.parse_args()
out = ROOT / 'tests/fixtures/native-pos-boundaries.json'
if out.exists():
    p.error('Refusing to overwrite frozen fixture: ' + str(out))

def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()

surfaces = [
    '발그스레해다', '발그스레해다가', '발그스레하는가보다',
    '발그스레하는척하다', '발그스레하는양하다', '발그스레하는체하다',
    '발그스레하는듯하다', '발그스레하는듯싶다', '발그스레하음세',
    '발그스레해대는', '발그스레하지않아대는', '발그스레하려하는',
    '발그스레하지않으려고하는', '발그스레함이느냐', '발그스레함이로구나',
    '발그스레하게되는', '발그스레하지못할라치면', '발그스레하였느니',
    '발그스레하시느니', '발그스레하옵느니', '발그스레하시다더군요',
    '발그스레하였다는구나', '발그스레하시는척하다',
]
words = {surface: json.loads(subprocess.check_output([
    str(a.cli), 'word', surface, '--dictionary', str(a.dictionary)])) for surface in surfaces}
result = dict(schema_version=1, checklist='COV-021q', before_revision='be1b115',
    cli=str(a.cli), cli_sha256=sha(a.cli), dictionary_sha256=sha(a.dictionary),
    extractor_sha256=sha(__file__), before_words={s: {k: v for k, v in w.items() if k != 'dictionary'} for s, w in words.items()},
    complete_before_annotations={s: w['dictionary'] for s, w in words.items()},
    scope='Additional authored diagnostics for existing class-sensitive result transfer, conjecture, pretence, repetition, prefinals, negatives and later owners. Native fields and the original 148-surface fixture remain unchanged; these probes are not contextual gold.')
with out.open('x') as file:
    json.dump(result, file, ensure_ascii=False, indent=2); file.write('\n')
print(len(surfaces), 'additional boundary probes')
