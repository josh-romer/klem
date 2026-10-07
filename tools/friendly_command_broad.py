"""Verify complete-stream preservation and each distinct command path's parent."""
import argparse
import hashlib
from pathlib import Path
from friendly_command_comparison import parent_for
from lexical_nada_audit import ROOT, read, sha
from well_doeda_audit import digest

PRIOR = ROOT / 'docs/ssik-adverb-packaged-observations.json.gz'
SOURCE = ROOT / 'docs/friendly-command-preflight.json.gz'
FIXTURE = ROOT / 'tests/fixtures/friendly-command-sources.json'
REPORT = ROOT / 'docs/friendly-command-observations.json.gz'


def inspect(report):
    prior, source = read(PRIOR), read(SOURCE)
    assert report['schema_version'] == 1 and report['checklist'] == 'COV-017bx'
    assert report['prior_sha256'] == sha(PRIOR) and report['source_sha256'] == sha(SOURCE)
    assert report['fixture_sha256'] == sha(FIXTURE)
    assert report['before_cli_sha256'] == prior['cli_sha256'] == source['before_cli_sha256']
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
            assert {k: v for k, v in before['dictionary'].items() if k != 'readings'} == {k: v for k, v in after['dictionary'].items() if k != 'readings'}
            for i, analysis in enumerate(new_paths):
                reading = after['dictionary']['readings'][i]
                if analysis in old_paths:
                    assert reading == before['dictionary']['readings'][old_paths.index(analysis)]
                    continue
                parent = parent_for(analysis, raw_parents[word])
                additions.append(dict(id='friendly-command-stream-' + digest([new['mode'], location['record'], word, analysis]), mode=new['mode'], location=location, surface=word, analysis=analysis, parent=parent, parent_retained_in_filter=parent in old_paths, source_entry='krdict:73877', source_sense_ids=['1'], reading=reading, contextual_verdict='unjudged', independent_review='pending'))
            if before.get('spacing') != after.get('spacing'):
                old_spacing, new_spacing = before['spacing'], after['spacing']
                assert {k: v for k, v in old_spacing.items() if k != 'alternatives'} == {k: v for k, v in new_spacing.items() if k != 'alternatives'}
                assert len(old_spacing['alternatives']) == len(new_spacing['alternatives'])
                for alternative_index, (old_alt, new_alt) in enumerate(zip(old_spacing['alternatives'], new_spacing['alternatives'], strict=True)):
                    assert {k: v for k, v in old_alt.items() if k != 'records'} == {k: v for k, v in new_alt.items() if k != 'records'}
                    for segment_index, (old_segment, segment) in enumerate(zip(old_alt['records'], new_alt['records'], strict=True)):
                        assert {k: v for k, v in old_segment.items() if k not in {'analysis', 'dictionary', 'breakdowns'}} == {k: v for k, v in segment.items() if k not in {'analysis', 'dictionary', 'breakdowns'}}
                        assert {k: v for k, v in old_segment['analysis'].items() if k != 'analyses'} == {k: v for k, v in segment['analysis'].items() if k != 'analyses'}
                        old_segment_paths, paths = old_segment['analysis']['analyses'], segment['analysis']['analyses']
                        assert [a for a in paths if a in old_segment_paths] == old_segment_paths
                        assert {k: v for k, v in old_segment['dictionary'].items() if k != 'readings'} == {k: v for k, v in segment['dictionary'].items() if k != 'readings'}
                        assert len(segment['breakdowns']) == len(paths)
                        for i, path in enumerate(paths):
                            if path in old_segment_paths:
                                old_index = old_segment_paths.index(path)
                                assert segment['dictionary']['readings'][i] == old_segment['dictionary']['readings'][old_index]
                                assert segment['breakdowns'][i] == old_segment['breakdowns'][old_index]
                                continue
                            parent = parent_for(path, old_segment_paths)
                            assert segment['breakdowns'][i] is not None
                            assert segment['breakdowns'][i] == old_segment['breakdowns'][old_segment_paths.index(parent)]
                            spacing_additions.append(dict(id='friendly-command-spacing-component-' + digest([new['mode'], location['record'], alternative_index, segment_index, path]), mode=new['mode'], location=location, original_surface=word, spaced=new_alt['spaced'], alternative_index=alternative_index, segment_index=segment_index, surface=segment['surface'], analysis=path, parent=parent, breakdown=segment['breakdowns'][i], reading=segment['dictionary']['readings'][i], source_entry='krdict:73877', contextual_verdict='unjudged', independent_review='pending'))
        assert (new['before_jsonl_sha256'] == new['after_jsonl_sha256']) == (not pairs)
        total += new['records']
    assert total == 1128312
    if 'candidate_changes' in report:
        assert report['candidate_changes'] == additions
    if 'spacing_component_changes' in report:
        assert report['spacing_component_changes'] == spacing_additions
    return additions, spacing_additions


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', required=True)
    parser.add_argument('--report', type=Path, default=REPORT)
    args = parser.parse_args()
    additions, spacing = inspect(read(args.report))
    print('Verified 1128312 original frames, retained spacing boundaries, and individually attributed token/spacing-component additions:', len(additions), len(spacing))
