"""Rederive every historical addition, original witness and prior parent."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def pointer(value, path):
    for key in path.split('/')[1:]:
        key = key.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def inputs():
    history = read(ROOT / 'tests/fixtures/gentle-command-history.json')
    return (history,
            read(ROOT / 'docs/gentle-command-history-proof-gentle-command-cohorts.json.gz'),
            read(ROOT / 'docs/literary-question-geona-prototype-legacy-history.json.gz'),
            {name: (ROOT / name).read_bytes() for name in history['source_files_sha256']},
            gzip.decompress((ROOT / 'docs/gentle-command-history-proof-gentle-command-history-retry1.json.gz').read_bytes()))


def inspect(history, cohorts, legacy, originals, captured_raw):
    assert sha(captured_raw) == '841da468a81b4c2bb713f37dac0615782bfe8f7a7edb1f1bab5f034690a6e7e5', 'original immutable prior-parent capture bytes'
    captured = json.loads(captured_raw)
    assert history['state'] == 'complete-gentle-command-history-and-prior-parent-capture-passed' and history['inputs_unchanged'], 'terminal parent capture'
    assert sha(history['producer']['text'].encode()) == history['producer']['sha256'], 'actual history producer'
    assert history['actual_prior_companions'] == captured['actual_prior_companions'], 'every complete actual prior counterpart preserved'
    assert cohorts['state'] == 'complete-original-corpus-history-comparison-passed' and cohorts['inputs_unchanged'], 'terminal complete cohort capture'
    assert sha(cohorts['producer']['text'].encode()) == cohorts['producer']['sha256'], 'actual complete cohort producer'
    archive = ROOT / 'docs/gentle-command-history-proof-gentle-command-cohorts.json.gz'
    assert history['original_cohort_capture_sha256'] == sha(archive.read_bytes()), 'exact original full cohort capture'
    assert [(r['family'], r['surfaces']) for r in cohorts['runs']] == [('corpus', 32096), ('history', 21406)], 'all53502originalwords'
    changed = {}
    for run in cohorts['runs']:
        before, after = run['captures']
        assert before['binary'] == history['prior_cli'], 'actual prior installed CLI'
        assert history['prior_cli_sha256'] == cohorts['frozen_inputs'][history['prior_cli']], 'exact prior executable bytes'
        old_words, new_words = before['words'], after['words']
        assert set(old_words) == set(new_words) and len(old_words) == run['surfaces'], 'all original cohort words'
        observed = []
        for surface, old in old_words.items():
            new = new_words[surface]
            assert {k: v for k, v in old.items() if k != 'analyses'} == {k: v for k, v in new.items() if k != 'analyses'}, 'original word fields'
            assert [a for a in new['analyses'] if a in old['analyses']] == old['analyses'], 'every ordered original candidate'
            if old != new:
                assert run['family'] == 'history', 'no changed annotated corpus candidate words'
                observed.append(surface)
                changed[surface] = dict(before=old, after=new)
        assert observed == run['changed_words'], 'all changed words in order'
    assert history['changed_words'] == changed and len(changed) == 8, 'exact eight captured histories'
    origins = {name for word in changed for name in [w['source'] for w in legacy['origins'][word]]}
    assert set(originals) == set(history['source_files_sha256']) == origins, 'every original source fixture'
    parsed = {}
    for source, raw in originals.items():
        assert sha(raw) == history['source_files_sha256'][source] == legacy['source_files_sha256'][source], 'unchanged original fixture bytes'
        parsed[source] = json.loads(raw)
    expected = []
    for surface, change in changed.items():
        witnesses, contexts = [], []
        for origin in legacy['origins'][surface]:
            assert origin['source_sha256'] == sha(originals[origin['source']]), 'exact original witness digest'
            original = parsed[origin['source']]
            witnesses.append({**origin, 'complete_original_record': pointer(original, origin['pointer'])})
            for key in ['source_cohort_original_groups', 'original_groups']:
                for index, group in enumerate(original.get(key, [])):
                    if surface in json.dumps(group.get('original_group', []), ensure_ascii=False):
                        contexts.append(dict(source=origin['source'], source_sha256=origin['source_sha256'], pointer=f'/{key}/{index}', complete_original_record=group))
        for actual in change['after']['analyses']:
            if actual in change['before']['analyses']:
                continue
            assert actual['rules'].count('ending.gentle_command') == 1, 'only exact new gentle paths'
            inverse = json.loads(json.dumps(actual))
            inverse['rules'].remove('ending.gentle_command')
            inverse['rules'] = sorted(set(inverse['rules'] + ['ending.willingness_question']))
            endings = [m for m in inverse['morphemes'] if m['kind'] == 'ending']
            assert len(endings) == 1 and endings[0]['form'] == '으렴', 'one canonical gentle ending'
            endings[0]['form'] = '으련'
            parent_surface = surface[:-1] + '련'
            assert surface.endswith('렴') and inverse in history['actual_prior_companions'][parent_surface]['analyses'], 'exact actual prior counterpart'
            expected.append(dict(id=f'gentle-command-history-{len(expected)+1}', surface=surface, analysis=actual, original_occurrences=witnesses, original_contexts=contexts, parent_surface=parent_surface, exact_parent=inverse, contextual_verdict='unjudged', independent_review='pending'))
    assert history['individual_additions'] == expected and len(expected) == 18, 'every exact individual addition and witness'
    assert set(history['actual_prior_companions']) == {w[:-1]+'련' for w in changed}, 'every actual prior counterpart word'
    return dict(original_words=53502, changed_corpus_words=0, changed_history_words=8,
                individual_unjudged_additions=18, original_source_fixtures=len(originals),
                contextual_and_independent_review='pending')


if __name__ == '__main__':
    print(inspect(*inputs()))
