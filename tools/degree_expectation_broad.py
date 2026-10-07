"""Verify complete production streams and exact sourced-ending companion paths."""
import argparse
import hashlib
from pathlib import Path
import sys
sys.path.insert(0, "/home/josh/projects/klem/tools")
import json
from degree_expectation_parent import inverse
from native_lmf import entry

def parent_for(word,path):
    companion,parent,_=inverse(word,path)
    frozen=read(ROOT/'docs/degree-expectation-main-companions.json.gz')
    capture=frozen['companions'][companion]
    assert capture['exit_code']==0
    assert hashlib.sha256(capture['json'].encode()).hexdigest()==capture['sha256']
    assert json.loads(capture['json'])==capture['analysis']
    assert capture['analysis']['normalized']==companion
    assert parent in capture['analysis']['analyses'],(word,path,companion)
    return {'surface':companion,'analysis':parent}

def preserve_dictionary_metadata(before,after):
    assert {k:v for k,v in before.items() if k not in {'readings','lemmas'}} == {k:v for k,v in after.items() if k not in {'readings','lemmas'}}
    assert [v for v in after['lemmas'] if v in before['lemmas']] == before['lemmas']

from lexical_nada_audit import ROOT, read, sha
from well_doeda_audit import digest

PRIOR = ROOT / 'docs/friendly-command-packaged-observations.json.gz'
SOURCE = ROOT / 'docs/degree-rimankeum-source-preparation.json.gz'
FIXTURE = ROOT / 'tests/fixtures/degree-rimankeum-sources.json'
REPORT = ROOT / 'docs/degree-expectation-main-observations-capture.json.gz'


def inspect(report):
    prior, source = read(PRIOR), read(SOURCE)
    companions=read(ROOT/'docs/degree-expectation-main-companions.json.gz')
    assert companions['capture_sha256']==sha(REPORT)
    assert companions['before_cli_sha256']==prior['cli_sha256']
    assert hashlib.sha256(companions['producer']['text'].encode()).hexdigest()==companions['producer']['sha256']
    assert report['schema_version'] == 1 and report['checklist'] == 'COV-013/COV-017'
    assert report['prior_sha256'] == sha(PRIOR) and report['source_sha256'] == sha(SOURCE)
    assert report['fixture_sha256'] == sha(FIXTURE)
    assert report['before_cli_sha256'] == prior['cli_sha256'] == source['cli_sha256']
    assert report['dictionary_sha256'] == prior['dictionary_sha256'] == source['dictionary_sha256']
    assert hashlib.sha256(report['producer']['text'].encode()).hexdigest() == report['producer']['sha256']
    if 'attribution_producer' in report:
        producer = report['attribution_producer']
        assert hashlib.sha256(producer['text'].encode()).hexdigest() == producer['sha256']
        original_path = ROOT / ('docs/friendly-command-packaged-observations-capture.json.gz' if report.get('packaged_capture') else 'docs/friendly-command-observations-capture.json.gz')
        assert report['capture_sha256'] == sha(original_path)
        assert {k: v for k, v in report.items() if k not in {'candidate_changes', 'spacing_component_changes', 'capture_sha256', 'attribution_producer'}} == read(original_path)
    assert len(report['comparisons']) == len(prior['comparisons']) == 8
    raw_parents = {}
    for pair in report['changed_record_pairs']:
        if pair['mode'].endswith('raw'):
            word = pair['before']['analysis']['normalized']
            paths = pair['before']['analysis']['analyses']
            if word in raw_parents:
                assert raw_parents[word] == paths
            raw_parents[word] = paths
    additions = []
    spacing_additions = []
    total = 0
    for old, new in zip(prior['comparisons'], report['comparisons'], strict=True):
        excluded = {'before_jsonl_sha256', 'after_jsonl_sha256', 'changed_records'}
        assert {k: v for k, v in old.items() if k not in excluded} == {k: v for k, v in new.items() if k not in excluded}
        assert new['before_jsonl_sha256'] == old['after_jsonl_sha256']
        pairs = [p for p in report['changed_record_pairs'] if p['mode'] == new['mode']]
        assert len(pairs) == new['changed_records']
        assert len({p['location']['record'] for p in pairs}) == len(pairs)
        text = None
        path = Path(new['source'])
        if path.exists():
            assert sha(path) == new['source_sha256']
            text = path.read_bytes()
        for pair in pairs:
            before, after, location = pair['before'], pair['after'], pair['location']
            assert location['mode'] == new['mode'] and 0 <= location['record'] < new['records']
            assert {k: v for k, v in before.items() if k not in {'analysis', 'dictionary', 'spacing'}} == {k: v for k, v in after.items() if k not in {'analysis', 'dictionary', 'spacing'}}
            assert location['span'] == after['span']
            if text is not None:
                span = after['span']
                assert text[span['start']:span['end']].decode() == after['surface']
                assert location['context'] == text[max(0, span['start'] - 120):min(len(text), span['end'] + 120)].decode(errors='replace')
            word = after['analysis']['normalized']
            old_paths, new_paths = before['analysis']['analyses'], after['analysis']['analyses']
            assert {k: v for k, v in before['analysis'].items() if k != 'analyses'} == {k: v for k, v in after['analysis'].items() if k != 'analyses'}
            assert [a for a in new_paths if a in old_paths] == old_paths
            preserve_dictionary_metadata(before['dictionary'], after['dictionary'])
            for i, analysis in enumerate(new_paths):
                reading = after['dictionary']['readings'][i]
                if analysis in old_paths:
                    assert reading == before['dictionary']['readings'][old_paths.index(analysis)]
                    continue
                parent = parent_for(word, analysis)
                additions.append(dict(id='degree-expectation-stream-' + digest([new['mode'], location['record'], word, analysis]), mode=new['mode'], location=location, surface=word, analysis=analysis, parent=parent, parent_retained_in_filter=parent['analysis'] in old_paths, source_entries=inverse(word,analysis)[2], source_sense_ids=['1'], reading=reading, contextual_verdict='unjudged', independent_review='pending'))
            assert before.get('spacing') == after.get('spacing'), 'This capture establishes unchanged spacing payloads; new segment additions require a separate audit.'
        assert (new['before_jsonl_sha256'] == new['after_jsonl_sha256']) == (not pairs)
        total += new['records']
    assert total == 1128312
    if 'candidate_changes' in report:
        assert report['candidate_changes'] == additions
    if 'spacing_component_changes' in report:
        assert report['spacing_component_changes'] == spacing_additions
    closure = read(ROOT / 'docs/degree-expectation-main-broad-native-closure.json.gz')
    assert closure['capture_sha256'] == sha(REPORT)
    assert {k: entry(v) for k, v in closure['original_lmf'].items()} == closure['complete_native_entries']
    heads = {lemma['text'] for change in additions for lemma in change['analysis']['lemmas']}
    matched = {e['headword'] for e in closure['complete_native_entries'].values()}
    assert closure['observed_added_heads'] == sorted(heads)
    assert closure['dictionary_matched_heads'] == sorted(matched)
    assert closure['unmatched_hypotheses'] == sorted(heads - matched)
    return additions, spacing_additions


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', required=True)
    parser.add_argument('--report', type=Path, default=REPORT)
    args = parser.parse_args()
    additions, spacing = inspect(read(args.report))
    print('Verified 1128312 original frames, retained spacing boundaries, and individually attributed token/spacing-component additions:', len(additions), len(spacing))
