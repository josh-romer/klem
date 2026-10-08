"""Bind the optional corpus lexicon to the preserved pre-implementation evidence."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inspect(lexicon, prepared):
    assert lexicon['schema'] == 1
    assert lexicon['partition'] == prepared['corpus_metadata']['partition'] == 'train'
    assert lexicon['source_url'] == prepared['corpus_metadata']['url']
    assert lexicon['license'] == prepared['corpus_metadata']['license'] == 'CC BY-SA 4.0'
    assert lexicon['license_url'] == 'https://creativecommons.org/licenses/by-sa/4.0/'
    assert 'converted from manual' in lexicon['attribution']
    expected_files = {f'data/corpora/kaist/{Path(p).name}': value for p, value in prepared['source_files'].items()}
    assert lexicon['source_files'] == expected_files
    assert len(lexicon['names']) == 1
    name = lexicon['names'][0]
    assert (name['id'], name['headword'], name['pos'], name['xpos']) == (
        'ud-ko-kaist:proper-name:park', '박', 'PROPN', 'nq')
    assert name['observations'] == prepared['observations']
    assert len(name['observations']) == 5
    for observation in name['observations']:
        assert observation['source_partition'] == 'train'
        row = observation['original_row']
        assert row[1:5] == ['박', '박', 'PROPN', 'nq']
        assert row[0] == observation['token_id']
        block = observation['complete_original_sentence']
        assert '\t'.join(row) in block.splitlines()
        assert f"# sent_id = {observation['sentence_id']}" in block.splitlines()
    native = prepared['complete_native_same_head_entries']
    assert set(native) == {'krdict:57518', 'krdict:57517'}
    assert all(e['headword'] == '박' for e in native.values())
    assert native['krdict:57518']['pos'] == '명사'
    assert native['krdict:57517']['pos'] == '의존 명사'
    thing = prepared['complete_native_bound_noun_entry']
    assert thing['id'] == 'krdict:62835' and thing['pos'] == '의존 명사'
    sense = next(s for s in thing['senses'] if s['id'] == '3')
    assert any('박 선생님 것' in line for group in sense['examples'] for line in group)
    return {'training_rows': 5, 'separate_proper_name_identities': 1,
            'preserved_unrelated_homonyms': 2, 'contextual_review_complete': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, default=ROOT)
    args = parser.parse_args()
    lexicon = json.loads((ROOT / 'src/dictionary/proper_names.json').read_text())
    prepared = json.loads(gzip.decompress((ROOT / 'docs/surname-corpus-preparation.json.gz').read_bytes()))
    result = inspect(lexicon, prepared)
    # Original local corpus files are optional for portable/Nix checks. When
    # present, verify complete bytes and every complete original sentence.
    verified = 0
    for name, expected in lexicon['source_files'].items():
        path = args.corpus_root / name
        if path.exists():
            raw = path.read_bytes()
            assert len(raw) == expected['bytes']
            assert hashlib.sha256(raw).hexdigest() == expected['sha256']
            verified += 1
            if path.suffix == '.conllu':
                sentences = set(raw.decode().strip().split('\n\n'))
                assert all(o['complete_original_sentence'] in sentences
                           for o in lexicon['names'][0]['observations'])
    result['local_source_files_verified'] = verified
    print(result)


if __name__ == '__main__':
    main()
